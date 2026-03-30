from __future__ import annotations

import importlib
import shutil
import subprocess
import sys


def sounddevice_load_error_message() -> str:
    if sys.platform == "darwin":
        return (
            "sounddevice could not load PortAudio. On Intel macOS install it with "
            "`brew install portaudio`, then reinstall dependencies from "
            "`requirements/macos-intel.txt` if needed."
        )
    if sys.platform == "win32":
        return (
            "sounddevice could not load PortAudio. Recreate the virtual environment "
            "with `requirements/windows.txt`, reinstall `sounddevice`, and confirm "
            "you are using a 64-bit Python on Windows."
        )
    if sys.platform.startswith("linux"):
        return (
            "sounddevice could not load PortAudio. On Ubuntu install the system audio "
            "packages first, for example `sudo apt install portaudio19-dev espeak-ng`, "
            "then reinstall dependencies from `requirements/ubuntu.txt` if needed."
        )
    return "sounddevice could not load PortAudio. Check the platform-specific setup in README.md."


def speak_text_blocking(text: str) -> bool:
    if sys.platform == "darwin":
        completed = subprocess.run(["say", text], check=False)
        return completed.returncode == 0

    if sys.platform == "win32":
        try:
            pyttsx3 = importlib.import_module("pyttsx3")
            engine = pyttsx3.init()
            try:
                engine.say(text)
                engine.runAndWait()
            finally:
                engine.stop()
            return True
        except Exception:
            return False

    if sys.platform.startswith("linux"):
        for executable in ("spd-say", "espeak-ng", "espeak"):
            if not shutil.which(executable):
                continue
            completed = subprocess.run([executable, text], check=False)
            return completed.returncode == 0

    return False


def speech_backend_name() -> str | None:
    if sys.platform == "darwin":
        return "macOS say"
    if sys.platform == "win32":
        return "Windows pyttsx3 TTS"
    if sys.platform.startswith("linux"):
        return "Linux spd-say/espeak-ng"
    return None
