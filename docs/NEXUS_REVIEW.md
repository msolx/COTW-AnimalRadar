# Manual review email draft

The author sends this message from the email associated with the Nexus account. Verify the username and upload the corresponding v1.1.0 artifact before sending. This draft does not send email or certify Nexus/antivirus approval.

For radar ticket 274634, reply to the existing support thread and keep its ticket subject rather than opening a duplicate ticket.

```text
To: support@nexusmods.com
Subject: Manual review request - COTW AnimalRadar v1.1.0 (Mod 1194)

Hello Nexus Mods Support,

My previous upload was quarantined by the automated safety checks. I have
prepared an updated v1.1.0 and published its corresponding separated source
and build instructions. Could you please manually review the updated file?

Nexus username: Zacks
Mod page: https://www.nexusmods.com/thehuntercallofthewild/mods/1194

Source code: https://github.com/msolx/COTW-AnimalRadar
Build instructions: https://github.com/msolx/COTW-AnimalRadar/blob/main/BUILD.md
Source/artifact verification:
https://github.com/msolx/COTW-AnimalRadar/blob/main/docs/SOURCE_PROVENANCE.md

This is a read-only exploration radar. It reads loaded-animal data using
standard Windows APIs and draws an independent Qt desktop overlay. It
does not write game memory, inject DLLs, install drivers or modify saves.

The Windows application uses Python 3.12 x64, PySide6-Essentials 6.8.3 and
PyInstaller 6.22.3 in onedir mode, with UPX disabled. The separated source
build was tested successfully. Original game assets, saves, private
settings, diagnostics and credentials are not included in the repository.
Compatibility with unverified game versions is explicitly experimental.

The locally reviewed COTW_AnimalRadar.exe has SHA-256:
d7612ce5eecdc0053ff1931729fae1efb16fc8cfc9370ab9411f1b52f59dd39c

All 26 embedded application modules matched the published runtime source
by bytecode/constants comparison. This is not a claim of byte-identical
rebuilds or antivirus clearance. If the submitted file has a specific
detection, please let me know what additional information is needed.

Thank you for your help.

Best regards,
Zacks
```
