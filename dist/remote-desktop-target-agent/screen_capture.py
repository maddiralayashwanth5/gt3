from __future__ import annotations

import asyncio

from aiortc import VideoStreamTrack
from av import VideoFrame
import mss


class ScreenVideoTrack(VideoStreamTrack):
    """Captures the primary monitor and emits frames directly into WebRTC."""

    def __init__(self, fps: int = 15) -> None:
        super().__init__()
        self.fps = max(1, fps)
        self.sct = mss.mss()
        self.monitor = self.sct.monitors[1]
        self.width = int(self.monitor["width"])
        self.height = int(self.monitor["height"])

    async def recv(self) -> VideoFrame:
        await asyncio.sleep(1 / self.fps)
        pts, time_base = await self.next_timestamp()
        shot = self.sct.grab(self.monitor)
        frame = VideoFrame.from_ndarray(shot, format="bgra")
        frame.pts = pts
        frame.time_base = time_base
        return frame

    def stop(self) -> None:
        try:
            self.sct.close()
        finally:
            super().stop()
