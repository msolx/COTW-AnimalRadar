# Third-party notices and dependencies

## Application source

The project's own source is provided under the MIT License in `LICENSE`. This does not grant rights to redistribute the game, its original assets, saved populations, or other projects' executables.

## Community attribute and trophy tables

`data/attribute_estimates.json` and `data/trophy_thresholds.json` reference:

- Repository: <https://github.com/Pure-Winter-hue/apc-pw>
- Pinned revision: `8f297b5a9d36cfa826a18977dc4bd8c129bfc6ce`
- Referenced configuration: `apc/config/animal_details.json`; fur-seed and read-only population-format research is acknowledged in the corresponding source comments.
- Upstream MIT license: `licenses/apc-pw-MIT.txt`, preserved with its original copyright statements. The upstream LICENSE at the pinned revision was checked when preparing this repository.

The parent project contains unrelated modification/injection features. They are not imported or distributed here. This application implements its own bounded read-only parser and join logic. Community estimates are not official game truth.

## Format research

SAVE/ADF and other format research also references the DECA/Mod Builder lineage:
<https://github.com/RyMaxim/cotw-mod-builder> at `3ac2b0c8ea61c822f47bcdd6ad54f3ab7a65adeb`.
Its MIT notice is retained in `licenses/ModBuilder-MIT.txt`. This radar does not include the parent workspace's archive patcher or Solo Helper.

Public entity-structure research:
<https://gist.github.com/Cvar1984/b8425fd7e1df271509db5af8273a013f>.
It supplied research clues only; this repository does not distribute or run its DMA/FPGA/MemProcFS program. Windows access is independently implemented using ctypes and standard read-only APIs.

## PySide6 / Qt / shiboken6

Runtime Python dependency: `PySide6-Essentials==6.8.3`, with matching `shiboken6`. These are external dependencies, not vendored binaries in this source repository. Qt/PySide use their respective commercial or open-source license terms; this project uses the open-source distribution.

The source repository includes `licenses/LGPL-3.0.txt`, `licenses/GPL-3.0.txt` and a Qt notice. The license texts were obtained from the official `qt/qtbase` repository, tag `v6.8.3`, `LICENSES/LGPL-3.0-only.txt` and `LICENSES/GPL-3.0-only.txt`.

- Qt source: <https://code.qt.io/cgit/qt/qtbase.git/> (v6.8.3).
- PySide/shiboken source: <https://code.qt.io/cgit/pyside/pyside-setup.git/> (v6.8.3).
- Licensing/third-party information: <https://doc.qt.io/qtforpython-6.8/licenses.html>.

Binary distributors must preserve the applicable notices and meet the relevant library/source/replacement obligations for what they ship. An onedir build keeps Qt libraries separate; do not conceal or prevent replacement of those library files. This notice is not a complete compliance certification of an arbitrary binary distribution.

## Python and PyInstaller

Python is an external interpreter and is bundled by PyInstaller only in a binary build. Python's runtime license is separate from this project's MIT license; use the license information supplied with the matching interpreter at <https://docs.python.org/3/license.html> when distributing it.
PyInstaller is a build tool, pinned in `requirements-build.txt`. Its upstream license and bootloader exception apply: <https://pyinstaller.org/en/stable/license.html>.
No Python, Qt, or PyInstaller binaries are committed to this source repository.

Reserve catalog source links are preserved in `data/reserves.json`. No game maps, extracted game textures, or game executable are included.
