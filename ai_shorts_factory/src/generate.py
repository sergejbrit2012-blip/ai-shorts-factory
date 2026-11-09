import os
import json
import re
import time
import urllib.request
import urllib.error
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse, urlencode

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output"
OUT.mkdir(exist_ok=True)

MAX_DURATION = 44.5

AGNES_BASE = "https://apihub.agnes-ai.com"
AGNES_MODEL = "agnes-video-2.5-flash"

SCENE_SECONDS = "12"
POLL_INTERVAL = 15

# До часа ожидания свободного места в очереди.
QUEUE_WAIT_SECONDS = 60 * 60

# До часа ожидания готовности уже принятой задачи.
MAX_WAIT_SECONDS = 60 * 60

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


def valid_file(path, minimum_size=10000):
    path = Path(path)
    return (
        path.exists()
        and path.is_file()
        and path.stat().st_size >= minimum_size
    )


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
        print("Нет OPENROUTER_API_KEY. Используем запасной сценарий.")
        return make_fallback_script()

    prompt = """
Придумай оригинальный сценарий для русского YouTube Shorts.

Тема: интересный и полезный совет о продуктах, еде или их хранении.
Главный герой — сам продукт, который разговаривает от первого лица.

Требования:
- Русский язык.
- Озвучка примерно 55-70 слов.
- Интересное начало.
- Ровно три сцены.
- У каждой сцены есть kicker, title и body.
- Каждая сцена описывает отдельное действие.
- Не придумывай медицинские обещания.
- Не выдумывай опасные советы по хранению.
- Верни только JSON.

Формат:
{
"title":"Название",
"description":"Описание и #shorts",
"voiceover":"Полный текст озвучки",
"scenes":[
{"kicker":"НАЧАЛО","title":"Заголовок","body":"Описание действия"},
{"kicker":"СОВЕТ","title":"Заголовок","body":"Описание действия"},
{"kicker":"ФИНАЛ","title":"Заголовок","body":"Описание действия"}
]
}
"""

    payload = {
        "model": "openrouter/free",
        "messages": [
            {
                "role": "system",
                "content": "Ты профессиональный автор сценариев мультфильмов. Возвращай только JSON."
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

        content = (choices[0].get("message") or {}).get("content")

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

        if not all(
            item["title"] and item["body"]
            for item in clean_scenes
        ):
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


def load_or_create_script():
    script_file = OUT / "last_script.json"

    # Если GitHub восстановил прошлый сценарий из кэша,
    # используем его, а не создаём новый.
    if valid_file(script_file, 20):
        try:
            data = json.loads(
                script_file.read_text(encoding="utf-8")
            )

            if (
                isinstance(data, dict)
                and data.get("title")
                and data.get("voiceover")
                and isinstance(data.get("scenes"), list)
                and len(data["scenes"]) == 3
            ):
                data["hero"] = choose_hero(
                    data["title"],
                    data["voiceover"]
                )

                print("Найден сохранённый сценарий.")
                print("Продолжаем предыдущую генерацию.")
                return data

        except Exception as error:
            print("Не удалось прочитать сохранённый сценарий:", error)

    data = make_script()

    script_file.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    return data


def make_voice(text, path, category="HOME"):
    wav = path.with_suffix(".wav")

    text = clean_text(text, 2000)
    text = re.sub(r"[*_`#]", "", text)

    if not text or not re.search(r"[а-яА-ЯёЁ]", text):
        raise RuntimeError("Нет русского текста для озвучки.")

    subprocess.run(
        [
            "espeak-ng",
            "-v", "ru",
            "-s", "125",
            "-p", "48",
            "-a", "175",
            "-g", "10",
            "-w", str(wav),
            "--stdin"
        ],
        input=text,
        text=True,
        check=True
    )

    if not valid_file(wav, 1000):
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

    if not valid_file(path, 1000):
        raise RuntimeError("MP3-файл озвучки не создан.")

    print("Озвучка создана:", path)


def make_subtitles(text, audio_path, subtitle_path):
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

    sentences = re.split(
        r"(?<=[.!?])\s+",
        clean_text(text, 2000)
    )

    sentences = [s.strip() for s in sentences if s.strip()]

    if not sentences:
        raise RuntimeError("Не удалось создать субтитры.")

    weights = [
        max(1, len(re.findall(r"\w+", sentence)))
        for sentence in sentences
    ]

    total = sum(weights)
    current = 0.0

    def timestamp(seconds):
        ms = int(seconds * 1000)
        hours = ms // 3600000
        minutes = (ms % 3600000) // 60000
        seconds_part = (ms % 60000) // 1000
        millis = ms % 1000

        return (
            f"{hours:02}:{minutes:02}:"
            f"{seconds_part:02},{millis:03}"
        )

    lines = []

    for index, (sentence, weight) in enumerate(
        zip(sentences, weights), 1
    ):
        segment = duration * weight / total
        end = min(duration, current + segment)

        lines.extend([
            str(index),
            f"{timestamp(current)} --> {timestamp(end)}",
            sentence,
            ""
        ])

        current = end

    subtitle_path.write_text(
        "\n".join(lines),
        encoding="utf-8"
    )

    print("Субтитры созданы:", subtitle_path)


def find_value(data, names):
    if isinstance(data, dict):
        for name in names:
            value = data.get(name)

            if value not in (None, ""):
                return value

        for value in data.values():
            found = find_value(value, names)

            if found not in (None, ""):
                return found

    elif isinstance(data, list):
        for item in data:
            found = find_value(item, names)

            if found not in (None, ""):
                return found

    return None


def agnes_request(
    url,
    method="GET",
    payload=None,
    timeout=120,
    queue_wait_seconds=0,
    max_retries=8
):
    api_key = os.getenv("AGNES_API_KEY", "").strip()

    if not api_key:
        raise RuntimeError("Не найден секрет AGNES_API_KEY.")

    headers = {
        "Authorization": "Bearer " + api_key,
        "Accept": "application/json"
    }

    body = None

    if payload is not None:
        headers["Content-Type"] = "application/json"
        body = json.dumps(payload).encode("utf-8")

    method = method.upper()

    queue_deadline = (
        time.monotonic() + queue_wait_seconds
        if queue_wait_seconds > 0
        else None
    )

    attempt = 0

    while True:
        request = urllib.request.Request(
            url,
            data=body,
            headers=headers,
            method=method
        )

        try:
            with urllib.request.urlopen(
                request,
                timeout=timeout
            ) as response:
                raw = response.read().decode("utf-8")
                return json.loads(raw)

        except urllib.error.HTTPError as error:
            details = error.read().decode(
                "utf-8",
                errors="replace"
            )[:3000]

            # POST повторяем только при явном отказе очереди
            # или ограничении частоты запросов.
            is_queue_full = (
                error.code == 503
                and "video_queue_full" in details.lower()
            )

            is_rate_limited = error.code == 429

            if (
                method == "POST"
                and queue_deadline is not None
                and (is_queue_full or is_rate_limited)
            ):
                remaining = queue_deadline - time.monotonic()

                if remaining <= 0:
                    raise RuntimeError(
                        "Agnes не освободил очередь за 60 минут. "
                        "Последняя ошибка: " + details
                    )

                retry_after = error.headers.get("Retry-After")

                try:
                    delay = float(retry_after)
                except (TypeError, ValueError):
                    delay = min(30 * (attempt + 1), 180)

                delay = max(5, min(delay, 180, remaining))

                attempt += 1

                print()
                print("Очередь Agnes переполнена или ограничена.")
                print(f"Попытка ожидания: {attempt}")
                print(f"Повторная отправка через {int(delay)} секунд.")
                print(
                    "Оставшееся время ожидания:",
                    int(remaining // 60),
                    "мин."
                )
                print()

                time.sleep(delay)
                continue

            # GET-запросы можно безопасно повторять.
            retry_codes = (429, 500, 502, 503, 504)

            if method == "GET" and error.code in retry_codes:
                if attempt < max_retries:
                    delay = min(10 * (2 ** attempt), 120)
                    attempt += 1

                    print(
                        f"Ошибка Agnes HTTP {error.code}. "
                        f"Повтор GET через {delay} секунд."
                    )

                    time.sleep(delay)
                    continue

            raise RuntimeError(
                f"Agnes API HTTP {error.code}: {details}"
            )

        except (
            urllib.error.URLError,
            TimeoutError,
            OSError
        ) as error:

            # Не повторяем POST после неизвестной сетевой ошибки:
            # сервер мог принять задачу, даже если ответ потерялся.
            if method == "POST":
                raise RuntimeError(
                    "Сетевая ошибка при отправке задачи Agnes. "
                    "Не повторяем POST автоматически, чтобы не "
                    "создать дублирующую задачу: " + str(error)
                )

            if attempt >= max_retries:
                raise RuntimeError(
                    f"Ошибка соединения с Agnes: {error}"
                )

            delay = min(10 * (2 ** attempt), 120)
            attempt += 1

            print(
                f"Проблема соединения. Повтор через {delay} секунд."
            )

            time.sleep(delay)


def create_agnes_video(prompt, output_path):
    output_path = Path(output_path)

    # Не генерируем повторно уже скачанную сцену.
    if valid_file(output_path):
        print("Найдена готовая сцена. Пропускаем Agnes:", output_path)
        return output_path

    print("Отправляем сцену в Agnes AI...")
    print("Модель:", AGNES_MODEL)

    payload = {
        "model": AGNES_MODEL,
        "prompt": prompt,
        "mode": "text",
        "seconds": SCENE_SECONDS,
        "size": "720P",
        "aspect_ratio": "9:16",
        "n": 1
    }

    result = agnes_request(
        AGNES_BASE + "/v1/videos",
        method="POST",
        payload=payload,
        timeout=180,
        queue_wait_seconds=QUEUE_WAIT_SECONDS
    )

    video_id = find_value(result, ["video_id"])

    if not video_id:
        video_id = find_value(result, ["task_id"])

    if not video_id:
        raise RuntimeError(
            "Agnes не вернул video_id: "
            + json.dumps(result, ensure_ascii=False)[:2000]
        )

    print("Задача Agnes создана:", video_id)

    started = time.monotonic()
    video_url = None

    while time.monotonic() - started < MAX_WAIT_SECONDS:
        time.sleep(POLL_INTERVAL)

        query = urlencode({
            "video_id": str(video_id),
            "model_name": AGNES_MODEL
        })

        status_data = agnes_request(
            AGNES_BASE + "/agnesapi?" + query,
            timeout=120,
            max_retries=8
        )

        status = str(
            find_value(status_data, ["status"]) or ""
        ).lower()

        progress = find_value(
            status_data,
            ["progress", "percentage"]
        )

        if progress is not None:
            print("Прогресс сцены:", progress)

        metadata = status_data.get("metadata", {})

        if not isinstance(metadata, dict):
            metadata = {}

        video_url = (
            metadata.get("url")
            or metadata.get("video_url")
            or find_value(
                status_data,
                ["video_url", "download_url"]
            )
            or status_data.get("url")
        )

        if status in (
            "completed",
            "complete",
            "success",
            "succeeded",
            "done"
        ):
            if not video_url:
                raise RuntimeError(
                    "Agnes сообщил о готовности, но не вернул URL: "
                    + json.dumps(
                        status_data,
                        ensure_ascii=False
                    )[:2000]
                )

            break

        if status in (
            "failed",
            "error",
            "cancelled",
            "canceled"
        ):
            raise RuntimeError(
                "Генерация Agnes завершилась ошибкой: "
                + json.dumps(
                    status_data,
                    ensure_ascii=False
                )[:2000]
            )

        print(
            "Agnes генерирует сцену. Статус:",
            status or "ожидание"
        )

    else:
        raise TimeoutError(
            "Agnes не успел создать сцену за 60 минут."
        )

    parsed = urlparse(str(video_url))

    if parsed.scheme not in ("http", "https"):
        raise RuntimeError("Agnes вернул некорректную ссылку.")

    print("Скачиваем готовую сцену...")

    download_request = urllib.request.Request(
        str(video_url),
        headers={"User-Agent": "AI-Shorts-Factory"}
    )

    temporary_file = output_path.with_name(
        output_path.stem + "_download.mp4"
    )

    with urllib.request.urlopen(
        download_request,
        timeout=240
    ) as response:
        temporary_file.write_bytes(response.read())

    if not valid_file(temporary_file):
        temporary_file.unlink(missing_ok=True)
        raise RuntimeError(
            "Скачанный видеофайл пустой или повреждён."
        )

    temporary_file.replace(output_path)

    print("Сцена скачана:", output_path)

    return output_path


def build_scene_prompt(data, scene, scene_number):
    hero = data["hero"]
    name = hero["name"]

    actions = [
        "The character introduces itself to the viewer, waves with one hand and smiles.",
        "The character demonstrates the useful tip with clear physical actions and expressive gestures.",
        "The character finishes with a friendly memorable gesture, smiles and waves goodbye."
    ]

    action = actions[scene_number - 1]

    return (
        "Create a high quality polished 3D animated family-friendly "
        "cartoon video, vertical portrait 9:16 composition. "
        "A cute anthropomorphic " + hero["id"] +
        " character, recognizable as " + name +
        ", is the main hero. "
        "The character has large expressive eyes, a friendly smiling face, "
        "small arms and legs, colorful simple clothes. "
        "Keep the same character appearance throughout this clip. "
        "Beautiful detailed environment related to the story, "
        "cinematic soft lighting, rich colors, smooth natural "
        "character animation, expressive gestures, professional "
        "animated movie quality. "
        "The character must be visible clearly in the center. "
        "Use a medium camera shot and gentle cinematic camera movement. "
        "Scene action: " + action + " "
        "Scene heading: " + scene["title"] + ". "
        "Scene description: " + scene["body"] + ". "
        "Topic: " + data["title"] + ". "
        "No written words, no captions, no logos, no watermark. "
        "Do not show multiple copies of the character."
    )


def normalize_scene(raw_video, normalized_video, index):
    print("Подготавливаем сцену", index)

    normalized_video.unlink(missing_ok=True)

    subprocess.run(
        [
            "ffmpeg", "-y",
            "-loglevel", "error",
            "-i", str(raw_video),
            "-an",
            "-vf",
            "scale=720:1280:force_original_aspect_ratio=increase,"
            "crop=720:1280,fps=24,setsar=1,format=yuv420p",
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "20",
            "-movflags", "+faststart",
            str(normalized_video)
        ],
        check=True
    )

    if not valid_file(normalized_video):
        raise RuntimeError(
            f"Не удалось подготовить сцену {index}."
        )

    print("Подготовленная сцена сохранена:", normalized_video)


def render(data, audio_path, video_path):
    print("Запускаем генерацию видео через Agnes AI.")
    print("Используется модель:", AGNES_MODEL)

    scene_files = []

    for index, scene in enumerate(data["scenes"], 1):
        prompt = build_scene_prompt(data, scene, index)

        prompt_file = OUT / f"scene_{index}_prompt.txt"
        prompt_file.write_text(prompt, encoding="utf-8")

        raw_video = OUT / f"scene_{index}_raw.mp4"
        normalized_video = OUT / f"scene_{index}.mp4"

        print()
        print(f"ПРОВЕРКА СЦЕНЫ {index} ИЗ 3")

        # Сначала проверяем уже подготовленную сцену.
        if valid_file(normalized_video):
            print("Сцена уже готова. Повторно не генерируем.")
            scene_files.append(normalized_video)
            continue

        # Если исходное видео скачано, но не обработано,
        # используем его без нового обращения к Agnes.
        if valid_file(raw_video):
            print("Найдено сохранённое исходное видео.")
            normalize_scene(
                raw_video,
                normalized_video,
                index
            )
            scene_files.append(normalized_video)
            continue

        print(f"Генерируем сцену {index} из 3...")

        create_agnes_video(prompt, raw_video)

        normalize_scene(
            raw_video,
            normalized_video,
            index
        )

        scene_files.append(normalized_video)

    concat_file = OUT / "concat_list.txt"

    concat_file.write_text(
        "".join(
            "file '" + str(path.resolve()) + "'\n"
            for path in scene_files
        ),
        encoding="utf-8"
    )

    silent_video = OUT / "agnes_combined.mp4"

    print("Объединяем три сцены...")

    silent_video.unlink(missing_ok=True)

    subprocess.run(
        [
            "ffmpeg", "-y",
            "-loglevel", "error",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_file),
            "-c", "copy",
            str(silent_video)
        ],
        check=True
    )

    if not valid_file(silent_video, 30000):
        raise RuntimeError("Не удалось объединить сцены.")

    audio_duration = float(subprocess.check_output(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(audio_path)
        ],
        text=True
    ).strip())

    video_duration = float(subprocess.check_output(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(silent_video)
        ],
        text=True
    ).strip())

    duration = min(
        audio_duration,
        video_duration,
        MAX_DURATION
    )

    duration = max(1.0, duration)

    subtitle_path = OUT / "subtitles.srt"

    make_subtitles(
        data["voiceover"],
        audio_path,
        subtitle_path
    )

    subtitle_filter = (
        "subtitles="
        + str(subtitle_path).replace("\\", "/").replace(":", r"\:")
        + ":force_style='FontName=DejaVu Sans,FontSize=18,"
          "PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,"
          "BorderStyle=1,Outline=2,Shadow=1,Alignment=2,MarginV=95'"
    )

    print("Собираем финальное видео с озвучкой...")

    video_path.unlink(missing_ok=True)

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
        "-crf", "20",
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
        print("Не удалось вшить субтитры. Повторяем без них.")

        video_path.unlink(missing_ok=True)

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
                "-crf", "20",
                "-pix_fmt", "yuv420p",
                "-c:a", "aac",
                "-b:a", "160k",
                "-t", str(duration),
                "-movflags", "+faststart",
                str(video_path)
            ],
            check=True
        )

    if not valid_file(video_path, 30000):
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

        token_file.write_text(
            creds.to_json(),
            encoding="utf-8"
        )

    yt = build("youtube", "v3", credentials=creds)

    body = {
        "snippet": {
            "title": data["title"][:100],
            "description": data["description"],
            "categoryId": "22",
            "defaultLanguage": "ru"
        },
        "status": {
            "privacyStatus": os.getenv(
                "YOUTUBE_PRIVACY",
                "private"
            ),
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
    print("AI SHORTS FACTORY — AGNES VIDEO 2.5 FLASH")
    print("================================")

    if not os.getenv("AGNES_API_KEY", "").strip():
        raise RuntimeError(
            "Добавь секрет AGNES_API_KEY в GitHub."
        )

    data = load_or_create_script()

    audio = OUT / "voice.mp3"
    video = OUT / "short.mp4"

    print("Проверяем русскую озвучку...")

    if valid_file(audio, 1000):
        print("Найдена сохранённая озвучка. Повторно не создаём.")
    else:
        print("Создаём русскую озвучку...")
        make_voice(
            data["voiceover"],
            audio,
            data.get("category", "HOME")
        )

    print("Создаём AI-видео...")

    render(data, audio, video)

    if os.getenv(
        "UPLOAD_TO_YOUTUBE",
        "false"
    ).lower() == "true":

        print("Загружаем видео на YouTube...")
        upload(video, data)

    else:
        print("Загрузка на YouTube отключена.")

    print("Создано:", video)
    print("Генерация завершена.")


if __name__ == "__main__":
    main()
