# COTW Animal Radar

A standalone, read-only animal exploration radar for **theHunter: Call of the Wild** on Windows. Shows nearby **loaded** animals as approximate areas, with species filters, distances, camera heading, and an optional transparent desktop overlay.

This repository contains the **radar only**. It does not contain Solo Helper, teleportation, movement/weight modifications, hunting-pressure modifications, memory writers, or the original development repository's history.

[中文说明](docs/README.zh-CN.md) · [Build instructions](BUILD.md) · [Source/binary relationship](docs/SOURCE_PROVENANCE.md) · [Third-party notices](THIRD_PARTY_NOTICES.md)

**v1.1.1:** launching the same installation again restores and activates its existing main window instead of silently exiting. This uses a current-user local named pipe, opens no TCP port, and creates no second game scanner. Close a running v1.1.0 instance once before upgrading. Windows foreground policy can still require using the taskbar/Alt+Tab; input is never simulated or forcibly attached.

## Supported environment

- Windows 10/11 x64; single-player use. Steam/Epic/custom installation directories can be detected or selected; this is not a claim of all-channel live validation.
- Tested game Steam build **25131233**, executable SHA256:
  `89dbab025114090c91a63ae7f0533ee84eee3c48f4b8543224b359c31b794c22`.
- Development/build: Python **3.12 x64** and `PySide6-Essentials==6.8.3`.
- v1.1.0 adds experimental compatibility attempts for other executable hashes. Steam build **26051119** (`33c8306e52c5541a5b87e4af576f4149f3da0c23b36775372ec6c41adbab73ca`) is a candidate layout: its exact profile enables experimental core positions only, with health, camera heading and identity fields disabled. Other unknown hashes can fall back to the older profile; that does not validate its field semantics for the new executable. A hash match or successful read is not a complete compatibility test.

## Features and limits

- Loaded animal positions, species filtering, horizontal distances, health/death status where the configured build supports them, and refresh intervals of 1/2/5 seconds.
- Default **50 m exploration grid**: same-species animals in an area are grouped. A marker represents an area, not an animal's precise body location or an aiming point. Unloaded animals are not reserve-wide live observations.
- Optional independently positioned, resized and background-transparent overlay; no game injection or rendering hook.
- A camera/view-direction arrow. It is not a directly verified character-body heading field.
- A 19-reserve species catalog. Reserve selection is manual. North-up is available for all catalog reserves based on a shared-axis assumption; the original individual direction checks covered Layton and Medved, not a claim of separately calibrated evidence for every reserve.
- Optional, read-only population-file attribute matching. Sex/score are joined only when the live weight, score and appearance seed uniquely match one saved record. Fur and difficulty are community estimates; medal thresholds predict **potential** awards, not final harvest results. Missing or ambiguous data remains unknown.
- English/Chinese UI selection. Operating-system language and saved settings are used by the UI.

The tool does not implement a complete reserve background map or a verified reserve-wide live animal layer. It does not bypass protected memory, modify game files, edit population saves, inject DLLs, install drivers, or disable protection. Local configuration/status files are written beside the application, so use a user-writable folder.

## Run from source

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

`main.py` explicitly starts the real-game/field-test source with experimental fallback. Merely importing `config.py` in a source environment still defaults to mock for developer/test callers. The mock data source is labeled and exists for offline tests; it is not game verification.

1. Start the game through its normal launcher and enter a **single-player** reserve.
2. Run `main.py`, or run the built `COTW_AnimalRadar.exe` after extracting its **entire** directory.
3. Select and confirm the correct reserve. Do not mistake a retained manual selection for automatic map detection after changing reserves.
4. Select a species and radar range; enable north-up if appropriate.
5. Enable the optional attribute-matching control if desired. No valid/unique save match means no reliable trophy prediction; merely enabling the highlight checkbox does not manufacture a score.
6. Borderless Windowed game mode is recommended for the overlay. Exclusive fullscreen/multi-monitor/DPI combinations can behave differently.

Overlay control uses the main-window **Show / Hide Mini-Radar** and **Adjust Mini-Radar** buttons; lock the overlay after positioning it. v1.1.0 does not register global radar hotkeys.

Game and save directories are detected using Steam registry/library information and the Windows Documents location, including registry-based redirection. For multiple numeric save-account directories the current selection uses folder modification time; it is a heuristic, not proof of the active Steam account.

If access is denied or memory structures fail validation, stop and inspect the message. Experimental fallback does not prove that a new executable has the same data layout. Do not disable antivirus, change game protection, force `verified=true`, or substitute random offsets. An empty species result only means no matching loaded animals were detected.

## Build and test

See [BUILD.md](BUILD.md) for exact dependency versions and the packaging command. Python/Qt runtime libraries are bundled into the Windows build; users do not need a separate Python installation, but must keep `_internal` with the executable.

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -q
```

Tests use synthetic memory/population fixtures and headless UI checks. They do not read a real game process, prove compatibility with all computers, or certify an executable as malware-free.

## Safety and distribution

This is an unofficial tool. Read-only access is not a guarantee of game-policy compliance, absence of account risk, compatibility, or freedom from crashes. Use only in single-player. A PyInstaller/unsigned application can receive security or reputation warnings; no antivirus is to be disabled and no bypass is provided. A Nexus quarantine is a request for review, not proof that a file is safe or malicious.

For manual source review, the application flow is `main.py` → `ui/main_window.py` → `services/scanner.py`/`services/live.py` → `memory/process_reader.py`/`memory/animal_reader.py`. Population parsing is in `services/population_file.py` and `services/attribute_resolver.py`. Read-only Windows process rights are `PROCESS_QUERY_INFORMATION | PROCESS_VM_READ`.

No game executables, original game assets, population saves, user Steam identifiers, crash dumps, local credentials or personal diagnostic reports are distributed in this source tree. No application telemetry or memory upload feature is implemented. Do not upload your generated status/configuration files or local population saves as public bug reports.

Project source is under the [MIT License](LICENSE). Third-party data/format references retain their own notices. Qt/PySide libraries have separate license terms; see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

Nexus page: <https://www.nexusmods.com/thehuntercallofthewild/mods/1194>
