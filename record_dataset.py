#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import time
from pathlib import Path

import soundfile as sf

from slapandmoan.config import DetectionConfig, load_detection_config, merge_detection_config
from slapandmoan.platform import sounddevice_load_error_message


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Record labeled impact/clap/typing samples.")
    parser.add_argument("label", help="Sample label, e.g. laptop_hit, clap, keyboard_typing")
    parser.add_argument("--config", default=None, help="Path to a TOML detection profile")
    parser.add_argument("--output-dir", default="data/raw", help="Directory for WAV files and metadata")
    parser.add_argument("--count", type=int, default=10, help="Number of samples to record")
    parser.add_argument("--duration", type=float, default=1.2, help="Recording duration in seconds")
    parser.add_argument("--gap", type=float, default=0.8, help="Silence gap between samples")
    parser.add_argument("--sample-rate", type=int, default=None)
    parser.add_argument("--device", default=None, help="sounddevice input device name or index")
    parser.add_argument("--list-devices", action="store_true", help="Print available audio devices and exit")
    return parser.parse_args()


def require_sounddevice():
    try:
        import sounddevice as sd  # type: ignore
    except OSError as exc:
        raise SystemExit(sounddevice_load_error_message()) from exc
    return sd


def build_config(args: argparse.Namespace) -> DetectionConfig:
    base = load_detection_config(args.config)
    return merge_detection_config(base, sample_rate=args.sample_rate)


def main() -> int:
    args = parse_args()
    sd = require_sounddevice()
    config = build_config(args)

    if args.list_devices:
        print(sd.query_devices())
        return 0

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    session_id = dt.datetime.now(dt.UTC).strftime("%Y%m%dT%H%M%SZ")
    metadata_path = output_dir / f"{args.label}_{session_id}.jsonl"

    print(f"Recording {args.count} samples into {output_dir}")
    if args.config:
        print(f"loaded config: {args.config}")
    print("Press Ctrl+C to stop.")

    for index in range(args.count):
        filename = output_dir / f"{args.label}_{session_id}_{index:03d}.wav"
        print(f"[{index + 1}/{args.count}] get ready...")
        time.sleep(args.gap)
        print("recording")
        recording = sd.rec(
            int(args.duration * config.sample_rate),
            samplerate=config.sample_rate,
            channels=config.channels,
            dtype=config.dtype,
            device=args.device,
        )
        sd.wait()
        sf.write(filename, recording, config.sample_rate)

        metadata = {
            "file": str(filename),
            "label": args.label,
            "sample_rate": config.sample_rate,
            "duration": args.duration,
            "captured_at": dt.datetime.now(dt.UTC).isoformat(),
            "device": args.device,
        }
        with metadata_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(metadata, ensure_ascii=True) + "\n")
        print(f"saved {filename.name}")

    print(f"metadata saved to {metadata_path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nStopped.", file=sys.stderr)
        raise SystemExit(130)
