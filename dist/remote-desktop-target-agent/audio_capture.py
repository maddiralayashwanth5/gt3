from __future__ import annotations

import asyncio
from fractions import Fraction

from aiortc import MediaStreamTrack
from av import AudioFrame
import pyaudio


SAMPLE_RATE = 48000
CHANNELS = 1
FRAME_SAMPLES = 960


def list_input_devices() -> list[dict]:
    pa = pyaudio.PyAudio()
    devices = []
    try:
        for index in range(pa.get_device_count()):
            info = pa.get_device_info_by_index(index)
            if info.get("maxInputChannels", 0) > 0:
                devices.append({"index": index, "name": info["name"]})
    finally:
        pa.terminate()
    return devices


def list_output_devices() -> list[dict]:
    pa = pyaudio.PyAudio()
    devices = []
    try:
        for index in range(pa.get_device_count()):
            info = pa.get_device_info_by_index(index)
            if info.get("maxOutputChannels", 0) > 0:
                devices.append({"index": index, "name": info["name"]})
    finally:
        pa.terminate()
    return devices


class SystemAudioTrack(MediaStreamTrack):
    kind = "audio"

    def __init__(self, device_index: int | None = None) -> None:
        super().__init__()
        self.device_index = device_index
        self.pa = pyaudio.PyAudio()
        self.stream = self.pa.open(
            format=pyaudio.paInt16,
            channels=CHANNELS,
            rate=SAMPLE_RATE,
            input=True,
            input_device_index=device_index,
            frames_per_buffer=FRAME_SAMPLES,
        )
        self.timestamp = 0

    async def recv(self) -> AudioFrame:
        loop = asyncio.get_running_loop()
        data = await loop.run_in_executor(
            None,
            lambda: self.stream.read(FRAME_SAMPLES, exception_on_overflow=False),
        )
        frame = AudioFrame(format="s16", layout="mono", samples=FRAME_SAMPLES)
        frame.planes[0].update(data)
        frame.sample_rate = SAMPLE_RATE
        frame.pts = self.timestamp
        frame.time_base = Fraction(1, SAMPLE_RATE)
        self.timestamp += FRAME_SAMPLES
        return frame

    def stop(self) -> None:
        try:
            self.stream.stop_stream()
            self.stream.close()
            self.pa.terminate()
        finally:
            super().stop()
