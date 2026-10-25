"""Shared plain-text narration and content fingerprint; no speech dependencies."""
import hashlib
import json

def narration_parts(data):
    parts=[]
    def add(value):
        if isinstance(value,str) and value.strip():
            parts.append(value.strip())
    add(data.get("title"))
    for section in data.get("sections",[]):
        add(section.get("heading"))
        for paragraph in section.get("bullets") or [section.get("text","")]:
            add(paragraph)
    for item in data.get("advisor",[]):
        if isinstance(item,str):
            add(item)
            continue
        for key in ("title","insight","client_impact","question"):
            add(item.get(key))
    add(data.get("takeaway"))
    return parts

def content_hash(data):
    payload=json.dumps(narration_parts(data),ensure_ascii=False,separators=(",",":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


import re

def speaking(text):
    text=str(text or "")
    english={"Alphabet":"אלפבית","Microsoft":"מיקרוסופט","Amazon":"אמזון",
             "Reuters":"רויטרס","Nasdaq":"נאסדק","AI":"בינה מלאכותית",
             "ECB":"הבנק המרכזי האירופי","CPI":"מדד המחירים לצרכן",
             "GDP":"תוצר מקומי גולמי","AP":"איי פי"}
    for source,target in english.items():
        text=re.sub(r"(?<![A-Za-z])"+re.escape(source)+r"(?![A-Za-z])",target,text)
    for source,target in (("מח״מ","משך חיים ממוצע"),("אג״ח","איגרות חוב"),
                          ("ארה״ב","ארצות הברית"),("תמ״ג","תוצר מקומי גולמי")):
        text=text.replace(source,target)
    digits={"0":"אפס","1":"אחת","2":"שתיים","3":"שלוש","4":"ארבע",
            "5":"חמש","6":"שש","7":"שבע","8":"שמונה","9":"תשע"}
    def percent(m):
        number=m.group(1)
        if m.group(2):
            number+=" נקודה "+" ".join(digits[d] for d in m.group(2))
        return number+" אחוז"
    text=re.sub(r"(\d+)(?:\.(\d+))?\s*%",percent,text)
    text=text.replace("—",", ").replace("·",", ").replace("–"," עד ")
    text=text.replace("״","").replace('"',"")
    return re.sub(r"\s+"," ",text).strip()

def split_short(text, limit=120):
    """Prefer punctuation; keep every word and number in the original order."""
    words=text.split()
    while words:
        size=0
        end=0
        preferred=0
        for i,word in enumerate(words):
            if size+len(word)+(1 if i else 0)>limit:
                break
            size+=len(word)+(1 if i else 0)
            end=i+1
            if re.search(r"[,;:!?]$|(?<!\d)\.$",word):
                preferred=end
        end=preferred or end or 1
        yield " ".join(words[:end])
        words=words[end:]
