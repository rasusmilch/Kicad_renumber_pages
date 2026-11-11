# Validation strategy

**Current evidence:** the parser, graph, immutable plan, terminal preview, and explicit apply/backup/limited rollback have passing Python behavior and failure-injection tests on disposable fixtures. A project-local virtual environment contains pytest. Independent file-level checks, actual Eeschema hierarchy inspection, and normalized netlist comparisons have run with official KiCad 10.0.8 on disposable upstream/synthetic projects. Independent source review reported no blocking apply defect; qualification evidence awaits independent acceptance; no CI exists and passing tests do not establish production readiness or power-loss durability.

## Risk to establish confidence against
Renumbering must not change circuit semantics, misnumber shared/repeated instances, silently skip sheets, partially write files, or claim safety when unsupported syntax or an ambiguous hierarchy prevents confidence.

## Validation layers and current coverage
1. **Model/traversal behavior:** single sheet; nested multiple levels; repeated source files via distinct instance paths; empty sheets; natural numeric names; ties; reordered siblings; existing duplicate/gapped page numbers; idempotent reruns. Expected order must follow the *approved* ordering policy rather than tests inventing it.
2. **Read and parse integrity:** covered by tests for malformed S-expressions, missing referenced sources, duplicate/invalid UUIDs and paths, cycles, unsupported versions/syntax, orphan current-project paths, foreign-project records, missing pages, JSON duplicates, symlinks/hardlinks, and external references. Registry and document UUID equality is not required; effective-root rules below govern path validation.
3. **Read-only safety:** tests compare file contents, mtimes, and directory entries before/after previews and no-ops, including a cold launcher with no import caches. Invalid apply fails without source writes. Source changes during analysis fail. **Write safety:** explicit apply, complete verified backups before replacement, per-file staging/replacement, source-change guards, limited rollback, interrupted-operation blocking, and unchanged repeat runs are covered by the apply suite below.
4. **Semantic preservation:** compare the complete pre/post instance graph and all protected schematic content; review actual changed expressions and Git diffs. Netlist equivalence and headless KiCad load checks should be evaluated for their actual ability to detect unintended circuit changes; ERC alone is not proof of preservation.
5. **Integration/pilot:** run against disposable copies of realistic repeated-channel projects with independently verified page counts and intended order. Check KiCad UI reopening and PDF page order when this is an applicable part of the approved workflow.

Tests should use synthetic fixture projects plus a carefully vetted real-world fixture if authorization, confidentiality, and distribution permit. A customer schematic is not automatically a distributable fixture. Do not copy proprietary test assets into a public repository.

Drawing compatibility regressions cover `rectangle`, `table`, and both together. Original synthetic drawing structures follow KiCad 10.0.6's [shape/table writer](https://gitlab.com/kicad/code/kicad/-/blob/10.0.6/eeschema/sch_io/kicad_sexpr/sch_io_kicad_sexpr.cpp) (`saveShape`, `saveTable`, and `saveTextBox`). Tests verify byte-identical drawings and every non-page span in candidate bytes, hierarchy-looking table-cell text remaining opaque, exact root/nested page locations, multiple roots and reused descendants, deterministic read-only CLI runs, and continued rejection of unknown top-level syntax, malformed expressions, missing actual pages, and invalid parent paths. Public issue23403 copies augmented with these original drawings also preview correctly; this is Python fixture validation, not KiCad 10 GUI/CLI integration evidence.

`tests/test_apply.py` uses actual temporary directories, exclusive staging, and real `os.replace` operations as well as controlled fault injection. Coverage includes single/multiple roots, reused descendants, mismatched root/document UUIDs and nil fallback, drawing/opaque-byte preservation, project/unrelated-file preservation, backup layout/completeness/digests, timestamp collisions and previous backups, mode/mtime preservation, editor locks, overlapping applies, malformed/stale markers, source changes after planning and just before replacement, and changes to the project or unchanged referenced files during partial application.

Injected failures cover marker/backup creation and writing, corrupted backups before and during replacement, staging creation/write/sync/verification, changed staging permissions, forward replacement before and after actual filesystem mutation, installed-content verification, directory sync, final graph verification, complete/incomplete rollback, third-party contents, marker cleanup, and unknown staging data. A subprocess calls `os._exit` after the first real replacement; the surviving marker and verified backup remain, exactly one file has expected-new bytes, and the next apply refuses without altering that state. This demonstrates process-interruption handling, not physical power-loss behavior.

## Evidence rules
- Codex must report actual commands executed, exit statuses, salient failures, and tests not run. No success without execution evidence.
- When Python is introduced, use behavior-focused `pytest` tests and Python compile checks (`python -m compileall` or an approved equivalent) where available and applicable.
- Validate code at the feature level, then perform a separate integrated check before declaring general readiness.
- Tests of text format or successful parses alone cannot prove functional connectivity preservation; toolchain-independent structural checks and KiCad verification have distinct confidence limits.
- Validate source identity and provenance of any imported KiCad fixture or version-specific claim.

## Commands
**Executed setup:** `python -m venv .venv` and `.venv/bin/python -m pip install --index-url https://pypi.org/simple pytest`. Installation succeeded from PyPI: pytest 9.2.0, iniconfig 2.3.1, packaging 26.3, pluggy 1.7.0, and pygments 2.21.0. Pip disabled its unwritable home cache; no system packages were changed. `requirements-dev.txt` pins the test runner for repeatable setup.

**Executed checks:** Python 3.12.14 on Linux; `.venv/bin/python -m pytest -q`, `python -m unittest discover -q`, `python -m compileall .`, and `git diff --check` have succeeded. The tests are unittest-compatible and discovered by pytest; they generate original, small synthetic KiCad 10 projects in temporary directories. Test fixtures are not live customer projects, and the suite does not require network access or KiCad. The task receipt records the final suite count and command results.

**Preview:** `python renumber_pages.py <explicit-project.kicad_pro>`. Direct preview of the public issue23403 fixture reports two roots, four instances, and already-correct pages 1–4, including the mismatched registered/document UUID case. Public files were inspected in scratch space and are not copied into this repository.

**Apply:** `python renumber_pages.py <disposable-project.kicad_pro> --apply`. Disposable demonstrations cover successful writes/backups, a completely unchanged second invocation, and a detected second-replacement failure with verified restoration and retained backups. No real customer file is used. Exit 4 covers failure before original writes or with verified restoration; exit 5 retains unresolved evidence and requires manual inspection. The exact manual marker-clearing procedure and digest interpretation are in [README.md](../README.md#manual-recovery-after-interruption).

**Unverified:** Python 3.11 execution, Windows, native Kubuntu, network filesystems, broad design coverage, physical power-loss durability, and hot reload with an open editor. Installed KiCad 10.0.8 results are scoped below; KiCad 9 and CLI success alone cannot establish full KiCad 10 GUI compatibility.

## Writable-descriptor synchronization correction (2026-11-11)

**Status: implemented and Linux-tested; native Windows resolution NOT VERIFIED.** Preflight fetched the existing feature branch and confirmed clean local/remote `dee6d636ea656dd871f9c8666581db72364e33ed`, with no divergence or discarded work. No customer project was accessed or recovered.

Descriptor audit found three synchronization paths: `_write()` flushes and fsyncs writable `wb` descriptors; POSIX directory sync uses `O_RDONLY|O_DIRECTORY` (skipped on Windows); old `_metadata()` reopened its destination as `rb` after copying metadata and fsynced that read-only regular-file descriptor. A deterministic `_commit` model using actual temporary files reproduced EBADF in the **first backup's metadata preparation**, before staging or any original replacement. This establishes the suspected source path under injection, not the exact stage of the user's native Windows incident.

The correction retains data write → flush → fsync → close. It then opens the **prepared destination** as non-truncating `r+b` before copying source permissions with `copystat`, verifies mode/mtime, flushes/fsyncs that writable descriptor, closes, and checks metadata/content/digest again. The writable descriptor is acquired before a copied read-only attribute can block opening it. Originals remain read-only inputs to verification. All backups are completed and verified, then the full backup set is reread after staging and before the first replacement. Existing locks, identities, hashes, operation marker, per-file checks, and conservative rollback remain in use.

On Windows, changed read-only schematic sources are explicitly refused **before preparation**; the utility does not clear an original's attribute to permit replacement. Read-only project/unchanged-source reads, preview, and no-op remain allowed. POSIX read-only sources can still be replaced when directory permissions permit, with their mode/mtime preserved. Cleanup can clear read-only only on tool-created staging files, after regular/unaliased-file checks and expected-byte verification for returned stages. Failed staging cleanup retains its marker and diagnostic evidence rather than reporting complete recovery. Backups and original attributes are not relaxed for cleanup.

File sync errors, including EBADF, propagate with operation, path, and stage; no file synchronization is skipped or downgraded to a read-only descriptor. The existing supported-filesystem directory policy is unchanged: Windows has no portable directory fsync; POSIX EINVAL/ENOTSUP/ENOSYS indicate unavailable directory synchronization, while other directory errors propagate with path context. This is not a new power-loss durability claim.

`tests/test_sync.py` adds **18 tests**: 16 runnable here and two native-Windows-only. A portable handle-tracking fault injector rejects read-only descriptors while forwarding valid fsync calls to the actual filesystem. Coverage includes:

- Prior-policy EBADF reproduction in backup metadata; corrected backup/stage writable modes and data-before-metadata sync ordering.
- Complete original backups, relative paths and SHA-256 checked at the first replacement barrier; verification failures block replacement.
- Read-only source backup/stage preparation, preserved mode/mtime, no source write-open, conservative Windows refusal, and true no-op behavior.
- Actual POSIX replacement of read-only files, and symlink/hardlink refusal before temporary cleanup can change source attributes.
- Marker/backup/stage data-sync failures and backup/stage metadata-sync failures, with path/stage diagnostics and no original replacement.
- Real later replacements followed by complete rollback; rollback sync failure and staging-cleanup failure retain markers/backups.
- Successful apply followed by a complete tree/mtime no-op. Native tests cover actual Windows apply/no-op and copied read-only metadata synchronization; they are skipped here.

Environment: Linux x86_64, Python 3.12.14, existing pytest 9.2.0 virtual environment; no dependency installation. `python.exe`, `powershell`, `pwsh`, and `wine` are unavailable. No native Windows execution environment is present. Injected Windows `_commit` behavior and Windows policy branches run on Linux filesystem operations, and are not native Windows compatibility evidence.

Executed commands, all exit 0:

```sh
.venv/bin/python -m pytest -q
.venv/bin/python -m unittest discover -q
KICAD_ISSUE23403_FIXTURE=/workspace/work/qualification/upstream/issue23403 KICAD10_APPRUN=/workspace/work/qualification/kicad10/squashfs-root/AppRun .venv/bin/python -m pytest -q
.venv/bin/python -m compileall .
git diff --check
git status --short
```

Default pytest: **135 passed, 5 skipped, 74 subtests passed**. Unittest: **140 tests, OK (skipped=5)**. With the existing authentic public fixture and official KiCad 10.0.8 AppRun supplied, pytest: **137 passed, 3 skipped, 77 subtests passed**. The three remaining skips are native Windows tests (one identity test plus two new synchronization tests); default execution additionally skips the two opt-in public-fixture/installed-CLI tests. Existing backup, rollback, interruption, source-identity/content, numbering, and independent byte-preservation coverage passes.

Additional actual launcher commands on a disposable temporary project used `.venv/bin/python renumber_pages.py <disposable.kicad_pro>`, then the same command with `--apply` twice: all exit 0. Preview left the tree unchanged, the saved backup bytes/SHA-256 matched the original, final numbering was correct, and the second apply left the complete tree and mtimes unchanged. Earlier KiCad GUI qualification is historical evidence; GUI inspection was not repeated for this repair.

Remaining limits: native Windows `_commit`, read-only-attribute behavior, replacement and cleanup semantics, NTFS/ReFS/network filesystems, Python 3.11, and physical power-loss durability remain unverified. The narrower descriptor defect is corrected in source and passes the modeled failure, but the user's Windows failure must not be declared resolved before native execution. Next validation: native Windows preview/apply/no-op on a disposable representative project, with synchronization-stage diagnostics and verified backups.

## Windows source-identity correction (2026-11-11)

The reported Windows diagnostic established a ctime-only discrepancy: path-based `lstat` values before/after a read agreed, but stable handle-based `fstat` ctime differed. The previous implementation compared all seven fields unconditionally and rejected this unchanged file while opening. Per the explicit user/ChatGPT correction, `_identity()` now substitutes zero for `st_ctime_ns` on `sys.platform == "win32"`. Python documents [Windows ctime deprecation](https://docs.python.org/3/library/os.html#os.stat_result.st_ctime_ns); ctime is not used as a Windows integrity signal. POSIX keeps its actual ctime.

The tuple remains `(st_dev, st_ino, st_mode, st_nlink, st_size, st_mtime_ns, ctime_slot)`. All consumers were inspected: read-open/read-complete/post-close checks, final analysis snapshots, apply source verification, marker ownership, immediate replacement and rollback rechecks, physical device/inode uniqueness, and permission/mtime preservation. Physical identity stays at indices 0–1, mode at 2, and mtime at 5. No tuple comparison consumer drops any additional field. A shared equality verifier now reports differing field names/values and verification stage. Permission/mtime failures also identify the field. Content/digest, backup, alias, lock, and rollback protections are unchanged.

`tests/test_source_identity.py` adds 15 tests (14 executable here, one native-Windows-only), including deterministic injected stat records and actual temporary files:

- Stable path/handle ctime disagreement accepted on the Windows policy, including changed path ctime across snapshot rechecks; contents and SHA-256 retained.
- Every retained field independently rejected at open and apply snapshot verification; reading-stage diagnostics include multiple differing fields.
- Actual size and mtime changes, and an actual same-content/same-mtime file replacement detected at the post-close path check.
- Same-size content edits with mtime restored detected by both final preview analysis and apply's content/digest guard.
- POSIX ctime-only open rejection and a real POSIX chmod/restore detected through ctime even after permissions are restored.
- Successful read-only CLI preview leaves the entire temporary project inventory unchanged; real apply/backup/no-op and failure-after-replacement/rollback run with injected Windows ctime mismatch.

Execution host: Linux x86_64, Python 3.12.14, existing pytest 9.2.0 virtual environment. `python.exe`, `powershell`, `pwsh`, and `wine` were absent; no native Windows runner was available. The native test is explicitly skipped, not passed. Simulated Windows identity policy still uses Linux filesystem operations and does not establish Windows replacement/permission semantics, NTFS/ReFS/network-share compatibility, or Python 3.11 execution. No customer project or live-project apply was used. No dependencies were added.

Executed checks, all exit 0:

```sh
.venv/bin/python -m pytest -q
.venv/bin/python -m unittest discover -q
KICAD_ISSUE23403_FIXTURE=/workspace/work/qualification/upstream/issue23403 KICAD10_APPRUN=/workspace/work/qualification/kicad10/squashfs-root/AppRun .venv/bin/python -m pytest -q
KICAD_ISSUE23403_FIXTURE=/workspace/work/qualification/upstream/issue23403 KICAD10_APPRUN=/workspace/work/qualification/kicad10/squashfs-root/AppRun .venv/bin/python -m unittest discover -q
.venv/bin/python -m compileall .
git diff --check
git status --short
```

Default pytest: **119 passed, 3 skipped, 67 subtests passed**. Unittest: **122 tests, OK (skipped=3)**. The default skips are native Windows plus the two opt-in upstream/installed-CLI checks. With the existing authentic upstream fixture and official KiCad 10.0.8 AppRun supplied, pytest reports **121 passed, 1 skipped, 70 subtests passed**, and unittest reports **122 tests, OK (skipped=1)**; only native Windows remains skipped. An additional disposable demonstration reproduced the ctime-only rejection using the previous comparison policy, accepted the same bytes with the corrected policy, and ran the actual launcher preview with exit 0 and an unchanged project inventory. Existing backup, rollback, source-change, alias, interruption, and independent byte-oracle tests pass. Installed CLI tests reran; earlier GUI evidence below is historical qualification, not a new GUI run for this repair. Recommended next validation: genuine Windows read-only preview with native lstat/fstat observations on a disposable representative project.

## Evidence gap and approved fixtures (2026-11-10)
- Codex's planning environment had KiCad 9.0.2 and Python 3.12.14, with no KiCad 10 runner. KiCad 9 cannot validate KiCad 10 imports/exports.
- ChatGPT independently inspected a current KiCad 10 hierarchical schematic project and upstream KiCad 10 documentation. Use the [KiCad upstream issue23403 regression fixture](https://gitlab.com/kicad/code/kicad/-/tree/10.0.6/qa/data/eeschema/issue23403) as public reference for multiple roots sharing a subsheet; build minimal original synthetic test fixtures locally, without copying proprietary customer material.
- Independent format evidence and safety boundary are in [ARCHITECTURE.md](ARCHITECTURE.md). Fixture structure tests must prove parent instance-path lookup, multi-root numbering, reused child file expansion and exact allowed byte changes. Include a fixture with a non-nil project-registered root UUID **different** from the document header UUID (as in KiCad upstream issue23403); assert acceptance and child paths keyed to the registered UUID. Include equality and explicit nil-registry-UUID fallback cases; reject absent/malformed registry UUIDs and duplicate effective root UUIDs, and verify neither identity is changed. KiCad CLI 10.0.6 can differ from Eeschema about this override; validate GUI and CLI versions separately rather than accepting CLI-only proof. The installed KiCad 10.0.8 qualification below supplies separate GUI and CLI evidence for these representative cases.


## Test environment setup authorization (2026-11-10)

The user explicitly permits Codex to install reasonably necessary development/test packages in its isolated execution environment. For Python tests, use a virtual environment and install `pytest` from a trusted package index; installing official distribution `python3-venv` or official KiCad 10 tooling for actually needed integration validation is authorized when safe and supported. Do not alter an end user's host system or install unrelated packages. Runtime remains standard-library-only unless a separate architecture decision is approved.

The setup authorization is distinct from test evidence; executed setup and checks are recorded above. Future receipts must state actual commands, versions where relevant, results, and skipped/unavailable integration tests. Refer to [AGENTS.md](../AGENTS.md) for the authoritative safety conditions.

## Installed KiCad qualification (2026-11-11)

**Disposition: FULL INTEGRATION QUALIFICATION for the three fixtures and environment below**, using the assigned task's definition: independent file checks plus actual KiCad 10 GUI inspection. This is evidence for independent review, not production readiness, a new compatibility promise, or permission for live customer use. No product implementation, runtime dependency, numbering policy, or architecture changed.

### Source and installation evidence

Preflight verified a clean `codex/read-only-numbering-engine` at reviewed commit `71b284bbb2129ee749ee46a73d4e4d283455203b`, with the expected `rasusmilch/Kicad_renumber_pages` origin. `git fetch origin`, an explicit feature-ref fetch, `git ls-remote --heads origin refs/heads/codex/read-only-numbering-engine refs/heads/main`, and `git merge --ff-only origin/codex/read-only-numbering-engine` succeeded; the latter reported already up to date. No source divergence or discarded work.

Actual environment commands/results:

| Command | Exit / relevant output |
| --- | --- |
| `cat /etc/os-release` | 0; Debian GNU/Linux 13, trixie, 13.6 |
| `uname -m` | 0; x86_64 |
| `.venv/bin/python --version` | 0; Python 3.12.14 |
| `.venv/bin/python -m pytest --version` | 0; pytest 9.2.0, existing virtual environment reused |
| `command -v kicad-cli` | 0; `/usr/bin/kicad-cli` |
| `kicad-cli version` | 0; **9.0.2**, not KiCad 10 |
| `command -v eeschema` | 0; `/usr/bin/eeschema`, system KiCad 9 |
| `dpkg-query -W kicad` | 0; `9.0.2+dfsg-1` |
| `apt-cache policy kicad` | 0; installed/candidate 9.0.2; unreadable `80-applied-apt-retries` warning |
| `command -v apt-get`, `dpkg`, `docker` | 0; `/usr/local/bin/apt-get`, `/usr/bin/dpkg`, `/usr/local/bin/docker` |
| `sh -c 'command -v <tool>'` for sudo, flatpak, snap, Xvfb, gpgv | 127 each; unavailable |
| `findmnt -T /workspace -o TARGET,FSTYPE,SOURCE` | 0; local workspace overlay filesystem |
| `ls -l /tmp/.X11-unix/X0` | 0; shared X11 display socket present |

The shell initially had no `DISPLAY`, `WAYLAND_DISPLAY`, or `XAUTHORITY`. Native desktop controls supplied a usable X11 desktop; no virtual display installation was needed. Network access to official download/upstream hosts worked. Home configuration paths are read-only: bare version calls emitted configuration-directory errors but still returned versions/exit 0. Setting writable, isolated XDG paths removed those diagnostics. No system upgrade, privileged installation, repository change, or workstation modification was needed.

The [official KiCad Linux download page](https://www.kicad.org/download/linux/) listed the 10.0.8 Lite AppImage. The native package candidate was only 9, so the official self-contained distribution was chosen. Executed download/extraction commands (all exit 0):

```sh
curl -fL https://www.kicad.org/download/linux/ -o /workspace/work/qualification/linux-download.html
curl -fL https://kicad-downloads.s3.cern.ch/appimage/stable/kicad-10.0.8-x86_64-lite.AppImage.tar -o /workspace/work/qualification/kicad-10.0.8-x86_64-lite.AppImage.tar
tar -xf /workspace/work/qualification/kicad-10.0.8-x86_64-lite.AppImage.tar -C /workspace/work/qualification/kicad10
chmod u+x /workspace/work/qualification/kicad10/kicad-10.0.8-x86_64-lite.AppImage
# In /workspace/work/qualification/kicad10:
./kicad-10.0.8-x86_64-lite.AppImage --appimage-extract
```

Archive: 316,538,880 bytes; SHA-256 `abb59cee9f9782736c1b9a92e3ab08b31320ee01d72a6f9442a07fdef71b87d0`. MD5 `d7517ca69c07918885df87c311066150` matched the official mirror's object metadata. This records official HTTPS provenance and artifact identity; no detached signature verification was performed. Extraction bypassed FUSE and required no root. Lite omits 3D assets, irrelevant to these schematic checks.

Subsequent commands used these isolated paths (the GUI used the same profile):

```sh
export XDG_CACHE_HOME=/workspace/work/qualification/xdg/cache
export XDG_CONFIG_HOME=/workspace/work/qualification/xdg/config
export XDG_DATA_HOME=/workspace/work/qualification/xdg/data
KICAD10_APPRUN=/workspace/work/qualification/kicad10/squashfs-root/AppRun
"$KICAD10_APPRUN" kicad-cli version
```

Actual executable output: **10.0.8**, exit 0. System KiCad 9 remained installed separately and supplied no integration pass.

### Fixtures and independent expectations

Public source: [official KiCad tag 10.0.6 issue23403](https://gitlab.com/kicad/code/kicad/-/tree/10.0.6/qa/data/eeschema/issue23403). Four files were downloaded from `https://gitlab.com/kicad/code/kicad/-/raw/10.0.6/qa/data/eeschema/issue23403/<filename>` into scratch space. Their Git blob SHA-1 identities are pinned and checked by `UPSTREAM_BLOBS` in [test_independent_qualification.py](../tests/test_independent_qualification.py). No upstream/customer project files or binaries were committed. Preview of the byte-authentic original reported 2 roots, 4 instances, already-correct pages 1–4, and changed nothing.

The new tests import no engine, parser, candidate, or plan implementation. Explicit tables establish root identities, full UUID instance paths, source files, page-record owner files/slots, existing values, and expected pre-order **before** any utility invocation. A deliberately fixture-limited byte matcher checks the stored parent paths, changes only known quoted page tokens, and constructs complete independently expected file bytes. It is not a product parser or alternative numbering policy.

| Fixture | Roots / instances | Independently fixed traversal, pages assigned consecutively |
| --- | --- | --- |
| Public issue23403 copy | 2 / 4 | 1 Root; 2 Root/shared1; 3 top_level_sheet_1; 4 top_level_sheet_1/shared1 |
| Original forest | 2 / 9 | 1 Block 2; 2 Block 2/Channel 2; 3 its Empty 2; 4 Block 2/Channel 10; 5 its Empty 2; 6 Block 2/Empty 10; 7 Block 10; 8 Block 10/Channel 2; 9 its Empty 2 |
| Original single-root nil fallback | 1 / 2 | 1 Single; 2 Single/Empty |

Upstream effective roots: `da308afe-918c-407a-88a0-b7c2f2b6b630` and `ccc7e5dc-77b6-4792-b9b6-8eaa039374d5`; the second document UUID is `574f9438-bf45-4364-93f8-a7864ab0aeac`. Forest roots are `22222222-2222-4222-8222-222222222222` and `aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa`; the latter document UUID is `11111111-1111-4111-8111-111111111111`. The single-root registry explicitly stores nil and resolves to that `1111…` document UUID. Neither stored identity is rewritten. Every full descendant UUID path and its page owner are specified in the test tables.

Forest registration stores Block 10 before Block 2, and physical child order is deliberately non-natural. Three instances reuse `shared.kicad_sch`, each with a repeated empty descendant, plus a direct empty child. Rectangle/table objects contain page- and sheet-looking text. Duplicated/gapped old values include 88, 22, 44, and 90. The upstream disposable copy changes only four old page values to 9, 40, 9, 90. Single uses 88 and 7. Unreferenced invalid schematic sentinels remain untouched. Page-bearing files: upstream's two roots; forest's two roots plus shared; single's root. Empty/shared leaf files carry no page records of their own.

### Preview, apply, backups, and recovery

Actual launcher subprocesses used `.venv/bin/python renumber_pages.py <disposable-project.kicad_pro>` and the same command with `--apply`. All successful preview/apply/no-op commands exited 0. Fixed expected order, full instance paths, old/new pages, and affected-file reports matched. Previews left complete directory/file/content/mode/mtime snapshots unchanged. Apply matched **complete independently constructed files**, protecting every non-page byte, all UUIDs, drawings, symbols/connectivity, project JSON, empty sources, and unrelated files. Exactly 2 upstream, 3 forest, and 1 single source files changed. Mode/mtime checks passed. Second applies created nothing and changed no bytes or mtimes anywhere in each tree.

Persistent GUI-tested copies were under `/workspace/work/qualification/cases/`; pristine misnumbered copies under `before/`. Editors and manager projects were closed before apply; no locks were deleted to bypass checks. Each changed file had one complete original backup, the exact expected relative path, matching full bytes and independently computed SHA-256:

| Fixture / timestamp directory | File | Original/backup SHA-256 |
| --- | --- | --- |
| upstream / `2026-11-11_00-54-17` | issue23403.kicad_sch | `a84ec4a13a60008a23ed23fed3819b161647b939dd7937aea57083cd5feb4aa9` |
| upstream / same | top_level_sheet_1.kicad_sch | `82be20aca57f70b716d645a6edf62c2d4d8f7cee8c540bbb3539b41f1e0ba70b` |
| forest / `2026-11-11_00-59-18` | forest.kicad_sch | `121af2382cad54540d8e97d52c382b8a53356d190f436959f26dfc9509e76abb` |
| forest / same | top2.kicad_sch | `0d98d345cab5bb59d5dc538ea8461624699ff24f95555d04118874954a5c6821` |
| forest / same | shared.kicad_sch | `2b9265f7affeb390986e4dc8f1dbc7a415282f9f754dc93c79159dd5cf122adb` |
| single / `2026-11-11_01-00-45` | single.kicad_sch | `d1bac464ccd1bd5d82aaaa59901b7b8f8e5ea25d31b8026570117ee11863bd7d` |

Recovery test: a subprocess performed one real `os.replace`, then `os._exit(73)` before the next replacement. The marker and all original backups survived; independent digests classified one target expected-new, two original, zero unknown. Another actual `--apply` returned 5 with the entire partial tree unchanged. A separate simulated external edit exercised unknown-digest classification and another unchanged exit-5 refusal. Unknown bytes and the marker were copied to audit files before manual restoration. Verified backups restored every original input byte/digest; read-only preview succeeded while the marker still existed. Only after restoration verification was the disposable marker explicitly cleared; backups and audit evidence remained. This follows the documented manual procedure, without claiming physical power-loss durability or automatic recovery from arbitrary third-party edits.

### Actual CLI and GUI evidence

Verified supported syntax with `"$KICAD10_APPRUN" kicad-cli sch export netlist --help <fixture.kicad_sch>` (0). Actual before/after commands used:

```sh
"$KICAD10_APPRUN" kicad-cli sch export netlist --format kicadxml --output /workspace/work/qualification/exports/before/forest.xml /workspace/work/qualification/cases/forest/forest.kicad_sch
"$KICAD10_APPRUN" kicad-cli sch export netlist --format kicadxml --output /workspace/work/qualification/exports/after/forest.xml /workspace/work/qualification/cases/forest/forest.kicad_sch
```

The same commands ran for `single/single.kicad_sch` and `upstream/issue23403.kicad_sch`, with corresponding output names. All six exports exited 0 and included 9, 2, and 4 sheet entries respectively. Independent XML comparison retains component/reference multiplicity, values, libraries, properties, instance sheet paths, and UUIDs; compares complete component/libpart/library sections as sorted trees; and compares net names plus all nodes/properties, ignoring only net numeric export codes. Design timestamps, source locations, and exported sheet-number metadata are excluded from electrical equivalence. Single-root XML intentionally omits the root display-name prefix. All comparisons matched. Upstream contains two exported capacitor instances and four nets; synthetic fixtures have no electrical components, so their netlist checks are limited structural corroboration.

Upstream exports warn `schematic has annotation errors, please use the schematic editor to fix them` both before and after. Both exported references are C1; the public source has only one stored symbol-instance annotation entry. This pre-existing annotation limitation was not repaired or counted as a clean ERC result. CLI can create/update `.kicad_prl` session sidecars; integration tests permit that KiCad-owned side effect while protecting project/schematic inputs. Utility preview/no-op checks still require a completely unchanged tree. No CLI-only conclusion about effective root UUID correctness was used, and CLI 10.0.6 itself was not installed or requalified.

For GUI inspection, the official AppRun opened each disposable `.kicad_pro` in KiCad Manager and launched its Schematic Editor. The isolated first-run profile started without external libraries (the public fixture embeds its capacitor symbol). Accelerated rendering produced stale/black canvas regions; selecting **Fallback Graphics** in the isolated profile made the actual sheets/title blocks visibly inspectable. Screenshots, hierarchy labels, and editor captions were observed through native desktop controls, not inferred from process existence or exit status.

Every top-level and descendant instance was opened by hierarchy navigation both before and after renumbering: all 4 upstream, 9 forest, and 2 single instances. Reused-file editor captions distinguished their parent paths. Post-apply hierarchy labels showed precisely pages 1–4, 1–9, and 1–2 from the independent tables; visible title blocks and rectangle/table rendering corroborated the selected sheets. No missing/unexpected duplicate sheet instance or post-apply load/compatibility repair warning appeared. Forest's hierarchy navigator retained registry order (Block 10 first) while its page labels correctly showed Block 10 as 7–9 and Block 2 as 1–6; the utility deliberately does not reorder project metadata.

Deliberately duplicated baseline pages caused KiCad to announce automatic in-memory page repairs on upstream/forest before apply (dirty editor titles); those changes were discarded without saving. Single loaded its baseline 88/7 without a repair notice. All post-apply editor titles were clean, with no repair notice. Closing the baseline GUI normalized some `.kicad_pro` defaults (ERC severity, empty netclass maps, and last export path settings), and created session/history files. These were KiCad's own actions, outside the utility. Apply's independent comparison used the immediate post-close input baseline and left that project byte-identical; separate fresh-fixture tests also prove original project JSON is preserved. Final post-GUI schematic bytes equal the independently expected page-only outputs and retain format 20260306/generator_version 10.0. No schematic save, format conversion, or customer project mutation was performed.

Preserved original mtimes did not prevent correct closed-project reopening on this local overlay filesystem: the same paths reopened with the new page numbers and protected content. This does not establish open-editor change detection (apply requires closure), Windows, network share semantics, or universal metadata preservation. No concrete evidence justified changing the approved metadata policy.

### Reproduction and remaining limits

The optional public test takes a directory containing the four authentic upstream files; the optional CLI test additionally takes the official extracted AppRun path. Tests perform no download/install themselves. Without those environment variables, the public-source and installed-CLI tests explicitly skip; the synthetic file/recovery tests still run. GUI inspection is manual evidence and is not automated by this test module.

Executed complete checks (exit 0; actual final receipt records publication):

```sh
KICAD_ISSUE23403_FIXTURE=/workspace/work/qualification/upstream/issue23403 KICAD10_APPRUN=/workspace/work/qualification/kicad10/squashfs-root/AppRun .venv/bin/python -m pytest -q
KICAD_ISSUE23403_FIXTURE=/workspace/work/qualification/upstream/issue23403 KICAD10_APPRUN=/workspace/work/qualification/kicad10/squashfs-root/AppRun .venv/bin/python -m unittest discover -q
.venv/bin/python -m compileall .
git diff --check
git status --short
```

Pytest: **107 passed, 50 subtests passed**, no skips with both qualification variables supplied. Unittest: **107 tests, OK**. Previous baseline: 102 passing tests; five independent qualification tests added. Early integration-test assertions were corrected to account for KiCad-created session sidecars and single-root XML naming; neither was a product implementation defect.

No material implementation defect or architecture contradiction was found in these cases. Remaining limits: Python 3.11, Windows, native Kubuntu, network filesystems, hot reload, larger electrically populated projects, and physical power-loss behavior are unverified. No ERC-clean, comprehensive KiCad-version, production-readiness, or live-customer-use claim follows. Recommended next action: independent ChatGPT review of this qualification evidence and its stated limits.
