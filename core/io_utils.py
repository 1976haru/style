from pathlib import Path
import json

def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))

def read_text(path):
    return Path(path).read_text(encoding="utf-8-sig", errors="replace")

def write_text(path,text):
    Path(path).write_text(text, encoding="utf-8")

def write_json(path,obj):
    Path(path).write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding="utf-8")
