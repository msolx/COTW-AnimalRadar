# Manual-review email draft (v1.1.1)

Reply to existing ticket 274634, preserving its original subject, rather than opening a duplicate ticket. Send from the email associated with your Nexus account. Verify the username (filled from the earlier reply as Zacks) and upload the corresponding v1.1.1 file before sending. This draft does not send email.

```text
To: support@nexusmods.com
Subject: Updated manual review request - COTW AnimalRadar v1.1.1 (Mod 1194, ticket 274634)

Hello Nexus Mods Support,

I would like to update my manual-review request for COTW AnimalRadar,
Mod ID 1194. The current maintenance release is v1.1.1, which fixes the
main window not reopening when the user launches the radar again.

Nexus username: Zacks
Mod page: https://www.nexusmods.com/thehuntercallofthewild/mods/1194
Versioned source: https://github.com/msolx/COTW-AnimalRadar/tree/v1.1.1
Build instructions:
https://github.com/msolx/COTW-AnimalRadar/blob/v1.1.1/BUILD.md
Source/binary evidence and test results:
https://github.com/msolx/COTW-AnimalRadar/blob/v1.1.1/docs/VALIDATION_v1.1.1.md

This is the radar-only, read-only application, separate from SoloHelper.
It reads loaded-animal data using standard Windows ReadProcessMemory
and draws an independent Qt overlay. It does not write game memory,
inject DLLs, install drivers, hook game functions or directly edit saves.

The new single-instance activation uses a current-user local Windows named
pipe through Qt. A second launch requests restoration of the existing
window and exits; it does not start another scanner or open a network port.
Normal Windows foreground APIs are used, without simulated input or
protection bypasses. The source includes English/Chinese instructions
and third-party license notices.

The release was built with Python 3.12 x64, PySide6-Essentials 6.8.3 and
PyInstaller 6.22.3 in onedir mode, without UPX. All 117 source tests passed.
The actual packaged EXE was also tested for minimize/relaunch/restore and
normal shutdown on Windows. All 26 embedded application modules match the
published runtime source by bytecode/constants comparison.

File: COTW_AnimalRadar_v1.1.1.zip
ZIP SHA-256:
6db2753ecb4449e93608d51963fd0ad2c3789a661bf3a8ce5cbc543f1deab2ef
EXE SHA-256:
cd9595711125060108babc87da9c7bfb1f9bf2c4cbca3c3667e3e69bd3514104

No antivirus clearance or universal game-version compatibility is claimed.
Could you please review the updated file? If a particular detection or
additional build information is needed, please let me know.

Thank you for your help.

Best regards,
Zacks
```
