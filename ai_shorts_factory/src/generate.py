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
    """Create a Russian Short from the built-in editorial library; no AI API key is needed."""
    topics=[x.strip() for x in (ROOT/'topics.txt').read_text(encoding='utf-8').splitlines() if x.strip() and not x.startswith('#')]
    if not topics:
        raise RuntimeError('topics.txt пустой')
    day=datetime.now(timezone.utc).timetuple().tm_yday
    slot=os.getenv('VIDEO_SLOT','').strip()
    if not slot:
        event_file=os.getenv('GITHUB_EVENT_PATH','')
        try:
            event=json.loads(Path(event_file).read_text(encoding='utf-8')) if event_file else {}
            schedule=event.get('schedule','')
            slot={'0 7 * * *':'1','0 10 * * *':'2','0 13 * * *':'3','0 16 * * *':'4','0 19 * * *':'5'}.get(schedule,'1')
        except Exception:
            slot='1'
    slot_num=max(1,min(5,int(slot)))
    index=((day-1)*5+slot_num-1) % len(topics)
    topic=topics[index]
    angle=(day*7+slot_num*3) % 4
    openers=[
        'Представь, что ты пользуешься этой технологией каждый день, даже не замечая этого.',
        'Об этой технологии говорят часто, но принцип её работы проще, чем кажется.',
        'Давай разберёмся, что происходит за кулисами этой технологии.',
        'Вот короткое объяснение технологии, которая уже меняет привычные вещи.'
    ]
    endings=[
        'Главное — помнить: технология помогает человеку, но не заменяет проверку и здравый смысл.',
        'Поэтому важно понимать не только возможности, но и ограничения этой технологии.',
        'Теперь ты знаешь базовый принцип. А дальше всё зависит от того, как именно его применять.',
        'Технология развивается, поэтому полезно следить за новыми возможностями и проверять информацию.'
    ]
    title=topic.rstrip('?.!')
    short_title=title if len(title)<=62 else title[:59].rsplit(' ',1)[0]+'…'
    scenes=[
      {'kicker':'ПРОСТОЕ ОБЪЯСНЕНИЕ','title':'Что это такое?','body':f'{title}. Разберём идею без сложных терминов.'},
      {'kicker':'КАК ЭТО РАБОТАЕТ','title':'В чём принцип?','body':'Система получает входные данные, обрабатывает их по заданным правилам и формирует результат.'},
      {'kicker':'ЧТО ВАЖНО ЗНАТЬ','title':'Польза и ограничения','body':'Результат зависит от качества данных, настроек и задачи. Важные выводы стоит проверять.'}
    ]
    if angle==1:
      scenes[1]['title']='Где применяется?'; scenes[1]['body']='Такие решения используют в цифровых сервисах, бизнесе, образовании и повседневных инструментах — в зависимости от конкретной задачи.'
    elif angle==2:
      scenes[1]['title']='Что внутри?'; scenes[1]['body']='Обычно есть входные данные, алгоритм обработки и результат. Чем понятнее задача и качественнее данные, тем полезнее итог.'
    elif angle==3:
      scenes[2]['title']='Где ошибается?'; scenes[2]['body']='Технология может ошибаться, если данные неполные, условия изменились или задача поставлена неточно. Поэтому нужен контроль человека.'
    voice=' '.join([openers[angle], f'Сегодня тема — {title.lower()}.', scenes[0]['body'], scenes[1]['body'], scenes[2]['body'], endings[angle]])
    description=f'Коротко и простыми словами: {title.lower()}. Подписывайся на новые разборы технологий. #shorts #ии #технологии'
    return {'title':short_title,'description':description,'voiceover':voice,'scenes':scenes}


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
    asyncio.run(make_voice(data['voiceover'],audio))
    render(data,audio,video)
    if os.getenv('UPLOAD_TO_YOUTUBE','false').lower()=='true': upload(video,data)
    print('Created:',video)

if __name__=='__main__': main()
