# Published release provenance — v1.1.1

Checked on 2026-10-28 against the actual **standalone GitHub Release**, not the earlier Toolkit distribution.

| Item | Identity |
| --- | --- |
| Release | [v1.1.1](https://github.com/msolx/COTW-AnimalRadar/releases/tag/v1.1.1) |
| ZIP | `COTW_AnimalRadar_v1.1.1.zip` (37194009 bytes) |
| ZIP SHA-256 | `6db2753ecb4449e93608d51963fd0ad2c3789a661bf3a8ce5cbc543f1deab2ef` |
| EXE SHA-256 | `cd9595711125060108babc87da9c7bfb1f9bf2c4cbca3c3667e3e69bd3514104` |
| Runtime source | [v1.1.1](https://github.com/msolx/COTW-AnimalRadar/tree/v1.1.1) |
| Source commit | `88c56e59ac0950803257050548c9c6eeb2493a1b` |

## What was checked

1. The locally retained release ZIP exists and matches the GitHub asset's reported SHA-256 and byte size. A new download was not needed; the digest establishes which file was examined.
2. ZIP CRC passed. The EXE was extracted from that ZIP and hashed separately.
3. All **26 embedded application modules** match the runtime source at the release tag by bytecode, names, flags, exception tables and recursive constants. Source paths/line tables are ignored. Per-module results are in [SOURCE_COMPARISON.json](SOURCE_COMPARISON.json).

This is a static source/binary comparison, not a byte-identical rebuild or antivirus certification. The EXE was not executed and real-game features were not retested during this documentation review.

## Tests and their scope

The existing v1.1.1 record reports **117 tests passed**, a successful source build, a native Windows window test and a packaged-EXE minimize/relaunch/restore/normal-close test. Those are previously recorded results, not tests rerun on the EXE during this documentation review. They do not validate real-game behavior on every platform/build. See [versioned validation](VALIDATION_v1.1.1.md).

The older [v1.1.0 validation](VALIDATION_v1.1.0.md) is historical and is not the current release record.

## Documentation and attribution update

The published release tags, ZIPs and EXEs are unchanged. The current documentation snapshot is tagged `docs-2026-10-28`; it updates comments and the project's own LICENSE/PE attribution to **msolx**, with the author's confirmation. Third-party notices are preserved.

The published EXEs still contain their original version metadata; the source metadata correction applies to future builds. Rebuilding current main is not the way to reproduce the recorded EXE metadata: use the runtime release tag above. The documentation snapshot is not a new binary release.

Local diagnostics, email drafts, game resources and private development history are not included in this source repository. See [technical details](TECHNICAL.md) for actual memory/file operations and compatibility limits.
