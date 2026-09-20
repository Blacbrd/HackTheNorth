# /// script
# requires-python = ">=3.10,<3.11"
# dependencies = ["bbos", "numpy<2"]
# [tool.uv.sources]
# bbos = { path = "/home/bracketbot/bbos", editable = true }
# ///
"""Play a PCM WAV file through the BracketBot speaker."""

from __future__ import annotations

import argparse
import wave
from pathlib import Path

import numpy as np
from bbos import Config, Type, Writer


def load_mono(path: Path, output_rate: int) -> np.ndarray:
    with wave.open(str(path), "rb") as source:
        if source.getsampwidth() != 2:
            raise ValueError("audio must be 16-bit PCM WAV")
        channels = source.getnchannels()
        input_rate = source.getframerate()
        samples = np.frombuffer(
            source.readframes(source.getnframes()), dtype="<i2"
        ).astype(np.float64)
    samples = samples.reshape(-1, channels).mean(axis=1)
    if input_rate != output_rate and len(samples) > 1:
        output_length = round(len(samples) * output_rate / input_rate)
        samples = np.interp(
            np.linspace(0.0, len(samples) - 1, output_length),
            np.arange(len(samples)),
            samples,
        )
    return samples


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("audio", type=Path)
    parser.add_argument("--volume", type=float, default=0.75)
    args = parser.parse_args()
    if not 0.05 <= args.volume <= 1.0:
        raise SystemExit("--volume must be between 0.05 and 1.0")

    cfg = Config("speaker")
    samples = load_mono(args.audio, int(cfg.sample_rate))
    peak = float(np.max(np.abs(samples))) if len(samples) else 0.0
    if peak <= 0.0:
        raise SystemExit("audio file is silent")
    samples = np.clip(samples * (args.volume * 32767.0 / peak), -32768, 32767)
    interleaved = np.repeat(
        samples.astype(np.int16)[:, None], int(cfg.channels), axis=1
    )
    padding = (-len(interleaved)) % int(cfg.chunk_size)
    if padding:
        interleaved = np.pad(interleaved, ((0, padding), (0, 0)))
    chunks = interleaved.reshape(-1, int(cfg.chunk_size), int(cfg.channels))

    with Writer("speaker.audio", Type("speaker_audio")) as writer:
        for chunk in chunks:
            with writer.buf() as command:
                command["audio"] = chunk
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
