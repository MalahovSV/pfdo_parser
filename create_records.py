"""
Создание новых договоров (зачислений) через API navigator.edu22.info.

Использование (CLI):
    python create_records.py                        # dry-run
    python create_records.py --test-one --commit    # 1 договор
    python create_records.py --limit 5 --commit     # 5 договоров
    python create_records.py --commit               # все (осторожно!)

Из меню:
    from create_records import run
    run(commit=False)                # dry-run
    run(commit=True, test_one=True)  # 1 договор
"""

import argparse
import csv
import re
import time
from collections import Counter
from datetime import datetime, date
from pathlib import Path

from auth import login_with_selenium


# ---------- НАСТРОЙКИ ----------

API_URL = "https://api-navigator.edu22.info/v2/municipal-task-contracts"

MATCHES_CSV = "gto_matches.csv"
LOG_CSV = "enroll_log.csv"

STUDENTS_PER_GROUP = 25
ENROLLMENT_YEAR = 2026

GROUPS = {
    "гто 28": 3412234,
    "гто 29": 3412235,
    "гто 30": 3412236,
    "гто 31": 3412238,
    "гто 32": 3412239,
    "гто 33": 3412241,
    "гто 34": 3412242,
    "гто 35": 3412244,
    "гто 36": 3412245,
    "гто 37": 3412246,
    "гто 38": 3412247,
    "гто 39": 3412249,
    "гто 40": 3412250,
}


# ---------- УТИЛИТЫ ----------

def parse_birthday(s: str):
    """'4.06.16' или '4.06.2016' → date."""
    s = s.strip()
    m = re.match(r'^(\d{1,2})\.(\d{1,2})\.(\d{2,4})$', s)
    if not m:
        return None
    d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
    if y < 100:
        y += 2000
    try:
        return date(y, mo, d)
    except ValueError:
        return None


def calculate_age(birthday: date, on_date: date) -> int:
    years = on_date.year - birthday.year
    if (on_date.month, on_date.day) < (birthday.month, birthday.day):
        years -= 1
    return years


def pick_start_date(group_number: int) -> str:
    """10 групп на одну дату зачисления."""
    if 1 <= group_number <= 10:
        return f"12.10.{ENROLLMENT_YEAR}"
    if 11 <= group_number <= 20:
        return f"13.10.{ENROLLMENT_YEAR}"
    if 21 <= group_number <= 30:
        return f"14.10.{ENROLLMENT_YEAR}"
    if 31 <= group_number <= 40:
        return f"15.10.{ENROLLMENT_YEAR}"
    if 41 <= group_number <= 50:
        return f"16.10.{ENROLLMENT_YEAR}"
    raise ValueError(f"Нет даты для группы {group_number}")


def load_students(path: str):
    with open(path, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f, delimiter=";"))


# ---------- ПЛАН ЗАЧИСЛЕНИЯ ----------
START_GROUP = 28   # первая свободная группа


def build_plan(students, cutoff_date: date, start_group=START_GROUP):
    seen = set()
    unique = []
    skipped_age = 0
    skipped_dup = 0
    skipped_bad = 0

    for s in students:
        num = s["number"].strip()
        if num in seen:
            skipped_dup += 1
            continue

        bday = parse_birthday(s["birthday"])
        if bday is None:
            skipped_bad += 1
            continue

        if calculate_age(bday, cutoff_date) >= 18:
            skipped_age += 1
            continue

        seen.add(num)
        unique.append(s)

    print(f"Всего в CSV: {len(students)}")
    print(f"  дубликатов:   {skipped_dup}")
    print(f"  18+:          {skipped_age}")
    print(f"  некорректных: {skipped_bad}")
    print(f"  к зачислению: {len(unique)}")

    plan = []
    for i, s in enumerate(unique):
        group_number = i // STUDENTS_PER_GROUP + start_group
        group_name = f"гто {group_number}"

        if group_name not in GROUPS:
            print(f"  ⚠ нет ID для группы {group_name} — остановка на {i} ученике")
            break

        plan.append({
            "fio": s["fio"],
            "number": s["number"].strip(),
            "group_name": group_name,
            "group_id": GROUPS[group_name],
            "start_date": pick_start_date(group_number),
        })

    return plan


# ---------- СОЗДАНИЕ ЧЕРЕЗ API ----------

def create_contract(session, certificate_number, group_id, start_date, limitless=0):
    payload = {
        "certificate_number": certificate_number,
        "group_id": group_id,
        "limitless": limitless,
        "start_education_date": start_date,
    }
    resp = session.post(API_URL, json=payload, timeout=30)
    if resp.status_code >= 400:
        raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:300]}")
    return resp.json()


def extract_contract_id(result: dict) -> str:
    data = result.get("data") or result
    if isinstance(data, dict):
        return str(
            data.get("id")
            or (data.get("contract") or {}).get("id")
            or (data.get("record_mark") or {}).get("id")
            or ""
        )
    return ""


# ---------- ЯДРО: run() ----------

def run(commit=False, test_one=False, limit=None):
    """Программный запуск. Без commit — только план."""
    cutoff = date(ENROLLMENT_YEAR, 10, 12)

    print(f"Читаем {MATCHES_CSV}")
    students = load_students(MATCHES_CSV)
    plan = build_plan(students, cutoff)

    if test_one:
        plan = plan[:1]
    elif limit:
        plan = plan[:limit]

    print(f"\nВ плане: {len(plan)} учеников")
    print("Распределение по группам:")
    for g, n in sorted(Counter(p["group_name"] for p in plan).items(),
                       key=lambda x: int(x[0].split()[1])):
        d = next(p["start_date"] for p in plan if p["group_name"] == g)
        print(f"  {g:<8} → {n:>3} чел., дата {d}")

    if not commit:
        print("\n[DRY-RUN] Договоры НЕ создаются. Первые 20 строк плана:\n")
        for i, row in enumerate(plan[:20], 1):
            print(f"  {i:>3}. {row['fio']:<40} {row['number']}  "
                  f"{row['group_name']} (id={row['group_id']})  {row['start_date']}")
        if len(plan) > 20:
            print(f"  ... и ещё {len(plan) - 20}")
        return plan

    print("\nАвторизация через Selenium...")
    session = login_with_selenium()

    print(f"\nСоздаём договоры ({len(plan)} шт.)...\n")
    log_path = Path(LOG_CSV)
    with log_path.open("w", encoding="utf-8-sig", newline="") as logf:
        writer = csv.writer(logf, delimiter=";")
        writer.writerow([
            "timestamp", "fio", "number", "group_name", "group_id",
            "start_date", "contract_id", "status", "error",
        ])
        for i, row in enumerate(plan, 1):
            ts = datetime.now().isoformat(timespec="seconds")
            try:
                result = create_contract(
                    session, row["number"], row["group_id"], row["start_date"])
                contract_id = extract_contract_id(result)
                print(f"[{i:>3}/{len(plan)}] OK  {row['fio']} → id={contract_id}")
                writer.writerow([ts, row["fio"], row["number"],
                                 row["group_name"], row["group_id"],
                                 row["start_date"], contract_id, "OK", ""])
            except Exception as err:
                print(f"[{i:>3}/{len(plan)}] ERR {row['fio']}: {err}")
                writer.writerow([ts, row["fio"], row["number"],
                                 row["group_name"], row["group_id"],
                                 row["start_date"], "", "ERROR", str(err)])
            time.sleep(0.3)

    print(f"\nГотово. Лог: {log_path}")
    return plan


# ---------- CLI ----------

def main_cli():
    parser = argparse.ArgumentParser(description="Создание договоров ГТО")
    parser.add_argument("--commit", action="store_true",
                        help="Реально создавать. Без флага — dry-run.")
    parser.add_argument("--test-one", action="store_true",
                        help="Только первого ученика.")
    parser.add_argument("--limit", type=int, default=None,
                        help="Не более N учеников.")
    args = parser.parse_args()
    run(commit=args.commit, test_one=args.test_one, limit=args.limit)


if __name__ == "__main__":
    main_cli()