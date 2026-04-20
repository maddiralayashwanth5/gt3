Remote Desktop Target Agent

This package runs on the target desktop machine.

Windows quick start:
1. Install Python 3.11+ from https://www.python.org/downloads/windows/
2. Install/configure the mic injection audio endpoint, for example VB-CABLE.
3. Open PowerShell in this folder.
4. Run: Set-ExecutionPolicy -Scope Process Bypass
5. Run: .\install-windows.ps1
6. Run: .\list-audio-devices.ps1
7. Edit config.json if needed.
8. Run: .\run-agent.ps1

Mic injection:
- The viewer's microphone is written into the mic injection output device.
- With VB-CABLE, the agent writes to "CABLE Input".
- Target apps select "CABLE Output" as their microphone.

Default server:
ws://13.205.19.192:8080/ws
