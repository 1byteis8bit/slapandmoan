# slapandmoan

Intel MacBook 내장 마이크로 `타격음 / 박수 / 키보드 타이핑`을 분리해 보고, 타격음을 감지하면 사운드를 재생하는 Python CLI 프로토타입이다.

## 설치

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

macOS에서는 실행 전에 터미널 또는 Python 실행 앱에 `Microphone` 권한을 줘야 한다.
`sounddevice`가 `PortAudio library not found`를 내면 먼저 아래를 설치한다.

```bash
brew install portaudio
```

## 1. 데이터 수집

장치 목록 확인:

```bash
python record_dataset.py dummy --list-devices
```

샘플 수집:

```bash
python record_dataset.py laptop_hit --count 30 --duration 1.2
python record_dataset.py clap --count 30 --duration 1.2
python record_dataset.py keyboard_typing --count 30 --duration 1.2
```

## 2. 프로파일링

```bash
python profile_audio.py data/raw --output-dir analysis
```

출력:
- `analysis/summary.csv`
- `analysis/plots/*.png`

## 3. 실시간 감지

효과음 WAV 사용:

```bash
python detect_live.py --sound assets/moan.wav
```

WAV가 없을 때 macOS `say` fallback 사용:

```bash
python detect_live.py --speak-text "ah"
```

드라이런:

```bash
python detect_live.py --dry-run
```

민감도 조정 예시:

```bash
python detect_live.py --min-peak 0.12 --sta-lta-threshold 3.2 --low-band-ratio-min 0.38
```

## 파일 구성

- `record_dataset.py`: 라벨별 샘플 수집
- `profile_audio.py`: 파형, 스펙트로그램, 수치 특징 추출
- `detect_live.py`: 실시간 감지 및 사운드 재생
- `slapandmoan/audio_core.py`: 필터, 특징 추출, 규칙 기반 감지
- `tests/test_audio_core.py`: 합성 신호 기반 단위 테스트

## 현재 기본값

- 샘플레이트: `16 kHz`
- 청크: `1024 frames`
- 롤링 분석 창: `1초`
- 필터: `80~2500 Hz` band-pass
- 쿨다운: `1.5초`

## 제한 사항

- v1은 규칙 기반 감지다. 환경이 바뀌면 threshold 재조정이 필요하다.
- 재생 음원이 마이크로 다시 들어올 수 있으므로, 기본적으로 재생 중 감지를 억제한다.
- 메뉴바 앱 패키징은 아직 포함하지 않는다.
