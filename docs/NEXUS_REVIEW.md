# Nexus review information — v1.1.1

This page describes the public release and its review material. Personal email drafts and support correspondence are kept locally, not in this repository. Providing source is not a claim of Nexus approval or antivirus clearance.

- Mod page: https://www.nexusmods.com/thehuntercallofthewild/mods/1194
- Published file: https://github.com/msolx/COTW-AnimalRadar/releases/tag/v1.1.1
- Runtime source (fixed release tag): https://github.com/msolx/COTW-AnimalRadar/tree/v1.1.1
- Build instructions (fixed tag): https://github.com/msolx/COTW-AnimalRadar/blob/v1.1.1/BUILD.md
- Corrected artifact provenance (fixed documentation tag): https://github.com/msolx/COTW-AnimalRadar/blob/docs-2026-10-28/docs/SOURCE_PROVENANCE.md
- Per-module comparison (fixed documentation tag): https://github.com/msolx/COTW-AnimalRadar/blob/docs-2026-10-28/docs/SOURCE_COMPARISON.json
- Validation scope (fixed documentation tag): https://github.com/msolx/COTW-AnimalRadar/blob/docs-2026-10-28/docs/VALIDATION_v1.1.1.md
- Technical operations/limits (fixed documentation tag): https://github.com/msolx/COTW-AnimalRadar/blob/docs-2026-10-28/docs/TECHNICAL.md

## Artifact identity

File: `COTW_AnimalRadar_v1.1.1.zip`

ZIP SHA-256: `6db2753ecb4449e93608d51963fd0ad2c3789a661bf3a8ce5cbc543f1deab2ef`

EXE SHA-256: `cd9595711125060108babc87da9c7bfb1f9bf2c4cbca3c3667e3e69bd3514104`

The local ZIP matches the GitHub asset digest/size, and all 26 embedded application modules match the release-tag source. This review did not execute the EXE or retest game features; the linked validation record distinguishes earlier source tests from released-binary checks.

## Actual operation

This application uses read-only Windows process APIs and an independent Qt overlay. It does not write game memory or edit game saves. Positions are approximate 50 m regions. Optional saved-population attributes are joined/estimated, not universally verified live fields. v1.1.1 uses current-user local IPC for window activation.

Single-player use only. Compatibility with unverified builds/channels is experimental. No DLL injection, drivers, game-function hooks, remote game-function execution or protection bypass is implemented. The Windows distribution uses Python 3.12 x64, PySide6-Essentials 6.8.3 and PyInstaller 6.22.3 in onedir mode without UPX.

No personal settings, saves, diagnostics or generated game resources are required in the public source. Rebuilt bytes may differ. Current source attribution changes do not rewrite metadata or license files inside the existing release ZIP.
