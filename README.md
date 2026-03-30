# slapandmoan

`slapandmoan` is a Python CLI prototype for simple impact-sound detection from a laptop microphone.
It can:

- record labeled audio samples
- profile WAV files and extract basic features
- run a live detector that reacts to low-frequency impact-like sounds

The current detector is rule-based. It is useful for quick experiments, threshold tuning, and collecting baseline data before moving to a learned model.

## Supported Platforms

- Intel macOS
- Windows

Platform-specific install files and runtime profiles are separated:

- install files:
  - `requirements/macos-intel.txt`
  - `requirements/windows.txt`
- runtime profiles:
  - `configs/intel_macbook.toml`
  - `configs/windows.toml`

## Quick Start

### Intel macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements/macos-intel.txt
```

If `sounddevice` fails with a PortAudio error, install PortAudio first:

```bash
brew install portaudio
```

You also need to grant microphone permission to the terminal or Python app you use.

### Windows

PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements/windows.txt
```

If audio input does not work, confirm that:

- your microphone is not locked by another app
- you are using a 64-bit Python build
- the input device is visible via `--list-devices`

## Workflow

### 1. List audio devices

Intel macOS:

```bash
python record_dataset.py dummy --config configs/intel_macbook.toml --list-devices
```

Windows:

```powershell
python record_dataset.py dummy --config configs/windows.toml --list-devices
```

### 2. Record a dataset

```bash
python record_dataset.py laptop_hit --config configs/intel_macbook.toml --count 30 --duration 1.2
python record_dataset.py clap --config configs/intel_macbook.toml --count 30 --duration 1.2
python record_dataset.py keyboard_typing --config configs/intel_macbook.toml --count 30 --duration 1.2
```

On Windows, replace `configs/intel_macbook.toml` with `configs/windows.toml`.

### 3. Profile recorded WAV files

```bash
python profile_audio.py data/raw --config configs/intel_macbook.toml --output-dir analysis
```

Outputs:

- `analysis/summary.csv`
- `analysis/plots/*.png`

### 4. Run live detection

Use a custom WAV file:

```bash
python detect_live.py --config configs/intel_macbook.toml --sound /path/to/effect.wav
```

Use built-in speech fallback instead:

```bash
python detect_live.py --config configs/intel_macbook.toml --speak-text "ah"
```

Windows example:

```powershell
python detect_live.py --config configs/windows.toml --speak-text "ah"
```

Dry run:

```bash
python detect_live.py --config configs/intel_macbook.toml --dry-run
```

Tune thresholds from the CLI:

```bash
python detect_live.py --config configs/intel_macbook.toml --min-peak 0.12 --sta-lta-threshold 3.2 --low-band-ratio-min 0.38
```

## Configuration

The runtime profile is loaded from `--config`, and CLI flags override values from the profile.

Main configuration fields include:

- sample rate and chunk size
- band-pass filter range
- cooldown and STA window
- threshold values such as peak, RMS, STA/LTA, low-band ratio, ZCR, and centroid
- playback gain and suppression while playing

Start from:

- `configs/intel_macbook.toml` on Intel MacBook
- `configs/windows.toml` on Windows

Then tune thresholds for your actual microphone and room noise.

## Repository Layout

- `record_dataset.py`: record labeled WAV samples and metadata
- `profile_audio.py`: generate plots and CSV summaries for WAV inputs
- `detect_live.py`: run the live detector and trigger playback
- `slapandmoan/audio_core.py`: feature extraction and rule-based detection logic
- `slapandmoan/config.py`: detection config model and TOML loading
- `slapandmoan/platform.py`: platform-specific audio and speech helpers
- `tests/`: unit tests for audio logic and platform config handling

## Testing

```bash
python -m unittest discover -s tests
```

## Current Defaults

- sample rate: `16 kHz`
- chunk size: `1024`
- rolling analysis window: `1.0 s`
- band-pass filter: `80 Hz` to `2500 Hz`
- cooldown: `1.5 s`

## Limitations

- This is a rule-based baseline, not a trained classifier.
- Thresholds will need retuning across microphones, desks, rooms, and background noise conditions.
- Playback can leak back into the microphone, so detection is suppressed while playback is active by default.
- `--speak-text` uses `say` on macOS and PowerShell TTS on Windows.
- No GUI or menu bar app packaging is included.
