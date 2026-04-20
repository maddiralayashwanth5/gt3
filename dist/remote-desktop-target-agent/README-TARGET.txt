Remote Desktop Target Agent

This package runs on the target desktop machine.

Windows quick start:
1. Install Python 3.11+ from https://www.python.org/downloads/windows/
2. Make sure the system-audio capture endpoint is enabled.
3. Open PowerShell in this folder.
4. Run: Set-ExecutionPolicy -Scope Process Bypass
5. Run: .\install-windows.ps1
6. Run: .\list-audio-devices.ps1
7. Edit config.json if needed.
8. Run: .\run-agent.ps1

Default server:
ws://13.205.19.192:8080/ws
