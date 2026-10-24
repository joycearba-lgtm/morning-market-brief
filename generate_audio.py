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
    blocks=["בוקר טוב. הנה סקירת השווקים של הבוקר."]
    for section in data.get("sections",[])[:5]:
        blocks.append(str(section.get("heading","")).replace("—",", "))
        points=section.get("bullets") or ([section.get("text")] if section.get("text") else [])
        for point in points[:2]:
            if not isinstance(point,str): continue
            # Two human-sized sentences per topic; no raw whole-page reading.
            import re
            sentences=re.split(r"(?<=[.!?])\s+",point)
            blocks.extend(sentences[:2])
    advisor=data.get("advisor",[])[:3]
    if advisor:
        blocks.append("ועכשיו, שלוש נקודות חשובות לשיחה עם לקוחות.")
        for p in advisor:
            blocks.append(p.get("title",""))
            blocks.append(p.get("insight",""))
            blocks.append(p.get("client_impact",""))
    blocks.append("עד כאן סקירת השווקים.")
    blocks=[str(b).strip() for b in blocks if b and str(b).strip()]
    from huggingface_hub import snapshot_download
    import numpy as np
    import soundfile as sf
    from blue_onnx import BlueTTS
    model_dir=snapshot_download(repo_id="notmax123/BlueTTS2.5-onnx",local_dir="/tmp/bluetts-model")
    # The official model bundle includes voice presets; use those instead of
    # downloading a potentially renamed file from a separate repository.
    voice_files=sorted(Path(model_dir).glob("voices/*.json"))
    voice_file=next((str(p) for p in voice_files if p.stem.lower()=="noa"),None)
    if not voice_file and voice_files:
        voice_file=str(voice_files[0])
    if not voice_file:
        raise FileNotFoundError("No bundled voice preset found under voices/*.json")
    tts=BlueTTS(onnx_dir=model_dir,style_json=voice_file)
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
    for paragraph in blocks:
        for phrase in split_short(paragraph):
            samples,sr=tts.synthesize(phrase,lang="he")
            rate=sr
            audio.append(np.asarray(samples,dtype=np.float32))
            audio.append(np.zeros(int(sr*0.32),dtype=np.float32))
    Path("audio").mkdir(exist_ok=True)
    wav="/tmp/daily-brief.wav"
    sf.write(wav,np.concatenate(audio),rate)
    subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-y","-i",wav,"-ac","1","-b:a","64k","audio/morning-brief.mp3"],check=True)
    manifest={"date":today,"status":"ok","file":"audio/morning-brief.mp3","engine":"BlueTTS open source","voice":Path(voice_file).stem,"generated_at":datetime.now(ZoneInfo("Asia/Jerusalem")).isoformat()}
    Path("daily_audio.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")
    print("Audio ready:",Path(manifest["file"]).stat().st_size,"bytes")

if __name__=="__main__":
    main()
