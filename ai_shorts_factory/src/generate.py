
import os
import json
import re
import urllib.request
import subprocess
import shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output"
OUT.mkdir(exist_ok=True)

MAX_DURATION = 44.5


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


def make_fallback_script():
    topics = [
        ("HOME", "Где лучше хранить картошку?"),
        ("HOME", "Почему хлеб быстро становится твёрдым?"),
        ("HOME", "Как правильно хранить бананы?"),
        ("AI", "Какая нейросеть лучше помогает с текстами?"),
        ("AI", "Какие нейросети умеют создавать видео?"),
        ("AI", "Как нейросети помогают в обычной жизни?"),
        ("SERIES", "Клубника спорит с Бананом"),
        ("SERIES", "Морковка забыла своё имя"),
        ("SERIES", "Огурец открыл секрет Клубники"),
        ("SERIES", "Картошка стала главным на кухне"),
    ]

    day = datetime.now(timezone.utc).timetuple().tm_yday
    slot = get_video_slot()
    index = ((day - 1) * 5 + slot - 1) % len(topics)

    category, topic = topics[index]
    title = topic.rstrip("?.!")

    if category == "HOME":
        voice = (
            f"Стоп! А ты знаешь? {topic} "
            "У каждого продукта есть свои условия хранения. "
            "Важно учитывать температуру, влажность и соседство "
            "с другими продуктами. Не забывай проверять свежесть "
            "еды и рекомендации на упаковке. Сохрани этот совет!"
        )
        scenes = [
            {"kicker": "ПОЛЕЗНЫЙ СОВЕТ", "title": "Ты знал об этом?", "body": topic},
            {"kicker": "КАК ПРАВИЛЬНО", "title": "Запомни это", "body": "У продуктов разные условия хранения."},
            {"kicker": "ВАЖНО", "title": "Не повторяй ошибку", "body": "Следи за свежестью продуктов."}
        ]
        description = topic + " Полезные советы. #shorts #советы"

    elif category == "AI":
        voice = (
            f"Хочешь узнать больше о нейросетях? {topic} "
            "Сначала реши, какая задача тебе нужна. "
            "Одни инструменты помогают писать тексты, "
            "другие создают изображения, а третьи работают с видео. "
            "Проверяй бесплатные возможности и ограничения. "
            "И обязательно проверяй результат!"
        )
        scenes = [
            {"kicker": "МИР НЕЙРОСЕТЕЙ", "title": "Какую выбрать?", "body": topic},
            {"kicker": "ВЫБИРАЕМ ИНСТРУМЕНТ", "title": "У каждой своя задача", "body": "Тексты, изображения и видео."},
            {"kicker": "ПОЛЕЗНЫЙ СОВЕТ", "title": "Проверяй результат", "body": "Сравни возможности разных сервисов."}
        ]
        description = topic + " Нейросети простыми словами. #shorts #нейросети"

    else:
        stories = [
            [
                "Клубника: Я самая красивая ягода на кухне!",
                "Банан: Зато меня знают во всём мире!",
                "Клубника: Да тебя даже перед едой раздевают!",
                "Банан: А тебя кладут в десерты только для украшения!",
                "Клубника: Повтори ещё раз!",
                "Банан: Давай устроим соревнование!",
                "Клубника: Кто победит, тот будет главным!",
                "Банан: У меня уже есть хитрый план!"
            ],
            [
                "Морковка: Подождите, а кто я вообще такая?",
                "Огурец: Ты Морковка! Мы же знакомы!",
                "Морковка: А почему я ничего не помню?",
                "Картошка: Кажется, она опять всё перепутала!",
                "Морковка: А ты кто такой?",
                "Картошка: Я самый важный овощ!",
                "Огурец: Почему у тебя на голове банановая кожура?",
                "Морковка: ЧТО?!"
            ],
            [
                "Огурец: Клубника, я знаю твой большой секрет!",
                "Клубника: Тише! Не говори так громко!",
                "Огурец: Тогда дай мне одну клубничку!",
                "Клубника: Так вот чего ты хотел!",
                "Огурец: Нет, я ещё кое-что заметил!",
                "Клубника: Что именно?",
                "Огурец: Ты разговариваешь с холодильником!",
                "Клубника: Всё! Ты слишком много знаешь!"
            ]
        ]

        dialogue = stories[index % len(stories)]
        voice = " ".join(dialogue)

        scenes = [
            {"kicker": "МИНИ-СЕРИАЛ", "title": "Новая серия!", "body": topic},
            {"kicker": "РАЗГОВОР", "title": "Всё начинается", "body": " ".join(dialogue[:3])},
            {"kicker": "НЕОЖИДАННЫЙ ПОВОРОТ", "title": "Что происходит?", "body": " ".join(dialogue[3:6])}
        ]
        description = topic + " Смотри продолжение! #shorts #мультфильм"

    return {
        "title": title[:62],
        "description": description,
        "voiceover": voice,
        "scenes": scenes,
        "category": category
    }


def make_script():
    api_key = os.getenv("OPENROUTER_API_KEY", "").strip()

    if not api_key:
        print("OPENROUTER_API_KEY отсутствует. Используем запасной сценарий.")
        return make_fallback_script()

    day = datetime.now(timezone.utc).timetuple().tm_yday
    global_index = (day - 1) * 5 + get_video_slot() - 1

    categories = [
        "HOME", "HOME", "AI", "SERIES", "HOME",
        "AI", "SERIES", "HOME", "AI", "SERIES"
    ]
    category = categories[global_index % len(categories)]

    instructions = {
        "HOME": "Создай полезный совет о доме, кухне или хранении продуктов.",
        "AI": "Создай интересный ролик о нейросетях и искусственном интеллекте. Не выдумывай цены и возможности сервисов.",
        "SERIES": "Создай смешной эпизод мультсериала с говорящими фруктами и овощами. Добавь диалог и неожиданный конец."
    }

    prompt = f"""
Создай оригинальный сценарий для русского YouTube Shorts.

Категория: {category}
Задача: {instructions[category]}

Требования:
- Простой естественный русский язык.
- Начни с цепляющей фразы.
- Озвучка примерно 30-42 секунды.
- Примерно 65-90 слов.
- Ровно три визуальные сцены.
- Озвучка должна быть цельной.
- Верни только JSON без пояснений.

Формат:
{{
  "title": "Название",
  "description": "Описание и хештеги",
  "voiceover": "Текст озвучки",
  "scenes": [
    {{"kicker":"НАДПИСЬ","title":"Заголовок","body":"Текст"}},
    {{"kicker":"НАДПИСЬ","title":"Заголовок","body":"Текст"}},
    {{"kicker":"НАДПИСЬ","title":"Заголовок","body":"Текст"}}
  ]
}}
"""

    payload = {
        "model": "openrouter/free",
        "messages": [
            {
                "role": "system",
                "content": "Создавай оригинальные сценарии для русских Shorts. Возвращай только корректный JSON."
            },
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.9,
        "max_tokens": 1400
    }

    request = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com",
            "X-Title": "AI Shorts Factory"
        },
        method="POST"
    )

    try:
        print("Генерируем сценарий через нейросеть...")

        with urllib.request.urlopen(request, timeout=90) as response:
            result = json.loads(response.read().decode("utf-8"))

        choices = result.get("choices") or []
        if not choices:
            raise ValueError("OpenRouter вернул пустой ответ.")

        message = (choices[0] or {}).get("message") or {}
        content = message.get("content")

        if isinstance(content, list):
            content = "".join(
                part.get("text", "")
                for part in content
                if isinstance(part, dict)
            )

        if not isinstance(content, str) or not content.strip():
            raise ValueError("OpenRouter вернул пустой текст.")

        content = re.sub(
            r"^```(?:json)?\s*|\s*```$",
            "",
            content.strip(),
            flags=re.IGNORECASE
        )

        start = content.find("{")
        end = content.rfind("}")

        if start == -1 or end == -1:
            raise ValueError("Ответ не содержит JSON.")

        data = json.loads(content[start:end + 1])

        title = str(data.get("title") or "").strip()
        description = str(data.get("description") or "").strip()
        voiceover = str(data.get("voiceover") or "").strip()
        scenes = data.get("scenes")

        if not title or not voiceover:
            raise ValueError("Пустое название или озвучка.")

        if len(voiceover) > 1600:
            raise ValueError("Слишком длинная озвучка.")

        if not isinstance(scenes, list) or len(scenes) != 3:
            raise ValueError("Нужно ровно три сцены.")

        clean_scenes = []
        for scene in scenes:
            if not isinstance(scene, dict):
                raise ValueError("Некорректная сцена.")

            clean_scenes.append({
                "kicker": str(scene.get("kicker") or "")[:35],
                "title": str(scene.get("title") or "")[:100],
                "body": str(scene.get("body") or "")[:350]
            })

        if not all(s["title"] and s["body"] for s in clean_scenes):
            raise ValueError("В одной из сцен нет текста.")

        if "#shorts" not in description.lower():
            description += " #shorts"

        print("Сценарий создан:", title)

        return {
            "title": title[:62],
            "description": description,
            "voiceover": voiceover,
            "scenes": clean_scenes,
            "category": category
        }

    except Exception as error:
        print("Ошибка генерации сценария:", str(error))
        print("Используем запасной сценарий.")
        return make_fallback_script()


def make_voice(text, path, category="HOME"):
    wav = path.with_suffix(".wav")

    # Более медленная речь.
    speeds = {
        "HOME": "105",
        "AI": "100",
        "SERIES": "95"
    }
    speech_speed = speeds.get(category, "100")

    text = str(text or "")
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"[*_`#]", "", text)
    text = re.sub(r"[^\w\s.,!?;:—–()«»\"'-]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    if not text or not re.search(r"[а-яА-ЯёЁ]", text):
        raise RuntimeError("Нет нормального русского текста для озвучки.")

    subprocess.run(
        [
            "espeak-ng",
            "-v", "ru",
            "-s", speech_speed,
            "-a", "180",
            "-g", "7",
            "-w", str(wav),
            "--stdin"
        ],
        input=text,
        text=True,
        check=True
    )

    if not wav.exists() or wav.stat().st_size < 1000:
        raise RuntimeError("Не удалось создать аудио.")

    probe = subprocess.check_output(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(wav)
        ],
        text=True
    )

    duration = float(probe.strip())
    if duration <= 0:
        raise RuntimeError("Неверная длительность аудио.")

    speed_factor = max(1.0, duration / (MAX_DURATION * 1.5))
    filters = []

    while speed_factor > 2.0:
        filters.append("atempo=2.0")
        speed_factor /= 2.0

    if speed_factor > 1.0:
        filters.append(f"atempo={speed_factor:.4f}")

    filters.append("loudnorm=I=-16:TP=-1.5:LRA=11")

    subprocess.run(
        [
            "ffmpeg", "-y",
            "-loglevel", "error",
            "-i", str(wav),
            "-af", ",".join(filters),
            "-ar", "44100",
            "-ac", "2",
            "-codec:a", "libmp3lame",
            "-b:a", "128k",
            str(path)
        ],
        check=True
    )

    wav.unlink(missing_ok=True)
    print("Русская озвучка создана:", path)


def render(data, audio_path, video_path):
    blender = shutil.which("blender")
    if not blender:
        raise RuntimeError("Blender не найден. Проверь установку в daily.yml.")

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

    print("Запускаем Blender 5: создание 3D-мультфильма...")

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

    subprocess.run(command, check=True)

    if not silent_video.exists() or silent_video.stat().st_size < 100_000:
        raise RuntimeError("Blender не создал видео.")

    print("Добавляем русскую озвучку...")

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
            "-crf", "23",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "128k",
            "-t", str(duration),
            "-movflags", "+faststart",
            str(video_path)
        ],
        check=True
    )

    print("Видео готово:", video_path)


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
            "categoryId": "28",
            "defaultLanguage": "ru"
        },
        "status": {
            "privacyStatus": os.getenv("YOUTUBE_PRIVACY", "private"),
            "selfDeclaredMadeForKids": False
        }
    }

    req = yt.videos().insert(
        part="snippet,status",
        body=body,
        media_body=MediaFileUpload(
            str(video_path),
            mimetype="video/mp4",
            resumable=True
        )
    )

    response = req.execute()
    print("YOUTUBE_VIDEO_ID=" + response["id"])


def main():
    print("================================")
    print("AI SHORTS FACTORY")
    print("Starting video generation...")
    print("================================")

    data = make_script()

    (OUT / "last_script.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    audio = OUT / "voice.mp3"
    video = OUT / "short.mp4"

    print("Создаём русскую озвучку...")
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
