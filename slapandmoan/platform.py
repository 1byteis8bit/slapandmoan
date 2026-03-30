from __future__ import annotations

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
    return "sounddevice could not load PortAudio. Check the platform-specific setup in README.md."


def build_speech_command(text: str) -> list[str] | None:
    if sys.platform == "darwin":
        return ["say", text]

    if sys.platform == "win32":
        escaped = text.replace("'", "''")
        return [
            "powershell",
            "-NoProfile",
            "-Command",
            (
                "Add-Type -AssemblyName System.Speech; "
                "$speaker = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
                f"$speaker.Speak('{escaped}')"
            ),
        ]

    return None


def speech_backend_name() -> str | None:
    if sys.platform == "darwin":
        return "macOS say"
    if sys.platform == "win32":
        return "Windows PowerShell TTS"
    return None
