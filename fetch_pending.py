"""
Загружает список всех зачислений в статусе «Ожидающие подтверждения» (status=10)
и сохраняет их в pending.csv: contract_id;number;fio;group;contract_status

Запуск:
    python fetch_pending.py
"""

import csv
import time
from pathlib import Path

from auth import login_with_selenium


API_URL = "https://api-navigator.edu22.info/v3/record-mark/record-mark"
OUTPUT = "pending.csv"
PER_PAGE = 100
PAUSE = 0.2

SEARCH_PARAMS = {
    "search[fund_type][]": [1, 2, 3],
    "search[status]": 10,
    "expand": "certificate_brief,program,group,contract_brief,special_information_availability",
    "sort": "-created_at",
}


def fetch_pending(session):
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
            total = resp.headers.get("X-Pagination-Total-Count", "?")
            print(f"Всего: {total}, страниц: {total_pages}")

        print(f"  страница {page}/{total_pages}: {len(items)} записей")

        if not items or page >= total_pages:
            break
        page += 1
        time.sleep(PAUSE)

    return all_items


def extract_rows(items):
    rows = []
    for it in items:
        cb = it.get("certificate_brief") or {}
        cont = it.get("contract_brief") or {}
        grp = it.get("group") or {}

        contract_id = cont.get("id")
        if not contract_id:
            continue

        fio = " ".join(filter(None, [
            cb.get("soname", ""),
            cb.get("name", ""),
            cb.get("phname", ""),
        ])).strip()

        rows.append({
            "contract_id": contract_id,
            "number": cb.get("number", ""),
            "fio": fio,
            "group": grp.get("name", ""),
            "contract_status": cont.get("status", ""),
        })
    return rows


def run():
    print("Авторизация...")
    session = login_with_selenium()

    print("Загружаем список «Ожидающие подтверждения»...")
    items = fetch_pending(session)
    print(f"\nВсего записей: {len(items)}")

    rows = extract_rows(items)
    print(f"С пригодным contract_id: {len(rows)}")

    out = Path(OUTPUT)
    with out.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["contract_id", "number", "fio", "group", "contract_status"],
            delimiter=";",
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nСохранено в {out}")

    print("\nПервые 5:")
    for row in rows[:5]:
        print(f"  {row['contract_id']:<10} {row['number']}  {row['fio']}  ({row['group']})")

    return rows


if __name__ == "__main__":
    run()