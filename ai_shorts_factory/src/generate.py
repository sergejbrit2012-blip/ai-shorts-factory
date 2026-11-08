
import os
import json
import re
import random
import urllib.request
import subprocess
import shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output"
OUT.mkdir(exist_ok=True)

MAX_DURATION = 44.5

HERO_RULES = {
    "банан": ("banana", "Банан", "yellow"),
    "бананы": ("banana", "Банан", "yellow"),
    "арбуз": ("watermelon", "Арбуз", "green"),
    "клубник": ("strawberry", "Клубника", "red"),
    "морков": ("carrot", "Морковка", "orange"),
    "огур": ("cucumber", "Огурец", "green"),
    "картош": ("potato", "Картошка", "brown"),
    "яблок": ("apple", "Яблоко", "red"),
    "апельсин": ("orange", "Апельсин", "orange"),
    "лимон": ("lemon", "Лимон", "yellow"),
    "виноград": ("grapes", "Виноград", "purple"),
    "помидор": ("tomato", "Помидор", "red"),
    "перец": ("pepper", "Перец", "green"),
    "груш": ("pear", "Груша", "green"),
}


def get_video_slot():
    slot = os.getenv("VIDEO_SLOT", "").strip()

    if not slot:
        event_file = os.getenv("GITHUB_EVENT_PATH", "")
        try:
            event = (
                json.loads(Path(event_file).read_text(encoding="utf-8"))
                if event_file else {}
            )
            schedule = event.get("schedule", "")
            slot = {
                "30 7 * * *": "1",
                "30 10 * * *": "2",
                "30 13 * * *": "3",
                "30 16 * * *": "4",
                "30 19 * * *": "5",
            }.get(schedule, "1")
        except Exception:
            slot = "1"

    try:
        return max(1, min(5, int(slot)))
    except (ValueError, TypeError):
        return 1


def choose_hero(title, voiceover=""):
    text = (str(title) + " " + str(voiceover)).lower()

    for keyword, hero in HERO_RULES.items():
        if keyword in text:
            return {
                "id": hero[0],
                "name": hero[1],
                "color": hero[2]
            }

    return {
        "id": "banana",
        "name": "Банан",
        "color": "yellow"
    }


def clean_text(value, limit=500):
    value = str(value or "")
    value = re.sub(r"https?://\S+", "", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()[:limit]


def make_fallback_script():
    topics = [
        "Как правильно хранить бананы?",
        "Как выбрать сладкий арбуз?",
        "Чем полезна клубника?",
        "Почему картошку нельзя хранить на свету?",
        "Как дольше сохранить свежесть огурцов?",
        "Как правильно хранить яблоки?",
        "Почему бананы темнеют?",
        "Как выбрать спелый помидор?",
        "Как правильно хранить морковь?",
        "Чем полезен лимон?"
    ]

    day = datetime.now(timezone.utc).timetuple().tm_yday
    slot = get_video_slot()
    topic = topics[((day - 1) * 5 + slot - 1) % len(topics)]

    hero = choose_hero(topic)

    voiceover = (
        f"Привет! Я {hero['name'].lower()}! "
        f"Сегодня расскажу тебе одну полезную вещь. {topic} "
        "Самое главное — соблюдать правильные условия хранения "
        "и регулярно проверять свежесть продукта. "
        "Не клади продукты куда попало. "
        "Запомни этот совет и поделись им с друзьями!"
    )

    return {
        "title": topic.rstrip("?.!"),
        "description": topic + " Полезные советы простыми словами. #shorts",
        "voiceover": voiceover,
        "category": "HOME",
        "hero": hero,
        "scenes": [
            {
                "kicker": "ЗНАКОМСТВО",
                "title": f"Привет! Я {hero['name']}!",
                "body": topic
            },
            {
                "kicker": "МОЙ СОВЕТ",
                "title": "Запомни это!",
                "body": "Правильное хранение помогает сохранить свежесть."
            },
            {
                "kicker": "ПОЛЕЗНО ЗНАТЬ",
                "title": "Теперь ты знаешь!",
                "body": "Проверяй свежесть продуктов."
            }
        ]
    }


def make_script():
    api_key = os.getenv("OPENROUTER_API_KEY", "").strip()

    if not api_key:
        print("Нет API-ключа. Используем запасной сценарий.")
        return make_fallback_script()

    prompt = """
Придумай оригинальный сценарий для русского YouTube Shorts.

Выбери интересную тему о продуктах, еде или хранении продуктов.
Главный герой должен быть тем продуктом, о котором рассказывается.

Примеры:
- Как хранить бананы — главный герой Банан.
- Как выбрать сладкий арбуз — главный герой Арбуз.
- Чем полезна клубника — главный герой Клубника.

Герой должен говорить от первого лица.
Сценарий должен быть интересным, полезным и понятным.

Требования:
- Русский язык.
- Озвучка примерно 65-90 слов.
- Начало с интересной фразы.
- Ровно три сцены.
- У каждой сцены есть kicker, title и body.
- Не придумывай медицинские обещания.
- Не выдумывай опасные советы по хранению продуктов.
- Верни только JSON.

Формат:
{
"title":"Название",
"description":"Описание и #shorts",
"voiceover":"Полный текст озвучки",
"scenes":[
{"kicker":"НАЧАЛО","title":"Заголовок","body":"Описание"},
{"kicker":"СОВЕТ","title":"Заголовок","body":"Описание"},
{"kicker":"ФИНАЛ","title":"Заголовок","body":"Описание"}
]
}
"""

    payload = {
        "model": "openrouter/free",
        "messages": [
            {
                "role": "system",
                "content": "Ты профессиональный автор сценариев коротких мультфильмов. Возвращай только JSON."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.85,
        "max_tokens": 1600
    }

    request = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": "Bearer " + api_key,
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com",
            "X-Title": "AI Shorts Factory"
        },
        method="POST"
    )

    try:
        print("Создаём сценарий...")

        with urllib.request.urlopen(request, timeout=90) as response:
            result = json.loads(response.read().decode("utf-8"))

        choices = result.get("choices") or []
        if not choices:
            raise ValueError("Нейросеть не вернула ответ.")

        message = choices[0].get("message") or {}
        content = message.get("content")

        if isinstance(content, list):
            content = "".join(
                item.get("text", "")
                for item in content
                if isinstance(item, dict)
            )

        if not isinstance(content, str) or not content.strip():
            raise ValueError("Пустой ответ нейросети.")

        content = re.sub(
            r"^```(?:json)?\s*|\s*```$",
            "",
            content.strip(),
            flags=re.IGNORECASE
        )

        start = content.find("{")
        end = content.rfind("}")

        if start < 0 or end < 0:
            raise ValueError("Не найден JSON.")

        data = json.loads(content[start:end + 1])

        title = clean_text(data.get("title"), 62)
        description = clean_text(data.get("description"), 1000)
        voiceover = clean_text(data.get("voiceover"), 1600)
        scenes = data.get("scenes")

        if not title or not voiceover:
            raise ValueError("Пустое название или озвучка.")

        if not isinstance(scenes, list) or len(scenes) != 3:
            raise ValueError("Нужно ровно три сцены.")

        clean_scenes = []

        for scene in scenes:
            if not isinstance(scene, dict):
                raise ValueError("Некорректная сцена.")

            clean_scenes.append({
                "kicker": clean_text(scene.get("kicker"), 35),
                "title": clean_text(scene.get("title"), 100),
                "body": clean_text(scene.get("body"), 350)
            })

        if not all(item["title"] and item["body"] for item in clean_scenes):
            raise ValueError("В сцене отсутствует текст.")

        if "#shorts" not in description.lower():
            description += " #shorts"

        hero = choose_hero(title, voiceover)

        print("Сценарий:", title)
        print("Главный герой:", hero["name"])

        return {
            "title": title,
            "description": description,
            "voiceover": voiceover,
            "category": "HOME",
            "hero": hero,
            "scenes": clean_scenes
        }

    except Exception as error:
        print("Ошибка сценария:", error)
        print("Используем запасной сценарий.")
        return make_fallback_script()


def make_voice(text, path, category="HOME"):
    wav = path.with_suffix(".wav")

    text = clean_text(text, 2000)
    text = re.sub(r"[*_`#]", "", text)

    if not text or not re.search(r"[а-яА-ЯёЁ]", text):
        raise RuntimeError("Нет русского текста для озвучки.")

    # Espeak — бесплатный синтезатор, но его голос сам по себе
    # звучит синтетически. Здесь добавлены паузы и обработка.
    speed = "125"
    pitch = "48"

    subprocess.run(
        [
            "espeak-ng",
            "-v", "ru",
            "-s", speed,
            "-p", pitch,
            "-a", "175",
            "-g", "10",
            "-w", str(wav),
            "--stdin"
        ],
        input=text,
        text=True,
        check=True
    )

    if not wav.exists() or wav.stat().st_size < 1000:
        raise RuntimeError("Не удалось создать WAV.")

    subprocess.run(
        [
            "ffmpeg", "-y",
            "-loglevel", "error",
            "-i", str(wav),
            "-af",
            "highpass=f=80,lowpass=f=11000,"
            "acompressor=threshold=0.12:ratio=2.5:attack=15:release=180,"
            "equalizer=f=2500:t=q:w=1:g=2,"
            "loudnorm=I=-16:TP=-1.5:LRA=10",
            "-ar", "44100",
            "-ac", "2",
            "-codec:a", "libmp3lame",
            "-b:a", "160k",
            str(path)
        ],
        check=True
    )

    wav.unlink(missing_ok=True)

    print("Озвучка создана:", path)


def make_subtitles(text, audio_path, subtitle_path):
    """
    Создаёт простой SRT с распределением фраз по длительности аудио.
    Это приблизительная синхронизация, не распознавание речи.
    """
    probe = subprocess.check_output(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(audio_path)
        ],
        text=True
    )

    duration = float(probe.strip())
    sentences = re.split(r"(?<=[.!?])\s+", clean_text(text, 2000))
    sentences = [s.strip() for s in sentences if s.strip()]

    if not sentences:
        return

    weights = [max(1, len(re.findall(r"\w+", s))) for s in sentences]
    total = sum(weights)
    current = 0.0

    def timestamp(seconds):
        ms = int(seconds * 1000)
        hours = ms // 3600000
        minutes = (ms % 3600000) // 60000
        seconds_part = (ms % 60000) // 1000
        millis = ms % 1000
        return f"{hours:02}:{minutes:02}:{seconds_part:02},{millis:03}"

    lines = []

    for index, (sentence, weight) in enumerate(zip(sentences, weights), 1):
        segment = duration * weight / total
        end = min(duration, current + segment)

        lines.extend([
            str(index),
            f"{timestamp(current)} --> {timestamp(end)}",
            sentence,
            ""
        ])

        current = end

    subtitle_path.write_text("\n".join(lines), encoding="utf-8")
    print("Субтитры созданы:", subtitle_path)


def render(data, audio_path, video_path):
    blender = shutil.which("blender")

    if not blender:
        raise RuntimeError("Blender не найден.")

    scene_script = Path(__file__).resolve().parent / "blender_scene.py"

    if not scene_script.exists():
        raise RuntimeError(f"Не найден файл: {scene_script}")

    scene_json = OUT / "blender_scene_data.json"
    silent_video = OUT / "cartoon_no_audio.mp4"

    scene_json.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    probe = subprocess.check_output(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(audio_path)
        ],
        text=True
    )

    duration = min(float(probe.strip()), MAX_DURATION)
    duration = max(8.0, duration)

    command = [
        blender,
        "-b",
        "-t", str(max(1, min(4, os.cpu_count() or 2))),
        "--python", str(scene_script),
        "--",
        "--data", str(scene_json),
        "--output", str(silent_video),
        "--duration", str(duration)
    ]

    print("Запускаем Blender...")

    subprocess.run(command, check=True)

    if not silent_video.exists() or silent_video.stat().st_size < 100_000:
        raise RuntimeError("Blender не создал видео.")

    subtitle_path = OUT / "subtitles.srt"
    make_subtitles(data["voiceover"], audio_path, subtitle_path)

    print("Собираем финальное видео...")

    # Вшиваем субтитры в изображение. FFmpeg subtitles-фильтр
    # использует libass, если он доступен в сборке FFmpeg.
    subtitle_filter = (
        "subtitles="
        + str(subtitle_path).replace("\\", "/").replace(":", r"\:")
        + ":force_style='FontName=DejaVu Sans,FontSize=18,"
          "PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,"
          "BorderStyle=1,Outline=2,Shadow=1,Alignment=2,MarginV=95'"
    )

    command = [
        "ffmpeg", "-y",
        "-loglevel", "error",
        "-i", str(silent_video),
        "-i", str(audio_path),
        "-vf", subtitle_filter,
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "21",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "160k",
        "-t", str(duration),
        "-movflags", "+faststart",
        str(video_path)
    ]

    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError:
        print("Не удалось вшить субтитры. Создаём видео без них.")

        subprocess.run(
            [
                "ffmpeg", "-y",
                "-loglevel", "error",
                "-i", str(silent_video),
                "-i", str(audio_path),
                "-map", "0:v:0",
                "-map", "1:a:0",
                "-c:v", "libx264",
                "-preset", "veryfast",
                "-crf", "21",
                "-pix_fmt", "yuv420p",
                "-c:a", "aac",
                "-b:a", "160k",
                "-t", str(duration),
                "-movflags", "+faststart",
                str(video_path)
            ],
            check=True
        )

    if not video_path.exists() or video_path.stat().st_size < 100_000:
        raise RuntimeError("Финальное видео не создано.")

    print("Готовое видео:", video_path)


def upload(video_path, data):
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload

    token_file = Path(os.getenv("YOUTUBE_TOKEN_FILE", "token.json"))

    creds = Credentials.from_authorized_user_file(
        str(token_file),
        ["https://www.googleapis.com/auth/youtube.upload"]
    )

    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        token_file.write_text(creds.to_json(), encoding="utf-8")

    yt = build("youtube", "v3", credentials=creds)

    body = {
        "snippet": {
            "title": data["title"][:100],
            "description": data["description"],
            "categoryId": "22",
            "defaultLanguage": "ru"
        },
        "status": {
            "privacyStatus": os.getenv("YOUTUBE_PRIVACY", "private"),
            "selfDeclaredMadeForKids": False
        }
    }

    request = yt.videos().insert(
        part="snippet,status",
        body=body,
        media_body=MediaFileUpload(
            str(video_path),
            mimetype="video/mp4",
            resumable=True
        )
    )

    response = request.execute()
    print("YOUTUBE_VIDEO_ID=" + response["id"])


def main():
    print("================================")
    print("AI SHORTS FACTORY")
    print("================================")

    data = make_script()

    (OUT / "last_script.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    audio = OUT / "voice.mp3"
    video = OUT / "short.mp4"

    print("Создаём озвучку...")
    make_voice(data["voiceover"], audio, data["category"])

    print("Создаём 3D-видео...")
    render(data, audio, video)

    if os.getenv("UPLOAD_TO_YOUTUBE", "false").lower() == "true":
        print("Загружаем видео на YouTube...")
        upload(video, data)
    else:
        print("Загрузка на YouTube отключена.")

    print("Создано:", video)
    print("Генерация завершена.")


if __name__ == "__main__":
    main()
