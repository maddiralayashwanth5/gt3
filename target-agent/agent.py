from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys

from aiortc import RTCPeerConnection, RTCSessionDescription
from aiortc.sdp import candidate_from_sdp
from websockets.asyncio.client import connect

from audio_capture import (
    SystemAudioTrack,
    list_input_devices,
    list_output_devices,
)
from input_control import apply_input
from screen_capture import ScreenVideoTrack


logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")


def read_config(path: str) -> dict:
    if not path or not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def env_int(name: str) -> int | None:
    value = os.environ.get(name)
    return int(value) if value not in (None, "") else None


def parse_candidate(payload: dict):
    candidate = payload.get("candidate")
    if not candidate:
        return None
    parsed = candidate_from_sdp(candidate.replace("candidate:", "", 1))
    parsed.sdpMid = payload.get("sdpMid")
    parsed.sdpMLineIndex = payload.get("sdpMLineIndex")
    return parsed


class TargetAgent:
    def __init__(self, signaling_url: str, room: str, system_audio_device: int | None) -> None:
        self.signaling_url = signaling_url
        self.room = room
        self.system_audio_device = system_audio_device
        self.pc: RTCPeerConnection | None = None
        self.ws = None
        self.screen_track: ScreenVideoTrack | None = None
        self.system_audio_track: SystemAudioTrack | None = None

    async def send(self, message: dict) -> None:
        await self.ws.send(json.dumps(message))

    async def reset_peer(self) -> None:
        if self.pc:
            await self.pc.close()
            self.pc = None
        if self.screen_track:
            self.screen_track.stop()
            self.screen_track = None
        if self.system_audio_track:
            self.system_audio_track.stop()
            self.system_audio_track = None

    async def create_peer(self) -> RTCPeerConnection:
        await self.reset_peer()
        pc = RTCPeerConnection()
        self.screen_track = ScreenVideoTrack()
        self.system_audio_track = SystemAudioTrack(device_index=self.system_audio_device)

        pc.addTrack(self.screen_track)
        pc.addTrack(self.system_audio_track)

        @pc.on("datachannel")
        def on_datachannel(channel) -> None:
            if channel.label != "input":
                return

            @channel.on("message")
            def on_message(message: str) -> None:
                try:
                    apply_input(json.loads(message))
                except Exception:
                    logging.exception("failed to apply input")

        @pc.on("track")
        def on_track(track) -> None:
            logging.info("received %s track from viewer; ignoring while source audio streaming is enabled", track.kind)

        @pc.on("icecandidate")
        async def on_icecandidate(candidate) -> None:
            if candidate is None:
                return
            await self.send(
                {
                    "type": "ice-candidate",
                    "candidate": {
                        "candidate": f"candidate:{candidate.to_sdp()}",
                        "sdpMid": candidate.sdpMid,
                        "sdpMLineIndex": candidate.sdpMLineIndex,
                    },
                }
            )

        self.pc = pc
        return pc

    async def handle_message(self, message: dict) -> None:
        msg_type = message.get("type")

        if msg_type == "joined":
            logging.info("joined room=%s peer_present=%s", self.room, message.get("peerPresent"))
            return

        if msg_type == "offer":
            pc = await self.create_peer()
            await pc.setRemoteDescription(RTCSessionDescription(sdp=message["sdp"], type="offer"))
            answer = await pc.createAnswer()
            await pc.setLocalDescription(answer)
            await self.send({"type": "answer", "sdp": pc.localDescription.sdp})
            logging.info("answer sent")
            return

        if msg_type == "ice-candidate" and self.pc:
            candidate = parse_candidate(message.get("candidate", {}))
            if candidate:
                await self.pc.addIceCandidate(candidate)
            return

        if msg_type == "peer-left":
            logging.info("viewer disconnected")
            await self.reset_peer()
            return

        if msg_type == "error":
            logging.error("signaling error: %s", message.get("message"))

    async def run(self) -> None:
        async with connect(self.signaling_url) as websocket:
            self.ws = websocket
            await self.send({"type": "join", "room": self.room, "role": "target"})
            async for raw in websocket:
                await self.handle_message(json.loads(raw))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Minimal WebRTC remote desktop target agent")
    app_dir = os.path.dirname(sys.executable if getattr(sys, "frozen", False) else __file__)
    default_config = os.path.join(app_dir, "config.json")
    parser.add_argument("--config", default=os.environ.get("AGENT_CONFIG", default_config))
    parser.add_argument("--room", default=os.environ.get("ROOM", "demo"))
    parser.add_argument("--signaling-url", default=os.environ.get("SIGNALING_URL", "ws://13.205.19.192:8080/ws"))
    parser.add_argument("--system-audio-device", type=int, default=env_int("SYSTEM_AUDIO_DEVICE"))
    parser.add_argument("--list-audio-devices", action="store_true")
    args = parser.parse_args()
    config = read_config(args.config)

    for key in ("room", "signaling_url", "system_audio_device"):
        if key in config and getattr(args, key) in (None, "", parser.get_default(key)):
            setattr(args, key, config[key])

    return args


async def async_main() -> None:
    args = parse_args()
    if args.list_audio_devices:
        print("Input devices:")
        for device in list_input_devices():
            print(f"  {device['index']}: {device['name']}")
        print("Output devices:")
        for device in list_output_devices():
            print(f"  {device['index']}: {device['name']}")
        return

    agent = TargetAgent(
        signaling_url=args.signaling_url,
        room=args.room,
        system_audio_device=args.system_audio_device,
    )
    await agent.run()


if __name__ == "__main__":
    asyncio.run(async_main())
