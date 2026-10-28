# Technical details — current application v1.1.1

For player instructions, see [README](../README.md). Hashes and binary/source correspondence are kept in [release provenance](SOURCE_PROVENANCE.md).

## Memory and file operations

Read-only process access is `PROCESS_QUERY_INFORMATION | PROCESS_VM_READ`; no game-memory writer is included. The application reads loaded entities and uses a default 50 m grid. Optional population joins use weight, score and appearance seed to require a unique local record; sex/score are joined, fur/difficulty/medals are estimates. The camera arrow is not independently verified body heading. A 19-reserve catalog is not evidence that every reserve was separately calibrated.

The v1.1.1 duplicate-launch path uses QLockFile and current-user QLocalServer IPC. It restores the existing Qt window without adding another scanner; it does not open an Internet listener or modify the game window. Windows can still decline foreground focus.

Neither tool implements DLL injection, kernel drivers, remote game-function execution or protection bypass. A single-player checkbox is a user confirmation, not automatic multiplayer detection. If Windows/game protections deny access, stop.

## Compatibility and local paths

The existing field observations concern game build 25131233 (EXE `89dbab025114090c91a63ae7f0533ee84eee3c48f4b8543224b359c31b794c22`). Build 26051119 (`33c8306e52c5541a5b87e4af576f4149f3da0c23b36775372ec6c41adbab73ca`) is a candidate, not fully observed feature compatibility.

The candidate's exact radar profile uses experimental core positions only; health, camera-heading and identity fields are disabled. Other unknown hashes can reuse an older profile, including its fields. That fallback does not verify field semantics in a new executable.

Installation discovery supports running-game/Steam-library information, common paths and saved custom game directories. Save discovery currently looks under Documents/Avalanche Studios/COTW/Saves and selects a recently modified numeric account folder. This is a heuristic; it is not guaranteed for Epic/custom save layouts or multiple accounts. Store detection and memory-layout compatibility are separate concerns.

Source/build dependencies and commands are in [BUILD.md](../BUILD.md). Synthetic tests, successful compilation and binary comparison are not substitutes for clean-machine or real-game acceptance. Logs and configuration may contain private paths/coordinates and should remain local.
