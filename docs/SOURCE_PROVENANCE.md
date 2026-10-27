# Source provenance and Nexus manual review

This is an independently initialized **radar-only source repository** for review of the COTW Animal Radar v1.0.0 distribution. It does not include the parent workspace's Git history, other tools, executable dependencies, saved populations, local identifiers, or private diagnostic files.

## Distribution examined

The local release manifest records the package assembled on **2026-10-27 at 16:53:55 +0800**:

| Artifact | SHA256 |
|---|---|
| `COTW_AnimalRadar_v1.0.0.zip` | `50c9d6a7e5731c1a1d40a90baaecea2c23d6e79f0ec50257c0134d3474276756` |
| Its `COTW_AnimalRadar.exe` | `daaadb93f21a851f826bec0b162b28365be4394a646a9d0c7b2e5f26d21d4f02` |

These identify the locally available release that corresponds to the v1.0.0 review preparation. The Nexus-hosted file was not downloaded and independently hashed in this source-preparation step. If a different file was uploaded, these hashes must not be claimed to identify it.

An earlier, superseded package used a mock-default entry. This examined package and the source here explicitly select `config.FIELD_TEST_SOURCE` in `main.py`. The development default when importing config directly remains separate. The public-release test protects against reintroducing the old entry mistake.

## Application-module comparison

Before copying, the release ZIP's EXE was checked against the local dist EXE and found byte-identical. Its PyInstaller archive was then read **without executing it**.

The main entry plus 24 embedded project modules were compared with freshly compiled copies of their source. The comparison checked Python bytecode, names, argument flags, exception tables and recursively nested constants, while ignoring filenames and line-number metadata. **All 25 compared application modules matched.**

The per-module result is in [SOURCE_COMPARISON.json](SOURCE_COMPARISON.json). It contains relative module filenames and artifact hashes, not original workstation paths. It does not certify the PyInstaller bootloader or external runtime DLLs as safe and does not replace an antivirus scan.

For this source distribution:

- Application source modules are preserved, including later path detection, i18n and diamond-marker work.
- Tests, English/Chinese documentation, build instructions, full library-license texts and this provenance record are added/organized for public review.
- Only the radar icon is included; unrelated Helper icons/images are omitted.
- Original development notes, handoff documents, logs, probes, captures, saves, status/settings files, build cache, binaries, and the original Git history are not published.
- No game assets are extracted or distributed. The data tables and read-only versioned offsets are part of the radar, with their sources/notices retained.

## Verification performed for this source tree

- **109 radar-focused tests passed** on Windows x64 with Python 3.12 and Qt 6.8.3 after separating the source tree; no Helper test dependencies are required.
- A clean PyInstaller 6.22.3 build of this separated source tree completed successfully with the provided spec on Windows 10 x64, Python 3.12.3 and Qt 6.8.3. This is compilation/packaging verification, not a real-game run or antivirus clearance. Build outputs/logs containing workstation paths are excluded from Git.
- No real-game memory access or Nexus-site modification is performed by these tests or by preparing this source repository.
- Antivirus clearance, absence of account risk and automatic release from Nexus quarantine are **not** asserted.

To rebuild, follow [BUILD.md](../BUILD.md). Rebuilding can produce a different file hash; do not label a new file as the old binary merely because the source is the same.
