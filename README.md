# slapandmoan

`slapandmoan` is a Python CLI prototype for impact-sound detection from a laptop microphone.

It can:

- record labeled audio samples
- profile WAV files and extract simple features
- run a live detector that reacts to low-frequency impact-like sounds

The detector is rule-based. The goal is fast experimentation, not production-grade classification.

## Supported Platforms

- Intel macOS
- Windows
- Ubuntu

## Zero-Config Usage

You do not need a config file to get started.

Default settings are embedded in the code, and the CLI uses them automatically.
Most users should:

1. install dependencies for their platform
2. list audio devices once
3. run live detection

The `configs/` directory is only for people who want to tweak thresholds or keep their own profiles.

## Install

### Intel macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements/macos-intel.txt
```

If `sounddevice` fails with a PortAudio error:

```bash
brew install portaudio
```

You also need to grant microphone permission to the terminal or Python app you use.

### Windows

No PowerShell activation is required:

```bat
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements/windows.txt
```

If you do not activate the virtual environment, run commands with `.\.venv\Scripts\python.exe`.

### Ubuntu

```bash
sudo apt update
sudo apt install -y python3-venv portaudio19-dev espeak-ng
python3 -m venv .venv
./.venv/bin/python -m pip install -r requirements/ubuntu.txt
```

If you do not activate the virtual environment, run commands with `./.venv/bin/python`.

## Fastest Start

### Intel macOS

```bash
python record_dataset.py dummy --list-devices
python detect_live.py --speak-text "ah"
```

### Windows

```bat
.\.venv\Scripts\python.exe record_dataset.py dummy --list-devices
.\.venv\Scripts\python.exe detect_live.py --speak-text "ah"
```

### Ubuntu

```bash
./.venv/bin/python record_dataset.py dummy --list-devices
./.venv/bin/python detect_live.py --speak-text "ah"
```

## Common Workflow

### 1. List audio devices

```bash
python record_dataset.py dummy --list-devices
```

### 2. Record a dataset

```bash
python record_dataset.py laptop_hit --count 30 --duration 1.2
python record_dataset.py clap --count 30 --duration 1.2
python record_dataset.py keyboard_typing --count 30 --duration 1.2
```

### 3. Profile recorded WAV files

```bash
python profile_audio.py data/raw --output-dir analysis
```

Outputs:

- `analysis/summary.csv`
- `analysis/plots/*.png`

### 4. Run live detection

Use a custom WAV file:

```bash
python detect_live.py --sound /path/to/effect.wav
```

Use built-in speech fallback:

```bash
python detect_live.py --speak-text "ah"
```

Dry run:

```bash
python detect_live.py --dry-run
```

Tune thresholds from the CLI:

```bash
python detect_live.py --min-peak 0.12 --sta-lta-threshold 3.2 --low-band-ratio-min 0.38
```

## Optional Custom Configs

If you want to keep your own tuned profile, pass `--config`.

Example files are provided here:

- `configs/intel_macbook.toml`
- `configs/windows.toml`
- `configs/ubuntu.toml`

Example:

```bash
python detect_live.py --config configs/ubuntu.toml --speak-text "ah"
```

Config files are optional overrides. They are not required for normal use.

## Embedded Defaults

The built-in defaults currently use:

- sample rate: `16 kHz`
- chunk size: `1024`
- rolling analysis window: `1.0 s`
- band-pass filter: `80 Hz` to `2500 Hz`
- cooldown: `1.5 s`

CLI flags override the embedded defaults.
If `--config` is provided, the file overrides the embedded defaults, and CLI flags still win last.

## Repository Layout

- `record_dataset.py`: record labeled WAV samples and metadata
- `profile_audio.py`: generate plots and CSV summaries for WAV inputs
- `detect_live.py`: run the live detector and trigger playback
- `slapandmoan/audio_core.py`: feature extraction and rule-based detection logic
- `slapandmoan/config.py`: embedded defaults and config loading
- `slapandmoan/platform.py`: platform-specific audio and speech helpers
- `configs/`: optional example config files
- `tests/`: unit tests

## Testing

```bash
python -m unittest discover -s tests
```

## Limitations

- This is a rule-based baseline, not a trained classifier.
- Thresholds will need retuning across microphones, desks, rooms, and background noise conditions.
- Playback can leak back into the microphone, so detection is suppressed while playback is active by default.
- `--speak-text` uses `say` on macOS, in-process `pyttsx3` on Windows, and `spd-say`/`espeak-ng` on Linux.
- No GUI or menu bar app packaging is included.
