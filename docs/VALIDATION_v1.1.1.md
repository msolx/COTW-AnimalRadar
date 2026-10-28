# v1.1.1 validation and change scope

Date: 2026-10-28. Radar-only maintenance release; Helper remains unchanged.

## Behavior

Repeated launch of the same installation sends a fixed activation request to the existing main process, then exits with code 0. The original process restores a minimized/hidden main window, preserves maximized state and relocates a completely offscreen window. It does not create a second scanner.

QLockFile remains the ownership guard. QLocalServer uses current-user local named-pipe IPC; it opens no TCP/Internet listener. An old v1.1.0 instance has no IPC listener, so close it normally once when upgrading. Malformed IPC requests are rejected, and a missing legacy listener gives an explicit user-visible message.

Foreground transfer uses Windows AllowSetForegroundWindow and SetForegroundWindow, plus Qt activation/notification. No input simulation, AttachThreadInput, game hooks or game writes are introduced. Windows may decline foreground activation in other environments; the window is restored and the taskbar can alert the user.

## Actual results

- Separated-source suite: **117 tests, 0 failures/errors, 0 skips**.
- Seven focused tests include actual secondary processes, minimized-window restoration, repeat requests, a delayed primary listener, legacy lock preservation, channel cleanup/restart, partial/malformed commands and maximized/offscreen recovery. They do not access a game.
- Native Windows QWidget test: minimized before=True, restored visible=True, foreground after=True, one activation, secondary code 0. No game access in this fixture.
- Actual packaged EXE test in an isolated copy: minimized before=True, restored visible=True, foreground after=True, original process alive, secondary code 0, normal main-window close code 0. No game was running for this test. No force-kill was needed.
- PyInstaller source build succeeded using Python 3.12.3 x64, PySide6-Essentials 6.8.3 and PyInstaller 6.22.3; QtNetwork.pyd and Qt6Network.dll included for local IPC.
- 26 embedded application modules match the source by code/constants comparison. ZIP CRC passed; directed privacy scan had no hits; no settings, logs, saves, game assets or private history packaged.

No antivirus clearance or every-desktop/Dock compatibility guarantee is asserted. This release does not change game offsets, radar coordinates, population matching or Helper memory writers. Existing candidate-build limitations remain.

## Artifact identity

- ZIP: COTW_AnimalRadar_v1.1.1.zip (37194009 bytes)
- ZIP SHA-256: `6db2753ecb4449e93608d51963fd0ad2c3789a661bf3a8ce5cbc543f1deab2ef`
- EXE SHA-256: `cd9595711125060108babc87da9c7bfb1f9bf2c4cbca3c3667e3e69bd3514104`

See SOURCE_COMPARISON.json for per-module comparison and BUILD.md to rebuild. Rebuilt hashes may differ.

API references: [Qt local-server access options](https://doc.qt.io/qt-6/qlocalserver.html), [Windows foreground permission transfer](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-allowsetforegroundwindow).
