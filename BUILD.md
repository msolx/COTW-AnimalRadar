# Windows x64 build instructions

## Prerequisites

- Windows 10 or 11 x64.
- Python **3.12 x64** with the Python launcher (`py`). Other versions may work but are not the recorded release build environment.
- Internet access to install the listed Python dependencies. Building or testing does not require a game installation, saved population, administrator rights, or access to a game process.
- A writable checkout directory. Do not copy this repository into the original game's archives.

All application settings live in `config.py` or the UI's saved local settings. The application has no argparse command-line interface.

## Install dependencies

From the repository root in PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-build.txt
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

`requirements-build.txt` pins PyInstaller **6.22.3** and hooks **2026.9**. The application runtime dependency is PySide6-Essentials **6.8.3** (and its matching shiboken6 dependency). Do not execute downloaded third-party mod binaries to build this project.

## Test without reading a game

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -q
```

The Windows API, memory contents and population data used by the unit tests are synthetic/mocked. UI tests use Qt's offscreen platform. A Chinese-font check may be skipped if the optional system font is unavailable. Review output; a skip is not a pass for that feature.

## Produce the application

```powershell
.\.venv\Scripts\python.exe -m PyInstaller --clean --noconfirm COTW_AnimalRadar.spec
```

Expected layout:

```text
dist/COTW_AnimalRadar/
    COTW_AnimalRadar.exe
    _internal/
        python312.dll
        PySide6/
        data/
        offsets/
        licenses/
        icons/
        ...
```

The exact file list is determined by PyInstaller's dependency hooks. `_find_resource()` supports the bundled `_internal` location as well as external resource directories. Never distribute only the EXE.

The spec uses onedir, windowed mode, optimization level 0 and **UPX disabled**. It does not request administrator elevation, use obfuscation, or install a driver. The build is not Authenticode-signed by this repository. PE version metadata is from `version_radar.txt`, and the project icon is `icons/radar.ico`.

The runtime source entry is `main.py`; it passes `config.FIELD_TEST_SOURCE` explicitly to `MainWindow`. Do not replace it with a bare mock-default `MainWindow()` call when making a release.

## Make a source-review distribution

For the source link requested by Nexus support, share the public Git repository URL. The repository contains no compiled EXE or bundled game data. It does contain the original application source and the data/offset definitions needed for review.

For a binary ZIP, copy README/third-party notices and the project LICENSE into the generated onedir output if needed, preserve all `_internal` files, then ZIP that directory. License texts are already collected by the spec. Do not copy the parent development workspace, any `.git` from another project, saves, logs, status JSON, or credentials into it.

Calculate hashes of the **final** ZIP and EXE:

```powershell
Get-FileHash .\dist\COTW_AnimalRadar\COTW_AnimalRadar.exe -Algorithm SHA256
```

Any new build may have different EXE/ZIP bytes due to environment and packaging metadata. These instructions support rebuilding and code inspection; they do **not** promise a bit-for-bit identical executable or an antivirus result.

For the examined v1.1.1 artifact hashes and the source comparison, see [docs/SOURCE_PROVENANCE.md](docs/SOURCE_PROVENANCE.md). A rebuilt file's hash must not be represented as the old uploaded file's hash.

## Review boundaries

- `memory/` and `services/live.py`: standard user-mode, read-only process access with verified/candidate profiles, experimental hash fallback and structure checks.
- `services/overlay_windows.py`: window discovery, the independent overlay/window handling; no game rendering hook.
- `services/population_file.py`: read-only SAVE/ADF population parser with stable-file checks.
- No Solo Helper modules, archive patcher, teleportation, pressure editor or memory writer are included.
- The local unit test result is not a substitute for a fresh-machine installation check or real-game validation. A code review or build does not clear a Nexus quarantine automatically.

## v1.1.1 main-window activation

QtNetwork is part of PySide6-Essentials and is bundled for QLocalServer/QLocalSocket local IPC; no new pip dependency or Internet listener is used. Seven single-instance tests use local sockets, child Python processes and Qt test windows without accessing the game. Close the previous v1.1.0 instance once before running the new build.

## Released source versus current documentation

For the already-published binary, check out **v1.1.1**. The `docs-2026-10-28` snapshot changes documentation, comments and the project author metadata only. Published tags/assets were not rebuilt or replaced; current source attribution applies to future builds. Artifact identities and the scope of tests are in [SOURCE_PROVENANCE.md](docs/SOURCE_PROVENANCE.md).
