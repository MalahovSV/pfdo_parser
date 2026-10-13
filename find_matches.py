"""
Сопоставляет ГТО-учеников (gto_students.json) со списком школы (pupils.csv).

Результат — gto_matches.csv со всеми полями обоих источников.

Запуск:
    python find_matches.py
    from find_matches import run; run()
"""

import csv
import json
import re
from pathlib import Path


GTO_JSON = "gto_students.json"
PUPILS_CSV = "pupils.csv"
OUTPUT_CSV = "gto_matches.csv"


# ---------- УТИЛИТЫ ----------

def norm(s: str) -> str:
    if not s:
        return ""
    s = s.strip().lower().replace("ё", "е")
    return re.sub(r'\s+', ' ', s)


def fio_key(fio: str) -> str:
    s = norm(fio)
    return re.sub(r'[^а-яa-z ]', '', s)


# ---------- ЧТЕНИЕ ----------

def load_pupils(csv_path: str):
    rows = None
    for enc in ("utf-8-sig", "cp1251", "utf-8"):
        try:
            with open(csv_path, "r", encoding=enc, newline="") as f:
                rows = list(csv.reader(f, delimiter=";"))
            print(f"CSV прочитан в кодировке {enc}, строк: {len(rows)}")
            break
        except UnicodeDecodeError:
            continue
    if rows is None:
        raise RuntimeError("Не удалось определить кодировку CSV")

    pupils = []
    for row in rows:
        if not row or len(row) < 5:
            continue
        if row[0].strip().lower() in ("№", "n", "number", "id"):
            continue
        try:
            klass = row[1].strip()
            last = row[2].strip()
            first = row[3].strip()
            middle = row[4].strip()
        except IndexError:
            continue
        birthday = row[5].strip() if len(row) > 5 else ""
        pupils.append({
            "class": klass,
            "fio": f"{last} {first} {middle}".strip(),
            "birthday": birthday,
        })
    return pupils


# ---------- СОПОСТАВЛЕНИЕ ----------

def match(gto_path=GTO_JSON, pupils_path=PUPILS_CSV, out_path=OUTPUT_CSV):
    with open(gto_path, "r", encoding="utf-8") as f:
        gto = json.load(f)
    print(f"ГТО-учеников из JSON: {len(gto)}")

    pupils = load_pupils(pupils_path)
    print(f"Учеников из CSV: {len(pupils)}")

    by_fio = {}
    for p in pupils:
        by_fio.setdefault(fio_key(p["fio"]), p)

    matches = []
    for g in gto:
        key = fio_key(g["fio"])
        p = by_fio.get(key)
        if not p:
            continue
        matches.append({
            "fio": g["fio"],
            "class": p["class"],
            "birthday": p["birthday"],
            "number": g["number"],
            "program": g["program"],
            "group": g["group"],
            "date_start": g["date_start"],
            "date_stop": g["date_stop"],
        })

    print(f"Совпадений найдено: {len(matches)}")

    with open(out_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "fio", "class", "birthday", "number",
                "program", "group", "date_start", "date_stop",
            ],
            delimiter=";",
        )
        writer.writeheader()
        writer.writerows(matches)

    print(f"Результат сохранён в {out_path}")
    return matches


def run():
    return match()


if __name__ == "__main__":
    run()