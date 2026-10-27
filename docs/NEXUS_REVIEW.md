# Information for Nexus manual review

Mod page: <https://www.nexusmods.com/thehuntercallofthewild/mods/1194>

This repository provides the radar-only application source and build instructions for manual review. The author must send any support request; this repository does not send email or change the Nexus listing.

Suggested message (verify the uploaded hashes before sending):

```text
Subject: Manual review request - COTW AnimalRadar - mod 1194

Hello Nexus Mods Support,

My first uploaded file, COTW AnimalRadar V1.0.0, was quarantined by the
automated safety checks. Could you please review it?

Mod page:
https://www.nexusmods.com/thehuntercallofthewild/mods/1194

Radar-only source code:
https://github.com/msolx/COTW-AnimalRadar

Build instructions are in BUILD.md. The project uses Python 3.12 x64,
PySide6-Essentials 6.8.3 and PyInstaller 6.22.3, in onedir mode without UPX.
The application reads loaded-animal data using standard Windows APIs
and displays an independent Qt overlay. It does not inject a DLL,
install a driver, write game memory or edit game saves.

docs/SOURCE_PROVENANCE.md identifies the locally examined v1.0.0 ZIP
and EXE hashes and describes the application-module source comparison.
No antivirus clearance is claimed. Please let me know if you need
additional information about the build or file.

Thank you.
```

Providing source does not automatically remove quarantine. Do not describe a failed or unavailable antivirus scan as a clean result, and do not ask users to disable security tools.
