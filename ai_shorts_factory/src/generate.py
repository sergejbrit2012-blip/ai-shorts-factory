
import os
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output"
OUT.mkdir(exist_ok=True)

W, H = 1080, 1920
MAX_DURATION = 44.5


def font(size, bold=False):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf"
    ]

    for p in candidates:
        if Path(p).exists():
            return ImageFont.truetype(p, size)

    return ImageFont.load_default()


def wrap(draw, text, fnt, max_width):
    words = text.split()
    lines = []
    line = ""

    for word in words:
        test = (line + " " + word).strip()

        if draw.textbbox((0, 0), test, font=fnt)[2] <= max_width:
            line = test
        else:
            if line:
                lines.append(line)
            line = word

    if line:
        lines.append(line)

    return lines


def make_slide(kicker, title, body, idx, total):
    im = Image.new("RGB", (W, H), (8, 13, 32))
    px = im.load()

    for y in range(H):
        for x in range(W):
            glow = max(
                0,
                1 - (((x - 850) / 900) ** 2 + ((y - 320) / 950) ** 2) ** 0.5
            )

            px[x, y] = (
                int(8 + 15 * glow),
                int(13 + 28 * glow),
                int(32 + 62 * glow)
            )

    d = ImageDraw.Draw(im, "RGBA")

    for r in range(180, 900, 130):
        d.ellipse(
            (760-r, 280-r, 760+r, 280+r),
            outline=(70, 135, 255, 32),
            width=3
        )

    d.rounded_rectangle(
        (70, 90, 1010, 1830),
        radius=55,
        outline=(105, 150, 255, 90),
        width=3,
        fill=(9, 17, 42, 90)
    )

    d.rounded_rectangle(
        (115, 145, 965, 220),
        radius=30,
        fill=(40, 90, 190, 110)
    )

    d.text(
        (155, 162),
        kicker.upper(),
        font=font(34, True),
        fill=(190, 220, 255, 255)
    )

    d.ellipse(
        (770, 330, 920, 480),
        fill=(70, 150, 255, 45),
        outline=(120, 190, 255, 210),
        width=5
    )

    d.ellipse(
        (815, 375, 875, 435),
        fill=(150, 210, 255, 220)
    )

    title_lines = wrap(d, title, font(76, True), 820)
    y = 600

    for line in title_lines[:4]:
        d.text(
            (135, y),
            line,
            font=font(76, True),
            fill=(255, 255, 255, 255),
            stroke_width=1,
            stroke_fill=(20, 35, 75, 255)
        )
        y += 100

    y += 65

    for line in wrap(d, body, font(48), 810)[:8]:
        d.text(
            (140, y),
            line,
            font=font(48),
            fill=(205, 220, 245, 255)
        )
        y += 75

    d.rounded_rectangle(
        (135, 1645, 945, 1658),
        radius=8,
        fill=(60, 115, 230, 100)
    )

    d.rounded_rectangle(
        (
            135,
            1645,
            135 + int(810 * (idx + 1) / total),
            1658
        ),
        radius=8,
        fill=(110, 185, 255, 255)
    )

    d.text(
        (140, 1705),
        f"AI КОРОТКО  •  {idx+1}/{total}",
        font=font(30, True),
        fill=(140, 175, 225, 255)
    )

    path = OUT / f"scene_{idx}.png"
    im.save(path)

    return path


def make_script():
    topics = [
        ("HOME", "Где лучше хранить картошку?"),
        ("HOME", "Почему хлеб быстро становится твёрдым?"),
        ("HOME", "Как правильно хранить бананы?"),
        ("HOME", "Какие продукты нельзя хранить рядом?"),

        ("AI", "Какая нейросеть лучше создаёт картинки?"),
        ("AI", "Какие нейросети помогают делать презентации?"),
        ("AI", "Какие нейросети умеют создавать видео?"),
        ("AI", "Какая нейросеть лучше помогает с текстами?"),

        ("SERIES", "Клубника спорит с Бананом"),
        ("SERIES", "Морковка забыла своё имя"),
        ("SERIES", "Огурец открыл секрет Клубники"),
        ("SERIES", "Картошка стала главным на кухне"),
    ]

    day = datetime.now(timezone.utc).timetuple().tm_yday
    slot = os.getenv("VIDEO_SLOT", "").strip()

    if not slot:
        event_file = os.getenv("GITHUB_EVENT_PATH", "")

        try:
            event = json.loads(
                Path(event_file).read_text(encoding="utf-8")
            ) if event_file else {}

            schedule = event.get("schedule", "")

            slot = {
                "0 7 * * *": "1",
                "0 10 * * *": "2",
                "0 13 * * *": "3",
                "0 16 * * *": "4",
                "0 19 * * *": "5",
            }.get(schedule, "1")

        except Exception:
            slot = "1"

    slot_num = max(1, min(5, int(slot)))
    index = ((day - 1) * 5 + slot_num - 1) % len(topics)

    category, topic = topics[index]

    title = topic.rstrip("?.!")
    short_title = title if len(title) <= 62 else title[:59].rsplit(" ", 1)[0] + "…"

    if category == "HOME":

        scenes = [
            {
                "kicker": "ПОЛЕЗНЫЙ СОВЕТ",
                "title": "Ты знал об этом?",
                "body": topic
            },
            {
                "kicker": "КАК ПРАВИЛЬНО",
                "title": "Запомни это",
                "body": "У каждого продукта свои условия хранения."
            },
            {
                "kicker": "ВАЖНО ЗНАТЬ",
                "title": "Не повторяй ошибку",
                "body": "Проверяй условия хранения и следи за свежестью продуктов."
            }
        ]

        voice = (
            f"Стоп! А ты правильно хранишь продукты? {topic} "
            "Не стоит складывать всё подряд в одно место. "
            "У каждого продукта свои условия хранения. "
            "Учитывай температуру, влажность и соседство с другими продуктами. "
            "Проверяй упаковку и рекомендации производителя. "
            "Сохрани этот совет, чтобы не забыть!"
        )

        description = (
            f"{topic} Полезные советы на каждый день. "
            "#shorts #советы #лайфхаки"
        )

    elif category == "AI":

        scenes = [
            {
                "kicker": "МИР НЕЙРОСЕТЕЙ",
                "title": "Какую выбрать?",
                "body": topic
            },
            {
                "kicker": "ВЫБИРАЕМ ИНСТРУМЕНТ",
                "title": "У каждой своя задача",
                "body": "Одни сервисы помогают с текстами, другие создают изображения и видео."
            },
            {
                "kicker": "ПОЛЕЗНЫЙ СОВЕТ",
                "title": "Не выбирай наугад",
                "body": "Сравни возможности, ограничения и доступность сервисов."
            }
        ]

        voice = (
            f"Хочешь выбрать нейросеть и не потратить время зря? {topic} "
            "Сначала реши, что тебе нужно. "
            "Для написания текстов подойдут одни инструменты, "
            "для создания картинок — другие, а для видео — третьи. "
            "Проверь бесплатные возможности и ограничения. "
            "И помни: результат нейросети всегда стоит проверить!"
        )

        description = (
            f"{topic} Нейросети простыми словами. "
            "#shorts #нейросети #ии"
        )

    else:

        stories = [
            [
                "Клубника: Я самая красивая ягода на кухне!",
                "Банан: Ха! Зато меня знают во всём мире!",
                "Клубника: Да тебя даже перед едой раздевают!",
                "Банан: А тебя кладут в десерты только для украшения!",
                "Клубника: Повтори ещё раз!",
                "Банан: Ладно, давай устроим соревнование!",
                "Клубника: Кто победит, тот и будет главным!",
                "Банан: Договорились! Но я уже придумал хитрый план!"
            ],
            [
                "Морковка: Подождите... А кто я вообще такая?",
                "Огурец: Ты Морковка! Мы же знакомы сто лет!",
                "Морковка: А почему я ничего не помню?",
                "Картошка: Кажется, она опять всё перепутала!",
                "Морковка: А ты кто такой?",
                "Картошка: Я Картошка! Самый важный овощ!",
                "Огурец: Почему у Морковки на голове банановая кожура?",
                "Морковка: ЧТО?!"
            ],
            [
                "Огурец: Клубника, я знаю твой большой секрет!",
                "Клубника: Тише! Не говори так громко!",
                "Огурец: Тогда дай мне одну клубничку!",
                "Клубника: Так вот чего ты хотел!",
                "Огурец: Нет, я ещё кое-что заметил!",
                "Клубника: Что именно?",
                "Огурец: Ты каждый вечер тайком разговариваешь с холодильником!",
                "Клубника: Всё! Ты слишком много знаешь!"
            ],
            [
                "Картошка: С сегодняшнего дня я здесь главный!",
                "Морковка: И с чего ты это взял?",
                "Картошка: Без меня не будет картошки фри!",
                "Огурец: А салат тогда кто будет делать?",
                "Картошка: Это уже не мои проблемы!",
                "Морковка: Тогда мы создадим свою команду!",
                "Огурец: И назовём её Великий Овощной Союз!",
                "Картошка: Эй! А меня почему не позвали?"
            ]
        ]

        dialogue = stories[index % len(stories)]

        scenes = [
            {
                "kicker": "МИНИ-СЕРИАЛ",
                "title": "Новая серия!",
                "body": topic
            },
            {
                "kicker": "РАЗГОВОР",
                "title": "Всё начинается",
                "body": " ".join(dialogue[:3])
            },
            {
                "kicker": "НЕОЖИДАННЫЙ ПОВОРОТ",
                "title": "Что происходит?",
                "body": " ".join(dialogue[3:6])
            }
        ]

        voice = " ".join(dialogue)

        description = (
            f"{topic} Смотри продолжение! "
            "#shorts #мультфильм #приколы"
        )

    return {
        "title": short_title,
        "description": description,
        "voiceover": voice,
        "scenes": scenes,
        "category": category
    }


def make_voice(text, path, category="HOME"):
    wav = path.with_suffix(".wav")

    speeds = {
        "HOME": "165",
        "AI": "155",
        "SERIES": "125"
    }

    speech_speed = speeds.get(category, "155")

    subprocess.run(
        [
            "espeak-ng",
            "-v", "ru",
            "-s", speech_speed,
            "-a", "165",
            "-g", "8",
            "-w", str(wav),
            text
        ],
        check=True
    )

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

    speed_factor = max(1.0, duration / MAX_DURATION)

    command = [
        "ffmpeg", "-y",
        "-i", str(wav),
        "-vn"
    ]

    if speed_factor > 1.0:
        command += [
            "-filter:a",
            f"atempo={speed_factor:.4f}"
        ]

    command += [
        "-codec:a", "libmp3lame",
        "-b:a", "128k",
        str(path)
    ]

    subprocess.run(
        command,
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    wav.unlink(missing_ok=True)


def render(data, audio_path, video_path):
    slides = []

    for i, s in enumerate(data["scenes"]):
        slides.append(
            make_slide(
                s.get("kicker", "ТЕХНОЛОГИИ"),
                s["title"],
                s["body"],
                i,
                3
            )
        )

    hook = make_slide(
        "СЕГОДНЯ ЗА 40 СЕКУНД",
        data["title"],
        "Разбираемся простыми словами",
        0,
        4
    )

    allslides = [hook] + slides

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
    seg = duration / len(allslides)

    inputs = []

    for p in allslides:
        inputs += [
            "-loop", "1",
            "-t", str(seg),
            "-i", str(p)
        ]

    inputs += ["-i", str(audio_path)]

    filters = "".join(
        f"[{i}:v]scale=1080:1920:force_original_aspect_ratio=increase,"
        f"crop=1080:1920,setsar=1,format=yuv420p[v{i}];"
        for i in range(len(allslides))
    )

    filters += "".join(
        f"[v{i}]"
        for i in range(len(allslides))
    )

    filters += (
        f"concat=n={len(allslides)}:v=1:a=0[vout]"
    )

    cmd = (
        ["ffmpeg", "-y"]
        + inputs
        + [
            "-filter_complex", filters,
            "-map", "[vout]",
            "-map", f"{len(allslides)}:a:0",
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-crf", "24",
            "-r", "30",
            "-c:a", "aac",
            "-b:a", "128k",
            "-t", str(MAX_DURATION),
            "-shortest",
            "-movflags", "+faststart",
            str(video_path)
        ]
    )

    subprocess.run(
        cmd,
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    final_probe = subprocess.check_output(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(video_path)
        ],
        text=True
    )

    final_duration = float(final_probe.strip())

    print(f"Video duration: {final_duration:.1f} seconds")
    print("Video format: 1080x1920 vertical")


def upload(video_path, data):
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload

    token_file = Path(
        os.getenv("YOUTUBE_TOKEN_FILE", "token.json")
    )

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

    yt = build(
        "youtube",
        "v3",
        credentials=creds
    )

    body = {
        "snippet": {
            "title": data["title"][:100],
            "description": data["description"] + "\n\nВизуальные материалы созданы автоматически.",
            "categoryId": "28",
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
    data = make_script()

    (OUT / "last_script.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    audio = OUT / "voice.mp3"
    video = OUT / "short.mp4"

    make_voice(
        data["voiceover"],
        audio,
        data["category"]
    )

    render(data, audio, video)

    if os.getenv("UPLOAD_TO_YOUTUBE", "false").lower() == "true":
        upload(video, data)

    print("Created:", video)


if __name__ == "__main__":
    main()
