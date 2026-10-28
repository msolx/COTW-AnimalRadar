# COTW AnimalRadar

**v1.1.1 · Windows 10/11 x64 · by msolx**

A read-only exploration radar for *theHunter: Call of the Wild*.

[Download v1.1.1](https://github.com/msolx/COTW-AnimalRadar/releases/tag/v1.1.1) · [中文说明](docs/README.zh-CN.md)

## What it does

- Shows nearby **loaded animals in approximate 50 m areas**, with species filters, counts and distance ranges. These are exploration markers, not exact body positions.
- Provides a small, movable and resizable overlay, plus a main window for filters and details.
- Offers optional sex/score matching and fur/difficulty/medal estimates from local population data. Missing or ambiguous matches stay unknown; predictions are not final harvest results.
- In v1.1.1, launching the same installation again restores its existing main window.

## Install and start

1. Download **COTW_AnimalRadar_v1.1.1.zip** from the Release's **Assets**, not the automatic Source code archive.
2. Extract the entire ZIP to a writable folder. Keep `_internal` and all companion files. Python is not required.
3. Start the game normally and enter a single-player reserve, then run `COTW_AnimalRadar.exe`.
4. Select the current reserve and desired species. Reserve selection is manual; update it when changing maps.
5. Click **Show / Hide Mini-Radar**. Use Borderless Windowed mode; use **Adjust Mini-Radar** to move/resize, then lock it.

Close the old radar before upgrading, extract the full new version, and update desktop/taskbar/Dock shortcuts. Do not replace only the EXE. If the main window is minimized, launch the same EXE again; Alt+Tab is another way to switch to it.

## Optional settings and troubleshooting

- Enable north-up after selecting the reserve. The direction arrow uses the camera view, not a separately verified body-heading field; some candidate game builds do not support it.
- Enable **Attribute trial** and trophy highlighting if you want population-based estimates. A valid save match is required. Automatic save selection can be wrong when multiple accounts or custom save locations exist.
- No matching dots means no matching loaded animals were detected; it does not mean the reserve has none.
- Global overlay hotkeys are not registered. Use the buttons in the main window.

## Before you use it

Recommended for **single-player only**. The radar does not write game memory or edit game saves. Positions are approximate areas and refresh periodically.

Game-version compatibility is **not guaranteed**. Other stores, candidate builds and modified executables use experimental compatibility attempts. A game update can break features. If access or structure checks fail, stop; do not disable security tools or bypass game protection. This unofficial tool is not guaranteed crash-free, risk-free or free from antivirus warnings.

Do not publish your settings, status logs, saves or crash dumps with bug reports unless you have removed private information.

## More information

[Build from source](BUILD.md) · [Technical details](docs/TECHNICAL.md) · [Release provenance](docs/SOURCE_PROVENANCE.md) · [Nexus review information](docs/NEXUS_REVIEW.md)

[MIT license](LICENSE) · [Third-party notices](THIRD_PARTY_NOTICES.md) · [Nexus page](https://www.nexusmods.com/thehuntercallofthewild/mods/1194)
