# Current source / binary provenance: v1.1.1

Radar-only release, examined 2026-10-28. Source/binary evidence is in [SOURCE_COMPARISON.json](SOURCE_COMPARISON.json); test and packaged-window checks are in [VALIDATION_v1.1.1.md](VALIDATION_v1.1.1.md).

ZIP SHA-256: `6db2753ecb4449e93608d51963fd0ad2c3789a661bf3a8ce5cbc543f1deab2ef`

EXE SHA-256: `cd9595711125060108babc87da9c7bfb1f9bf2c4cbca3c3667e3e69bd3514104`

All 26 embedded application modules match the source by bytecode/names/flags/exception tables/recursive constants, ignoring paths/line tables. This is not a byte-identical rebuild or malware-free guarantee.

Only source, synthetic tests, public data/offset definitions, build support and license notices are published. Local test logs, status/settings, game archives/populations, Helper code/writers and private development history are excluded. Prior release evidence is retained in Git history and version-specific validation documents.

Build instructions: [BUILD.md](../BUILD.md). Runtime source entry remains main.py with the real field-test data source; duplicate launch performs local activation and exits before constructing MainWindow/scanner.
