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
