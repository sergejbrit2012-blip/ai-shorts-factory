
import subprocess
import sys
import re
from pathlib import Path

VOICE = "ru-RU-SvetlanaNeural"
RATE = "-8%"
PITCH = "-2Hz"
VOLUME = "+0%"


def make_voice(text, output_path):
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    subtitle_path = output_path.with_suffix(".srt")

    text = re.sub(r"\s+", " ", str(text)).strip()

    if not text:
        raise RuntimeError("Текст для озвучки пустой.")

    command = [
        sys.executable,
        "-m",
        "edge_tts",
        "--voice", VOICE,
        "--rate", RATE,
        "--pitch", PITCH,
        "--volume", VOLUME,
        "--text", text,
        "--write-media", str(output_path),
        "--write-subtitles", str(subtitle_path)
    ]

    print("Создаём нейросетевую озвучку...")
    print("Голос:", VOICE)

    subprocess.run(command, check=True, timeout=180)

    if not output_path.exists() or output_path.stat().st_size < 1000:
        raise RuntimeError("Edge TTS не создал аудиофайл.")

    if not subtitle_path.exists():
        raise RuntimeError("Edge TTS не создал субтитры.")

    print("Озвучка готова:", output_path)
    print("Субтитры готовы:", subtitle_path)

    return output_path, subtitle_path


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--text", required=True)
    parser.add_argument("--output", default="output/voice.mp3")
    args = parser.parse_args()

    make_voice(args.text, args.output)
