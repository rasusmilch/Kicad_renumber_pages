"""Lossless S-expression syntax with offsets into the original UTF-8 bytes.

This module never serializes a document. Quoted token ranges include the
quotes. Unknown escape encodings fail closed rather than losing information.
"""

from dataclasses import dataclass


class InvalidProject(ValueError):
    """Input is invalid, unsupported, inconsistent, or changed during analysis."""


@dataclass(frozen=True)
class Atom:
    value: str
    start: int
    end: int
    quoted: bool


@dataclass(frozen=True)
class Expr:
    items: tuple["Atom | Expr", ...]
    start: int
    end: int

    @property
    def head(self) -> str:
        if self.items and isinstance(self.items[0], Atom) and not self.items[0].quoted:
            return self.items[0].value
        return ""


def parse(data: bytes) -> Expr:
    """Parse exactly one expression without recursion or character offsets."""
    try:
        data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise InvalidProject(f"invalid UTF-8 at byte {exc.start}") from exc
    if b"\0" in data:
        raise InvalidProject("NUL byte in schematic")
    stack: list[tuple[int, list[Atom | Expr]]] = []
    result: list[Atom | Expr] = []
    i = 0
    escapes = {34: b'"', 92: b"\\", 110: b"\n", 114: b"\r", 116: b"\t"}
    while i < len(data):
        ch = data[i]
        if ch in b" \t\r\n":
            i += 1
            continue
        if ch == 40:
            if len(stack) >= 512:
                raise InvalidProject("unsupported S-expression nesting beyond 512 levels")
            stack.append((i, []))
            i += 1
            continue
        if ch == 41:
            if not stack:
                raise InvalidProject(f"unexpected ')' at byte {i}")
            start, items = stack.pop()
            node: Atom | Expr = Expr(tuple(items), start, i + 1)
            i += 1
        elif ch == 34:
            start = i
            i += 1
            value = bytearray()
            while i < len(data) and data[i] != 34:
                if data[i] == 92:
                    i += 1
                    if i == len(data) or data[i] not in escapes:
                        raise InvalidProject(f"unsupported or incomplete string escape at byte {i}")
                    value.extend(escapes[data[i]])
                else:
                    value.append(data[i])
                i += 1
            if i == len(data):
                raise InvalidProject(f"unterminated quoted string at byte {start}")
            i += 1
            node = Atom(value.decode("utf-8"), start, i, True)
            if i < len(data) and data[i] not in b" \t\r\n()":
                raise InvalidProject(f"missing token delimiter at byte {i}")
        else:
            start = i
            while i < len(data) and data[i] not in b" \t\r\n()":
                if data[i] in b'"\\;':
                    raise InvalidProject(f"unsupported unquoted syntax at byte {i}")
                i += 1
            node = Atom(data[start:i].decode("utf-8"), start, i, False)
        (stack[-1][1] if stack else result).append(node)
    if stack:
        raise InvalidProject(f"unclosed '(' at byte {stack[-1][0]}")
    if len(result) != 1 or not isinstance(result[0], Expr):
        raise InvalidProject("expected exactly one top-level S-expression")
    return result[0]


def children(node: Expr, head: str) -> tuple[Expr, ...]:
    return tuple(x for x in node.items[1:] if isinstance(x, Expr) and x.head == head)


def only(node: Expr, head: str) -> Expr:
    matches = children(node, head)
    if len(matches) != 1:
        raise InvalidProject(f"expected exactly one {head} record in {node.head}")
    return matches[0]


def atom(node: Expr, index: int = 1, *, quoted: bool = True) -> Atom:
    if len(node.items) <= index or not isinstance(node.items[index], Atom):
        raise InvalidProject(f"missing value in {node.head}")
    value = node.items[index]
    if value.quoted != quoted:
        raise InvalidProject(f"unexpected value encoding in {node.head}")
    return value


def scalar(node: Expr, *, quoted: bool = True) -> Atom:
    if len(node.items) != 2:
        raise InvalidProject(f"malformed {node.head} scalar")
    return atom(node, quoted=quoted)
