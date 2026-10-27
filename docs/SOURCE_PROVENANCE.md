# v1.1.0 source and executable provenance

Reviewed artifact: `COTW_Toolkit/COTW_AnimalRadar.exe` from the author's locally supplied Toolkit directory, examined 2026-10-28.

EXE SHA-256: `d7612ce5eecdc0053ff1931729fae1efb16fc8cfc9370ab9411f1b52f59dd39c`.

The executable is not committed. No archive hash is asserted: an uploaded ZIP may be repackaged, and its hash must be calculated from that final upload.

All 26 embedded application modules match the published runtime source by Python bytecode, names, flags, exception tables and recursive constants, ignoring source paths/line metadata. See [SOURCE_COMPARISON.json](SOURCE_COMPARISON.json). This is semantic-code comparison, not a byte-for-byte rebuild guarantee or antivirus certification.

Data, offset profiles, icons and notices are copied from the examined distribution. Tests and build support are additional review materials. Current game resources, generated modifications, settings, save files, diagnostics and binaries are excluded. Previous v1.0.0 records remain in repository history.

The current source-build instructions are in [BUILD.md](../BUILD.md). An executable/hash compatibility gate is not proof of data-layout compatibility. Candidate or fallback behavior remains experimental.

The radar uses standard read-only Windows process APIs and an independent Qt overlay. No Helper code, memory writer, game assets, saves or private development history is included. Population attributes are optional read-only joins/estimates, not live-material inspection.

Separated-source tests and successful rebuild: [VALIDATION_v1.1.0.md](VALIDATION_v1.1.0.md).
