from __future__ import annotations

import tomllib
from dataclasses import dataclass, fields
from pathlib import Path
from typing import Any, Mapping


@dataclass(slots=True)
class DetectionConfig:
    sample_rate: int = 16_000
    channels: int = 1
    dtype: str = "float32"
    chunk_size: int = 1_024
    rolling_window_sec: float = 1.0

    filter_low_hz: float = 80.0
    filter_high_hz: float = 2_500.0
    filter_order: int = 4

    sta_ms: float = 96.0
    cooldown_sec: float = 1.5

    min_peak: float = 0.10
    min_rms: float = 0.015
    sta_lta_threshold: float = 2.8
    low_band_ratio_min: float = 0.34
    zcr_max: float = 0.22
    centroid_max_hz: float = 1_800.0

    profile_low_band_hz: tuple[float, float] = (80.0, 400.0)
    profile_high_band_hz: tuple[float, float] = (1_500.0, 4_000.0)

    playback_gain: float = 1.0
    suppress_while_playing: bool = True

    @property
    def rolling_window_samples(self) -> int:
        return int(self.sample_rate * self.rolling_window_sec)

    @property
    def sta_samples(self) -> int:
        return max(1, int(self.sample_rate * (self.sta_ms / 1_000.0)))


CONFIG_FIELD_NAMES = {field.name for field in fields(DetectionConfig)}
TUPLE_FIELDS = {"profile_low_band_hz", "profile_high_band_hz"}


def _normalize_config_values(values: Mapping[str, Any]) -> dict[str, Any]:
    unknown_keys = sorted(set(values) - CONFIG_FIELD_NAMES)
    if unknown_keys:
        keys = ", ".join(unknown_keys)
        raise ValueError(f"unknown detection config keys: {keys}")

    normalized: dict[str, Any] = {}
    for key, value in values.items():
        if key in TUPLE_FIELDS and isinstance(value, list):
            normalized[key] = tuple(value)
            continue
        normalized[key] = value
    return normalized


def load_detection_config(path: str | Path | None = None) -> DetectionConfig:
    if path is None:
        return DetectionConfig()

    config_path = Path(path).expanduser()
    with config_path.open("rb") as handle:
        loaded = tomllib.load(handle)

    normalized = _normalize_config_values(loaded)
    return DetectionConfig(**normalized)


def merge_detection_config(base: DetectionConfig, **overrides: Any) -> DetectionConfig:
    merged = {field.name: getattr(base, field.name) for field in fields(DetectionConfig)}
    for key, value in overrides.items():
        if value is None:
            continue
        merged[key] = value

    normalized = _normalize_config_values(merged)
    return DetectionConfig(**normalized)
