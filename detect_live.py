#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import queue
import sys
import threading
import time
from pathlib import Path

import numpy as np
import soundfile as sf

from slapandmoan.audio_core import ImpactDetector, RollingAudioBuffer, summarize_result
from slapandmoan.config import DetectionConfig, load_detection_config, merge_detection_config
from slapandmoan.platform import sounddevice_load_error_message, speak_text_blocking, speech_backend_name


class EffectPlayer:
    def __init__(self, sounddevice_module, sound_path: str | None, gain: float, speak_text: str | None = None) -> None:
        self.sd = sounddevice_module
        self.sound_path = Path(sound_path).expanduser() if sound_path else None
        self.gain = gain
        self.speak_text = speak_text
        self._busy = threading.Event()

    @property
    def busy(self) -> bool:
        return self._busy.is_set()

    def play(self) -> None:
        if self._busy.is_set():
            return

        thread = threading.Thread(target=self._play_blocking, daemon=True)
        thread.start()

    def _play_blocking(self) -> None:
        self._busy.set()
        try:
            if self.sound_path and self.sound_path.exists():
                data, sample_rate = sf.read(self.sound_path, dtype="float32", always_2d=False)
                data = np.asarray(data, dtype=np.float32) * self.gain
                self.sd.play(data, sample_rate)
                self.sd.wait()
                return

            if self.speak_text:
                if speak_text_blocking(self.speak_text):
                    return

                backend_name = speech_backend_name()
                if backend_name:
                    print(f"triggered, but {backend_name} is not available", flush=True)
                    return

            print("triggered, but no playback asset configured", flush=True)
        finally:
            self._busy.clear()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Detect laptop impacts from the microphone.")
    parser.add_argument("--config", default=None, help="Optional TOML overrides for the embedded defaults")
    parser.add_argument("--device", default=None, help="sounddevice input device")
    parser.add_argument("--list-devices", action="store_true", help="Print audio devices and exit")
    parser.add_argument("--sound", default=None, help="WAV file to play when an impact is detected")
    parser.add_argument(
        "--speak-text",
        default=None,
        help="Built-in speech fallback when --sound is not provided (macOS say / Windows in-process TTS / Linux spd-say or espeak-ng)",
    )
    parser.add_argument("--log-csv", default="logs/events.csv", help="CSV file for feature/event logs")
    parser.add_argument("--dry-run", action="store_true", help="Log detections without playing output")
    parser.add_argument("--sample-rate", type=int, default=None)
    parser.add_argument("--chunk-size", type=int, default=None)
    parser.add_argument("--cooldown", type=float, default=None)
    parser.add_argument("--min-peak", type=float, default=None)
    parser.add_argument("--min-rms", type=float, default=None)
    parser.add_argument("--sta-lta-threshold", type=float, default=None)
    parser.add_argument("--low-band-ratio-min", type=float, default=None)
    parser.add_argument("--zcr-max", type=float, default=None)
    parser.add_argument("--centroid-max-hz", type=float, default=None)
    parser.add_argument("--playback-gain", type=float, default=None)
    return parser.parse_args()


def require_sounddevice():
    try:
        import sounddevice as sd  # type: ignore
    except OSError as exc:
        raise SystemExit(sounddevice_load_error_message()) from exc
    return sd


def build_config(args: argparse.Namespace) -> DetectionConfig:
    base = load_detection_config(args.config)
    return merge_detection_config(
        base,
        sample_rate=args.sample_rate,
        chunk_size=args.chunk_size,
        cooldown_sec=args.cooldown,
        min_peak=args.min_peak,
        min_rms=args.min_rms,
        sta_lta_threshold=args.sta_lta_threshold,
        low_band_ratio_min=args.low_band_ratio_min,
        zcr_max=args.zcr_max,
        centroid_max_hz=args.centroid_max_hz,
        playback_gain=args.playback_gain,
    )


def main() -> int:
    args = parse_args()
    sd = require_sounddevice()
    if args.list_devices:
        print(sd.query_devices())
        return 0

    config = build_config(args)
    detector = ImpactDetector(config)
    player = EffectPlayer(sd, args.sound, config.playback_gain, speak_text=args.speak_text)
    rolling = RollingAudioBuffer(config.rolling_window_samples)
    audio_queue: queue.Queue[np.ndarray] = queue.Queue()

    log_path = Path(args.log_csv)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_handle = log_path.open("a", newline="", encoding="utf-8")
    fieldnames = [
        "timestamp",
        "triggered",
        "reasons",
        "peak",
        "rms",
        "sta",
        "lta",
        "sta_lta_ratio",
        "zcr",
        "centroid_hz",
        "low_band_ratio",
        "high_band_ratio",
        "attack_ms",
    ]
    writer = csv.DictWriter(log_handle, fieldnames=fieldnames)
    if log_handle.tell() == 0:
        writer.writeheader()

    def audio_callback(indata: np.ndarray, frames: int, time_info: dict[str, float], status) -> None:
        del frames, time_info
        if status:
            print(status, file=sys.stderr)
        audio_queue.put(indata[:, 0].copy())

    print("starting live detector")
    if args.config:
        print(f"loaded config: {args.config}")
    print("press Ctrl+C to stop")

    try:
        with sd.InputStream(
            samplerate=config.sample_rate,
            channels=config.channels,
            dtype=config.dtype,
            blocksize=config.chunk_size,
            device=args.device,
            callback=audio_callback,
        ):
            while True:
                chunk = audio_queue.get()
                rolling.extend(chunk)
                window = rolling.view()
                now = time.monotonic()
                suppress = config.suppress_while_playing and player.busy
                result = detector.process(window, now, suppress=suppress)

                print(summarize_result(result), flush=True)

                row = {
                    "timestamp": time.time(),
                    "triggered": result.triggered,
                    "reasons": ",".join(result.reasons),
                    **result.features,
                }
                writer.writerow(row)
                log_handle.flush()

                if result.triggered and not args.dry_run:
                    player.play()
    except KeyboardInterrupt:
        print("\nstopped")
    finally:
        log_handle.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
