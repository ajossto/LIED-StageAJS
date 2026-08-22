"""Extrait les annotations « note » (/Subtype/Text) d'un PDF via `mutool show grep`.

Sortie : une entrée par note, avec le numéro de page (ordre du document) et le
texte décodé (UTF-16BE hexadécimal tel qu'écrit par les visionneuses Qt/poppler).
"""

import re
import subprocess
import sys
from pathlib import Path

pdf = Path(sys.argv[1])
dump = subprocess.run(
    ["mutool", "show", str(pdf), "grep"],
    capture_output=True, text=True, timeout=600,
).stdout

# 1. numéro d'objet de chaque page, dans l'ordre du document
pages = subprocess.run(
    ["mutool", "show", str(pdf), "pages"], capture_output=True, text=True, timeout=600
).stdout
page_of_obj = {}
for match in re.finditer(r"page (\d+) = (\d+) 0 R", pages):
    page_of_obj[int(match.group(2))] = int(match.group(1))


def decode(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith("<") and raw.endswith(">"):
        data = bytes.fromhex(raw[1:-1])
        if data[:2] == b"\xfe\xff":
            return data[2:].decode("utf-16-be", errors="replace")
        return data.decode("latin-1", errors="replace")
    if raw.startswith("(") and raw.endswith(")"):
        return raw[1:-1]
    return raw


notes = []
for line in dump.splitlines():
    if "/Subtype/Text" not in line:
        continue
    num = int(line.split(" ", 1)[0])
    contents = re.search(r"/Contents\s*(<[0-9A-Fa-f]*>|\([^)]*\))", line)
    parent = re.search(r"/P (\d+) 0 R", line)
    rect = re.search(r"/Rect\[([^\]]*)\]", line)
    stamp = re.search(r"/M\(([^)]*)\)", line)
    page = page_of_obj.get(int(parent.group(1))) if parent else None
    y = float(rect.group(1).split()[3]) if rect else 0.0
    notes.append({
        "obj": num,
        "page": page or 0,
        "y": y,
        "date": stamp.group(1) if stamp else "",
        "text": decode(contents.group(1)) if contents else "",
    })

notes.sort(key=lambda n: (n["page"], -n["y"]))
print(f"# {pdf.name} — {len(notes)} notes\n")
for index, note in enumerate(notes, 1):
    print(f"## [{index}] page {note['page']}  (y={note['y']:.0f}, obj {note['obj']})")
    print(note["text"])
    print()
