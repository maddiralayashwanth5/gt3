from __future__ import annotations

import asyncio
from fractions import Fraction
from typing import Iterable

from aiortc import MediaStreamTrack
from av import AudioFrame, AudioResampler
import numpy as np
import pyaudio


SAMPLE_RATE = 48000
CHANNELS = 1
FRAME_SAMPLES = 960
MIC_INJECTION_OUTPUT_KEYWORDS = (
    "cable input",
    "vb-audio",
    "voicemeeter input",
    "blackhole",
    "loopback",
)


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


def find_output_device_by_name(name: str) -> int | None:
    wanted = name.lower()
    for device in list_output_devices():
        if wanted in device["name"].lower():
            return int(device["index"])
    return None


def autodetect_mic_injection_output() -> int | None:
    for keyword in MIC_INJECTION_OUTPUT_KEYWORDS:
        match = find_output_device_by_name(keyword)
        if match is not None:
            return match
    return None


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


class MicInjectionSink:
    """Writes the viewer mic track into the selected mic injection output.

    On Windows with VB-CABLE, write to "CABLE Input"; target apps then
    select "CABLE Output" as their microphone. This keeps injection explicit
    and avoids silently sending the viewer voice to regular speakers.
    """

    def __init__(self, device_index: int | None = None) -> None:
        if device_index is None:
            device_index = autodetect_mic_injection_output()
        if device_index is None:
            raise RuntimeError(
                "No mic injection output device was selected or auto-detected. "
                "Configure a mic injection device and pass --mic-injection-device."
            )

        self.device_index = device_index
        self.pa = pyaudio.PyAudio()
        self.stream = self.pa.open(
            format=pyaudio.paInt16,
            channels=CHANNELS,
            rate=SAMPLE_RATE,
            output=True,
            output_device_index=device_index,
            frames_per_buffer=FRAME_SAMPLES,
        )
        self.resampler = AudioResampler(format="s16", layout="mono", rate=SAMPLE_RATE)
        self.task: asyncio.Task | None = None

    async def consume(self, track: MediaStreamTrack) -> None:
        while True:
            frame = await track.recv()
            resampled: Iterable[AudioFrame] | AudioFrame | None = self.resampler.resample(frame)
            if resampled is None:
                continue
            if isinstance(resampled, AudioFrame):
                frames = [resampled]
            else:
                frames = list(resampled)
            for item in frames:
                pcm = item.to_ndarray().astype(np.int16).tobytes()
                self.stream.write(pcm)

    def close(self) -> None:
        if self.task:
            self.task.cancel()
        self.stream.stop_stream()
        self.stream.close()
        self.pa.terminate()


MicPlaybackSink = MicInjectionSink
