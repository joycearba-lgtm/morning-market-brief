"""Generate optional Hebrew daily MP3 using a locally executed open-source BlueTTS voice.
Runs in GitHub Actions: no third-party paid speech API. If any dependency
fails, the website continues to work and no stale audio is labelled today's.
"""
import json
import subprocess
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

def main():
    data=json.loads(Path("macro_brief.json").read_text(encoding="utf-8"))
    today=datetime.now(ZoneInfo("Asia/Jerusalem")).date().isoformat()
    if data.get("date")!=today or data.get("status")=="unavailable":
        print("No current editorial brief; not creating audio")
        return
    import re
    def speaking(text):
        text=str(text or "")
        for src,dest in (("AI","בינה מלאכותית"),("ECB","הבנק המרכזי האירופי"),
                         ("CPI","מדד המחירים לצרכן"),("GDP","תוצר מקומי גולמי"),
                         ("Nasdaq","נאסדק"),("מח״מ","משך חיים ממוצע"),
                         ("אג״ח","איגרות חוב"),("ארה״ב","ארצות הברית"),
                         ("תמ״ג","תוצר מקומי גולמי")):
            text=text.replace(src,dest)
        def say_percent(m):
            digits={"0":"אפס","1":"אחת","2":"שתיים","3":"שלוש",
                    "4":"ארבע","5":"חמש","6":"שש","7":"שבע","8":"שמונה","9":"תשע"}
            whole=m.group(1)
            fraction=m.group(2)
            num=whole+(" נקודה "+" ".join(digits[d] for d in fraction) if fraction else "")
            return num+" אחוז"
        text=re.sub(r"(\\d+)(?:\\.(\\d+))?\\s*%",say_percent,text)
        text=re.sub(r"\\b(20\\d{2})\\b",lambda m:"שנת "+m.group(1),text)
        text=text.replace("3.25", "שלוש נקודה שתיים חמש")
        text=text.replace("4.00", "ארבע")
        text=text.replace("—",", ").replace("·",", ").replace("–"," עד ")
        return re.sub(r"\\s+"," ",text).strip()
    def first_sentence(text):
        text=str(text or "").strip()
        parts=re.split(r"(?<=[.!?])\\s+",text)
        if not parts:return ""
        sentence=parts[0]
        if len(sentence)>250:
            # Prefer complete clauses over cutting at an arbitrary character.
            clauses=re.split(r"[,;:]\\s+",sentence)
            if len(clauses)>1 and len(clauses[0])>=45:
                sentence=clauses[0].rstrip(" .")+"."
            # Otherwise preserve the full sentence; speech chunking below
            # will handle the model's short-utterance limit.
        return speaking(sentence)
    blocks=["בוקר טוב. הנה עיקרי סקירת השווקים להיום."]
    intros=["נתחיל בתמונה הכלכלית בעולם.",
            "ועכשיו, מה קורה עם הריביות והבנקים המרכזיים?",
            "מכאן נעבור לשוק המניות ולאנרגיה.",
            "ולסיום תמונת המאקרו, נתמקד בישראל."]
    for i,section in enumerate(data.get("sections",[])[:4]):
        points=section.get("bullets") or [section.get("text","")]
        if points and points[0]:
            blocks.extend((intros[i],first_sentence(points[0])))
    advisor=data.get("advisor",[])[:3]
    if advisor:
        blocks.append("ועכשיו, שלוש נקודות שאפשר להעלות בשיחה עם לקוחות.")
        for intro,item in zip(("הנקודה הראשונה.", "הנקודה השנייה.", "הנקודה השלישית."),advisor):
            blocks.append(intro)
            blocks.append(speaking(item.get("title",""))+".")
            blocks.append(first_sentence(item.get("insight","")))
    blocks.append("עד כאן סקירת השווקים. המשך יום נעים.")
    blocks=[x for x in blocks if x]
    from huggingface_hub import snapshot_download
    import numpy as np
    import soundfile as sf
    from blue_onnx import BlueTTS
    print("Downloading Hebrew voice models",flush=True)
    model_dir=snapshot_download(repo_id="notmax123/BlueTTS2.5-onnx",local_dir="/tmp/bluetts-model")
    print("Model downloaded",flush=True)
    # The official model bundle includes voice presets; use those instead of
    # downloading a potentially renamed file from a separate repository.
    voice_files=sorted(Path(model_dir).glob("voices/*.json"))
    voice_file=next((str(p) for p in voice_files if p.stem.lower()=="libri_female_6147"),None)
    if not voice_file and voice_files:
        voice_file=str(voice_files[0])
    if not voice_file:
        raise FileNotFoundError("No bundled voice preset found under voices/*.json")
    print("Loading voice:",Path(voice_file).name,flush=True)
    # Pin the actual Hebrew G2P model locally. The library's default downloader
    # requests datastore.json, which no longer exists in the model repository.
    from huggingface_hub import hf_hub_download
    renikud_model=hf_hub_download(repo_id="notmax123/RenikudPlus",filename="model.onnx")
    print("Hebrew phonemization model ready",flush=True)
    tts=BlueTTS(onnx_dir=model_dir,style_json=voice_file,renikud_path=renikud_model)
    audio=[]
    rate=None
    def split_short(text, limit=120):
        import re
        for sentence in re.split(r"(?<=[.!?])\s+",text):
            current=""
            for word in sentence.split():
                if current and len(current)+len(word)+1>limit:
                    yield current
                    current=""
                current=(current+" "+word).strip()
            if current:
                yield current
    for idx,paragraph in enumerate(blocks):
        print("Synthesizing block",idx+1,"of",len(blocks),flush=True)
        for phrase in split_short(paragraph):
            samples,sr=tts.synthesize(phrase,lang="he")
            rate=sr
            audio.append(np.asarray(samples,dtype=np.float32))
            audio.append(np.zeros(int(sr*0.55),dtype=np.float32))
    Path("audio").mkdir(exist_ok=True)
    wav="/tmp/daily-brief.wav"
    sf.write(wav,np.concatenate(audio),rate)
    import imageio_ffmpeg
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),"-hide_banner","-loglevel","error","-y","-i",wav,"-ac","1","-b:a","64k","audio/morning-brief.mp3"],check=True)
    manifest={"date":today,"status":"ok","file":"audio/morning-brief.mp3","engine":"BlueTTS open source","voice":Path(voice_file).stem,"generated_at":datetime.now(ZoneInfo("Asia/Jerusalem")).isoformat()}
    Path("daily_audio.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")
    print("Audio ready:",Path(manifest["file"]).stat().st_size,"bytes",flush=True)

if __name__=="__main__":
    main()
