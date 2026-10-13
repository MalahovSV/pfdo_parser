"""
Парсер архивных зачислений на программу ГТО с navigator.edu22.info.

Что делает:
    1. Авторизуется через auth.py.
    2. Выгружает все зачисления со статусом 60 («Расторгнутые/Архив»).
    3. Фильтрует по программе "ГТО. Быстрее".
    4. Сохраняет результат в gto_students.json.

Запуск напрямую:
    python parser.py

Запуск из меню:
    from parser import run; run()
"""

import json
import re
import time
from pathlib import Path

from auth import login_with_selenium


# ---------- НАСТРОЙКИ ----------

API_URL = "https://api-navigator.edu22.info/v3/record-mark/record-mark"
OUTPUT_JSON = "gto_students.json"
PROGRAM_KEYWORD = "ГТО. Быстрее"
PER_PAGE = 100
PAUSE = 0.2

SEARCH_PARAMS = {
    "search[fund_type][]": [1, 2, 3],
    "search[status]": 60,          # 60 = «Расторгнутые/Архив»
    "expand": "certificate_brief,program,group",
    "sort": "-created_at",
}


# ---------- УТИЛИТЫ ----------

def normalize(s: str) -> str:
    """Схлопывает пробелы и приводит к нижнему регистру."""
    return re.sub(r'\s+', ' ', s or "").strip().lower()


def extract_fio(cb: dict) -> str:
    """Из certificate_brief собирает 'Фамилия Имя Отчество'."""
    if not cb:
        return ""
    return " ".join(filter(None, [
        cb.get("soname", ""),
        cb.get("name", ""),
        cb.get("phname", ""),
    ])).strip()


# ---------- ВЫГРУЗКА ЧЕРЕЗ API ----------

def fetch_all_records(session):
    """Постранично выгружает все записи со статусом 60."""
    all_items = []
    page = 1
    total_pages = None

    while True:
        params = dict(SEARCH_PARAMS)
        params["page"] = page
        params["per-page"] = PER_PAGE

        resp = session.get(API_URL, params=params, timeout=30)
        if resp.status_code == 401:
            raise RuntimeError("401 Unauthorized — токен не подошёл")
        resp.raise_for_status()

        payload = resp.json()
        items = payload.get("data", [])
        all_items.extend(items)

        if total_pages is None:
            total_pages = int(resp.headers.get("X-Pagination-Page-Count", 0) or 0)
            total_count = resp.headers.get("X-Pagination-Total-Count", "?")
            print(f"Всего записей: {total_count}, страниц: {total_pages}")

        print(f"  страница {page}/{total_pages}: получено {len(items)}")

        if not items or page >= total_pages:
            break
        page += 1
        time.sleep(PAUSE)

    return all_items


# ---------- ФИЛЬТРАЦИЯ ----------

def filter_by_program(items, keyword: str):
    """Возвращает список учеников, у которых программа содержит keyword."""
    kw = normalize(keyword)
    result = []
    for item in items:
        program = (item.get("program") or {}).get("name", "")
        if kw not in normalize(program):
            continue

        cb = item.get("certificate_brief") or {}
        group = item.get("group") or {}

        result.append({
            "fio": extract_fio(cb),
            "number": cb.get("number"),
            "program": program,
            "group": group.get("name"),
            "group_id": group.get("id"),
            "date_start": item.get("date_start"),
            "date_stop": item.get("date_stop"),
        })
    return result


# ---------- ТОЧКА ВХОДА ----------

def run():
    """Полный цикл: авторизация → выгрузка → фильтр → сохранение."""
    print("Авторизация...")
    session = login_with_selenium()

    print("\nВыгружаем все зачисления со статусом 60...")
    items = fetch_all_records(session)
    print(f"\nВсего записей: {len(items)}")

    print(f"\nФильтруем по программе: {PROGRAM_KEYWORD!r}")
    gto = filter_by_program(items, PROGRAM_KEYWORD)
    print(f"Найдено ГТО-учеников: {len(gto)}")

    out_path = Path(OUTPUT_JSON)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(gto, f, ensure_ascii=False, indent=2)
    print(f"\nРезультат сохранён в {out_path}")

    print("\nПервые 10 записей:")
    for row in gto[:10]:
        print(f"  {row['fio']:<40} {row['number']}  {row['group']}")

    return gto


if __name__ == "__main__":
    run()