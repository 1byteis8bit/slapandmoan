#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
from pathlib import Path

import librosa
import librosa.display
import matplotlib.pyplot as plt
import numpy as np

from slapandmoan.audio_core import extract_profile_features
from slapandmoan.config import load_detection_config, merge_detection_config


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Profile WAV files and save plots/features.")
    parser.add_argument("inputs", nargs="+", help="WAV files or directories containing WAV files")
    parser.add_argument("--config", default=None, help="Path to a TOML detection profile")
    parser.add_argument("--output-dir", default="analysis", help="Where plots and CSV summary are written")
    parser.add_argument("--sample-rate", type=int, default=None)
    return parser.parse_args()


def expand_inputs(items: list[str]) -> list[Path]:
    files: list[Path] = []
    for item in items:
        path = Path(item)
        if path.is_dir():
            files.extend(sorted(path.rglob("*.wav")))
        elif path.suffix.lower() == ".wav":
            files.append(path)
    return files


def save_plot(y: np.ndarray, sr: int, output_path: Path) -> None:
    figure, axes = plt.subplots(2, 1, figsize=(12, 7))
    librosa.display.waveshow(y, sr=sr, ax=axes[0])
    axes[0].set_title("Waveform")
    axes[0].set_xlabel("Time (s)")
    axes[0].set_ylabel("Amplitude")

    spectrogram = librosa.amplitude_to_db(np.abs(librosa.stft(y)), ref=np.max)
    librosa.display.specshow(spectrogram, sr=sr, x_axis="time", y_axis="hz", ax=axes[1])
    axes[1].set_title("Spectrogram")
    figure.tight_layout()
    figure.savefig(output_path, dpi=150)
    plt.close(figure)


def main() -> int:
    args = parse_args()
    files = expand_inputs(args.inputs)
    if not files:
        raise SystemExit("No WAV files found.")

    output_dir = Path(args.output_dir)
    plots_dir = output_dir / "plots"
    plots_dir.mkdir(parents=True, exist_ok=True)
    config = merge_detection_config(load_detection_config(args.config), sample_rate=args.sample_rate)
    if args.config:
        print(f"loaded config: {args.config}")

    csv_path = output_dir / "summary.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = None
        for file_path in files:
            y, sr = librosa.load(file_path, sr=config.sample_rate, mono=True)
            features = extract_profile_features(y, config)
            row = {"file": str(file_path), **features}

            if writer is None:
                writer = csv.DictWriter(handle, fieldnames=list(row.keys()))
                writer.writeheader()

            writer.writerow(row)
            save_plot(y, sr, plots_dir / f"{file_path.stem}.png")
            print(f"profiled {file_path}")

    print(f"summary written to {csv_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
