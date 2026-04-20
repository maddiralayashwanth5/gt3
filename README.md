# remote-desktop-webrtc

Minimal WebRTC remote desktop with:

- screen streaming over a WebRTC video track
- system audio streaming over a WebRTC audio track
- keyboard and mouse control over a WebRTC DataChannel
- Dockerized signaling, coturn, and LiveKit services

This repo is intentionally small. To keep it runnable immediately, the **minimal working media path is direct WebRTC between the browser and the Python target agent**, while **LiveKit is included in Docker** to match the requested deployment shape and to give you a clean starting point for moving media through an SFU later.

## Repository

```text
remote-desktop-webrtc/
├── docker-compose.yml
├── README.md
├── server/
│   ├── coturn/turnserver.conf
│   ├── livekit/livekit.yaml
│   └── signaling/
│       ├── package.json
│       └── server.js
├── shared/protocol.json
├── target-agent/
│   ├── agent.py
│   ├── audio_capture.py
│   ├── input_control.py
│   ├── requirements.txt
│   └── screen_capture.py
└── viewer/
    ├── index.html
    └── viewer.js
```

## Quick start

### 1. Start infrastructure

```bash
cd remote-desktop-webrtc
docker compose up
```

This starts:

- signaling server on `http://13.205.19.192:8080`
- coturn on `3478` and `5349`
- LiveKit on `7880` and `7881`

### 2. Run the target agent on the machine you want to control

The target agent must run on the real desktop machine because it needs local access to:

- the screen
- the system audio capture device
- the OS input APIs

Install Python dependencies:

```bash
cd remote-desktop-webrtc/target-agent
python3 -m pip install -r requirements.txt
```

List audio devices:

```bash
python3 agent.py --list-audio-devices
```

Run the agent:

```bash
python3 agent.py \
  --room demo \
  --signaling-url ws://13.205.19.192:8080/ws \
  --system-audio-device 3
```

## Portable EXE target agent

If you only want to send a single file to the target machine, package the Windows target agent as an `.exe`.
The EXE bundles Python and dependencies, so the target machine does not need Python installed.

Build it on a Windows machine:

```powershell
cd remote-desktop-webrtc\target-agent
.\build-exe.ps1
```

Output:

```text
target-agent\dist\remote-desktop-agent.exe
```

Then send only that `.exe` to the target Windows machine and run:

```powershell
.\remote-desktop-agent.exe --list-audio-devices
.\remote-desktop-agent.exe --room demo --signaling-url ws://13.205.19.192:8080/ws --system-audio-device 3
```

If the target uses the default room and server, it can run with no arguments:

```powershell
.\remote-desktop-agent.exe
```

### Build the EXE from macOS

macOS cannot directly build a reliable Windows EXE for this stack. Use the included GitHub Actions workflow instead:

1. Push this repo to GitHub.
2. Open `Actions`.
3. Run `Build target EXE`.
4. Download the `remote-desktop-agent-windows` artifact.
5. Send only `remote-desktop-agent.exe` to the target machine.

Notes:

- The `.exe` is for Windows targets.
- You should build the `.exe` on Windows for best compatibility.
- The target machine needs a working system-audio capture endpoint if you want app/system audio streamed to the viewer.

## Target package from macOS

From macOS you cannot reliably build a Windows `.exe`, but you can build a target-only source zip package:

```bash
cd remote-desktop-webrtc
./package-target.sh
```

This source package requires Python on the target. Prefer the EXE workflow above when the target should not need Python.

Send this file to the target only if Python is allowed there:

```text
dist/remote-desktop-target-agent.zip
```

On the Windows target, unzip it, open PowerShell in the folder, then run:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\install-windows.ps1
.\list-audio-devices.ps1
.\run-agent.ps1
```

### 3. Open the viewer

Open:

```text
http://13.205.19.192:8080/?room=demo
```

Click `Connect`, then click the remote video to send keyboard input.

## AWS EC2 notes

- Attach an Elastic IP to the EC2 instance.
- Open security-group inbound rules for:
  - `8080/tcp`
  - `3478/tcp`
  - `3478/udp`
  - `5349/tcp`
  - `7880/tcp`
  - `7881/tcp`
  - `50000-60000/udp`
- For production TURN on EC2, set an external IP in coturn if your instance is behind NAT.
- For HTTPS/WSS in production, place Nginx or ALB in front of the signaling server and enable TLS.

## Audio routing notes

### System audio capture

`--system-audio-device` should point to a loopback or monitor input:

- Windows: `Stereo Mix`, `VB-Cable`, or a WASAPI loopback-compatible device
- Linux: a PulseAudio or PipeWire monitor source
- macOS: `BlackHole` or another loopback device

## Notes

- The code uses WebRTC media tracks for audio/video and a DataChannel for control.
- The signaling server only handles room join, SDP relay, and ICE relay.
- This is the smallest useful baseline, not a hardened production remote access product.
