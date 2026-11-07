import os, json, re, random, asyncio, subprocess, textwrap
from datetime import datetime, timezone
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output'
OUT.mkdir(exist_ok=True)
W, H = 1080, 1920


def font(size, bold=False):
    candidates = [
        '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf' if bold else '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
        '/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf' if bold else '/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf'
    ]
    for p in candidates:
        if Path(p).exists(): return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def wrap(draw, text, fnt, max_width):
    words = text.split(); lines=[]; line=''
    for word in words:
        test=(line+' '+word).strip()
        if draw.textbbox((0,0), test, font=fnt)[2] <= max_width: line=test
        else:
            if line: lines.append(line)
            line=word
    if line: lines.append(line)
    return lines


def make_slide(kicker, title, body, idx, total):
    # Abstract technology artwork: generated locally, no stock-media dependency.
    im=Image.new('RGB',(W,H),(8,13,32)); px=im.load()
    for y in range(H):
        for x in range(W):
            glow=max(0,1-(((x-850)/900)**2+((y-320)/950)**2)**0.5)
            px[x,y]=(int(8+15*glow),int(13+28*glow),int(32+62*glow))
    d=ImageDraw.Draw(im,'RGBA')
    for r in range(180,900,130):
        d.ellipse((760-r,280-r,760+r,280+r),outline=(70,135,255,32),width=3)
    d.rounded_rectangle((70,90,1010,1830),radius=55,outline=(105,150,255,90),width=3,fill=(9,17,42,90))
    d.rounded_rectangle((115,145,965,220),radius=30,fill=(40,90,190,110))
    d.text((155,162),kicker.upper(),font=font(34,True),fill=(190,220,255,255))
    # Accent orb
    d.ellipse((770,330,920,480),fill=(70,150,255,45),outline=(120,190,255,210),width=5)
    d.ellipse((815,375,875,435),fill=(150,210,255,220))
    title_lines=wrap(d,title,font(76,True),820)
    y=600
    for line in title_lines[:4]:
        d.text((135,y),line,font=font(76,True),fill=(255,255,255,255),stroke_width=1,stroke_fill=(20,35,75,255)); y+=100
    y+=65
    for line in wrap(d,body,font(48),810)[:8]:
        d.text((140,y),line,font=font(48),fill=(205,220,245,255)); y+=75
    d.rounded_rectangle((135,1645,945,1658),radius=8,fill=(60,115,230,100))
    d.rounded_rectangle((135,1645,135+int(810*(idx+1)/total),1658),radius=8,fill=(110,185,255,255))
    d.text((140,1705),f'AI КОРОТКО  •  {idx+1}/{total}',font=font(30,True),fill=(140,175,225,255))
    path=OUT/f'scene_{idx}.png'; im.save(path); return path



def make_script():
    """Create Shorts in three categories: home tips, AI tools and funny series."""

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
            event = json.loads(Path(event_file).read_text(encoding="utf-8")) if event_file else {}
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
                "body": "Правильное хранение помогает дольше сохранять свежесть продуктов."
            },
            {
                "kicker": "ВАЖНО ЗНАТЬ",
                "title": "Полезная привычка",
                "body": "Проверяй продукты и не используй испорченные."
            }
        ]
        voice = (
            f"Ты знал об этом? {topic} "
            "Есть простые правила, которые помогают сохранить продукты свежими. "
            "Главное — соблюдать подходящие условия хранения и регулярно всё проверять."
        )
        description = f"{topic} Полезные советы на каждый день. #shorts #советы #лайфхаки"

    elif category == "AI":
        scenes = [
            {
                "kicker": "МИР НЕЙРОСЕТЕЙ",
                "title": "Какую выбрать?",
                "body": topic
            },
            {
                "kicker": "ВЫБИРАЕМ ИНСТРУМЕНТ",
                "title": "Под разные задачи",
                "body": "Одни инструменты помогают с текстами, другие создают изображения, а третьи работают с видео."
            },
            {
                "kicker": "ПОЛЕЗНЫЙ СОВЕТ",
                "title": "Проверь результат",
                "body": "Перед выбором проверь возможности, ограничения и доступность сервиса."
            }
        ]
        voice = (
            f"Не знаешь, какую нейросеть выбрать? {topic} "
            "Сначала определись с задачей. Для текстов нужны одни инструменты, "
            "для картинок другие, а для видео третьи. "
            "Не забывай проверять возможности каждого сервиса."
        )
        description = f"{topic} Нейросети простыми словами. #shorts #нейросети #ии"

    else:
        stories = [
            [
                "Клубника: Я самая красивая!",
                "Банан: А я самый популярный!",
                "Клубника: Зато тебя все очищают!",
                "Банан: Это ещё не конец нашего спора!"
            ],
            [
                "Морковка: Подожди, а кто я?",
                "Огурец: Ты же Морковка!",
                "Морковка: А почему я ничего не помню?",
                "Огурец: Кажется, я знаю, что случилось..."
            ],
            [
                "Огурец: Клубника, я знаю твой секрет!",
                "Клубника: Только никому не говори!",
                "Огурец: Тогда дай мне одну клубничку!",
                "Клубника: Так вот чего ты хотел!"
            ],
            [
                "Картошка: Теперь я здесь главный!",
                "Морковка: С чего ты это взял?",
                "Картошка: Потому что без меня не будет картошки фри!",
                "Огурец: А меня вообще кто-нибудь спросит?"
            ]
        ]

        dialogue = stories[index % len(stories)]

        scenes = [
            {
                "kicker": "МИНИ-СЕРИАЛ",
                "title": "Начало истории",
                "body": topic
            },
            {
                "kicker": "РАЗГОВОР",
                "title": "Спор начинается",
                "body": " ".join(dialogue[:2])
            },
            {
                "kicker": "ПРОДОЛЖЕНИЕ",
                "title": "Что будет дальше?",
                "body": " ".join(dialogue[2:])
            }
        ]

        voice = " ".join(dialogue)
        description = f"{topic} Смотри продолжение! #shorts #мультфильм #приколы"

    return {
        "title": short_title,
        "description": description,
        "voiceover": voice,
        "scenes": scenes
    }


def make_voice(text, path):
    # Offline Russian speech via eSpeak NG; quality is robotic but needs no paid API.
    wav=path.with_suffix('.wav')
    subprocess.run(['espeak-ng','-v','ru','-s','148','-a','165','-w',str(wav),text],check=True)
    subprocess.run(['ffmpeg','-y','-i',str(wav),'-codec:a','libmp3lame','-qscale:a','5',str(path)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    wav.unlink(missing_ok=True)

def render(data, audio_path, video_path):
    slides=[]
    for i,s in enumerate(data['scenes']): slides.append(make_slide(s.get('kicker','ТЕХНОЛОГИИ'),s['title'],s['body'],i,3))
    # 4 visual beats: hook/title card, then 3 generated scenes.
    hook=make_slide('СЕГОДНЯ ЗА 40 СЕКУНД',data['title'],'Разбираемся простыми словами',0,4)
    allslides=[hook]+slides
    # probe audio duration
    probe=subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','default=noprint_wrappers=1:nokey=1',str(audio_path)],text=True)
    duration=float(probe.strip())
    seg=duration/len(allslides)
    inputs=[]
    for p in allslides: inputs += ['-loop','1','-t',str(seg),'-i',str(p)]
    inputs += ['-i',str(audio_path)]
    filters=''.join(f'[{i}:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,format=yuv420p[v{i}];' for i in range(len(allslides)))
    filters+=''.join(f'[v{i}]' for i in range(len(allslides)))+f'concat=n={len(allslides)}:v=1:a=0[vout]'
    cmd=['ffmpeg','-y']+inputs+['-filter_complex',filters,'-map','[vout]','-map',f'{len(allslides)}:a:0','-c:v','libx264','-preset','ultrafast','-crf','24','-r','30','-c:a','aac','-b:a','128k','-shortest','-movflags','+faststart',str(video_path)]
    subprocess.run(cmd,check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)


def upload(video_path, data):
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    token_file=Path(os.getenv('YOUTUBE_TOKEN_FILE','token.json'))
    creds=Credentials.from_authorized_user_file(str(token_file),['https://www.googleapis.com/auth/youtube.upload'])
    if creds.expired and creds.refresh_token:
        creds.refresh(Request()); token_file.write_text(creds.to_json(),encoding='utf-8')
    yt=build('youtube','v3',credentials=creds)
    body={'snippet':{'title':data['title'][:100],'description':data['description']+'\n\nВизуальные материалы созданы автоматически.','categoryId':'28','defaultLanguage':'ru'},'status':{'privacyStatus':os.getenv('YOUTUBE_PRIVACY','private'),'selfDeclaredMadeForKids':False}}
    req=yt.videos().insert(part='snippet,status',body=body,media_body=MediaFileUpload(str(video_path),mimetype='video/mp4',resumable=True))
    response=req.execute()
    print('YOUTUBE_VIDEO_ID='+response['id'])


def main():
    data=make_script()
    (OUT/'last_script.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    audio=OUT/'voice.mp3'; video=OUT/'short.mp4'
    make_voice(data['voiceover'], audio)
    render(data,audio,video)
    if os.getenv('UPLOAD_TO_YOUTUBE','false').lower()=='true': upload(video,data)
    print('Created:',video)

if __name__=='__main__': main()
