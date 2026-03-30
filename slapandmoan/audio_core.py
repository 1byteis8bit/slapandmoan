from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass
from typing import Any

import numpy as np
from scipy import signal

from .config import DetectionConfig


EPSILON = 1e-9


def ensure_mono_float32(samples: np.ndarray) -> np.ndarray:
    array = np.asarray(samples, dtype=np.float32)
    if array.ndim == 2:
        array = array[:, 0]
    return np.ascontiguousarray(array)


class RollingAudioBuffer:
    def __init__(self, size: int) -> None:
        self.size = size
        self._buffer = np.zeros(size, dtype=np.float32)

    def extend(self, samples: np.ndarray) -> None:
        chunk = ensure_mono_float32(samples)
        if len(chunk) >= self.size:
            self._buffer[:] = chunk[-self.size :]
            return
        self._buffer = np.roll(self._buffer, -len(chunk))
        self._buffer[-len(chunk) :] = chunk

    def view(self) -> np.ndarray:
        return self._buffer.copy()


def design_bandpass(config: DetectionConfig) -> np.ndarray:
    nyquist = config.sample_rate / 2.0
    high = min(config.filter_high_hz, nyquist * 0.95)
    low = min(config.filter_low_hz, high - 1.0)
    return signal.butter(
        config.filter_order,
        [low, high],
        btype="bandpass",
        fs=config.sample_rate,
        output="sos",
    )


def apply_bandpass(samples: np.ndarray, sos: np.ndarray) -> np.ndarray:
    chunk = ensure_mono_float32(samples)
    try:
        filtered = signal.sosfiltfilt(sos, chunk)
    except ValueError:
        filtered = signal.sosfilt(sos, chunk)
    return np.asarray(filtered, dtype=np.float32)


def rms(samples: np.ndarray) -> float:
    chunk = ensure_mono_float32(samples)
    return float(np.sqrt(np.mean(np.square(chunk), dtype=np.float64)))


def peak_amplitude(samples: np.ndarray) -> float:
    return float(np.max(np.abs(ensure_mono_float32(samples))))


def zero_crossing_rate(samples: np.ndarray) -> float:
    chunk = ensure_mono_float32(samples)
    if len(chunk) < 2:
        return 0.0
    signs = np.signbit(chunk)
    crossings = np.count_nonzero(signs[1:] != signs[:-1])
    return float(crossings / (len(chunk) - 1))


def _power_spectrum(samples: np.ndarray, sample_rate: int) -> tuple[np.ndarray, np.ndarray]:
    chunk = ensure_mono_float32(samples)
    windowed = chunk * np.hanning(len(chunk))
    spectrum = np.fft.rfft(windowed)
    freqs = np.fft.rfftfreq(len(chunk), d=1.0 / sample_rate)
    power = np.abs(spectrum) ** 2
    return freqs, power


def spectral_centroid(samples: np.ndarray, sample_rate: int) -> float:
    freqs, power = _power_spectrum(samples, sample_rate)
    total_power = float(np.sum(power))
    if total_power <= EPSILON:
        return 0.0
    return float(np.sum(freqs * power) / total_power)


def band_energy_ratio(
    samples: np.ndarray,
    sample_rate: int,
    low_hz: float,
    high_hz: float,
) -> float:
    freqs, power = _power_spectrum(samples, sample_rate)
    total_power = float(np.sum(power))
    if total_power <= EPSILON:
        return 0.0
    mask = (freqs >= low_hz) & (freqs < high_hz)
    band_power = float(np.sum(power[mask]))
    return band_power / total_power


def attack_time_ms(samples: np.ndarray, sample_rate: int) -> float:
    chunk = np.abs(ensure_mono_float32(samples))
    peak = float(np.max(chunk))
    if peak <= EPSILON:
        return 0.0
    ten = 0.1 * peak
    ninety = 0.9 * peak
    above_ten = np.flatnonzero(chunk >= ten)
    above_ninety = np.flatnonzero(chunk >= ninety)
    if len(above_ten) == 0 or len(above_ninety) == 0:
        return 0.0
    start = int(above_ten[0])
    finish = int(above_ninety[0])
    if finish < start:
        return 0.0
    return ((finish - start) / sample_rate) * 1_000.0


def compute_sta_lta(samples: np.ndarray, sta_samples: int) -> tuple[float, float, float]:
    chunk = ensure_mono_float32(samples)
    squared = np.square(chunk, dtype=np.float64)
    sta_samples = min(sta_samples, len(chunk))
    sta = float(np.mean(squared[-sta_samples:]))

    if len(chunk) > sta_samples:
        lta = float(np.mean(squared[:-sta_samples]))
    else:
        lta = sta

    ratio = sta / max(lta, EPSILON)
    return sta, lta, ratio


def extract_profile_features(samples: np.ndarray, config: DetectionConfig, sos: np.ndarray | None = None) -> dict[str, float]:
    raw = ensure_mono_float32(samples)
    selected_sos = sos if sos is not None else design_bandpass(config)
    filtered = apply_bandpass(raw, selected_sos)
    sta, lta, ratio = compute_sta_lta(filtered, config.sta_samples)

    return {
        "peak": peak_amplitude(raw),
        "rms": rms(filtered),
        "sta": sta,
        "lta": lta,
        "sta_lta_ratio": ratio,
        "zcr": zero_crossing_rate(filtered),
        "centroid_hz": spectral_centroid(filtered, config.sample_rate),
        "low_band_ratio": band_energy_ratio(
            filtered,
            config.sample_rate,
            config.profile_low_band_hz[0],
            config.profile_low_band_hz[1],
        ),
        "high_band_ratio": band_energy_ratio(
            filtered,
            config.sample_rate,
            config.profile_high_band_hz[0],
            config.profile_high_band_hz[1],
        ),
        "attack_ms": attack_time_ms(filtered, config.sample_rate),
    }


@dataclass(slots=True)
class DetectionResult:
    triggered: bool
    features: dict[str, float]
    reasons: list[str]


class ImpactDetector:
    def __init__(self, config: DetectionConfig) -> None:
        self.config = config
        self.sos = design_bandpass(config)
        self.cooldown_until = 0.0
        self.recent_results: deque[DetectionResult] = deque(maxlen=32)

    def process(self, samples: np.ndarray, now: float, suppress: bool = False) -> DetectionResult:
        features = extract_profile_features(samples, self.config, self.sos)
        reasons: list[str] = []

        if suppress:
            reasons.append("playback_suppressed")
        if now < self.cooldown_until:
            reasons.append("cooldown")

        if features["peak"] < self.config.min_peak:
            reasons.append("low_peak")
        if features["rms"] < self.config.min_rms:
            reasons.append("low_rms")
        if features["sta_lta_ratio"] < self.config.sta_lta_threshold:
            reasons.append("low_sta_lta")
        if features["low_band_ratio"] < self.config.low_band_ratio_min:
            reasons.append("not_low_band_dominant")
        if features["zcr"] > self.config.zcr_max:
            reasons.append("zcr_too_high")
        if features["centroid_hz"] > self.config.centroid_max_hz:
            reasons.append("centroid_too_high")

        triggered = not reasons
        if triggered:
            self.cooldown_until = now + self.config.cooldown_sec

        result = DetectionResult(triggered=triggered, features=features, reasons=reasons)
        self.recent_results.append(result)
        return result


def summarize_result(result: DetectionResult) -> str:
    f = result.features
    status = "TRIGGER" if result.triggered else "skip"
    return (
        f"{status} "
        f"peak={f['peak']:.3f} rms={f['rms']:.3f} "
        f"sta/lta={f['sta_lta_ratio']:.2f} low={f['low_band_ratio']:.2f} "
        f"zcr={f['zcr']:.3f} centroid={f['centroid_hz']:.0f}Hz "
        f"attack={f['attack_ms']:.1f}ms"
    )


def dbfs(samples: np.ndarray) -> float:
    value = rms(samples)
    if value <= EPSILON:
        return -math.inf
    return 20.0 * math.log10(value)
