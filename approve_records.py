"""
Одобрение (активация) зачислений через API navigator.edu22.info.

Активация:
    PATCH /v2/contracts/{contract_id}/activate
    body: {"date": "00.00.0000", "fund_type": 2}
    ответ: {"data": [], "result_code": "FLSCS", "result_message": "Полный успех"}

Источник: pending.csv (список «Ожидающие подтверждения», полученный fetch_pending.py)

Использование:
    python approve_records.py                        # dry-run
    python approve_records.py --limit 1 --commit     # 1
    python approve_records.py --limit 5 --commit     # 5
    python approve_records.py --commit               # все
"""

import argparse
import csv
import time
from datetime import datetime
from pathlib import Path

from auth import login_with_selenium


API_URL = "https://api-navigator.edu22.info/v2/contracts/{contract_id}/activate"

SOURCE_CSV = "pending.csv"
LOG_CSV = "approve_log.csv"

FUND_TYPE = 2
ACTIVATION_DATE = "00.00.0000"
PAUSE = 0.3


# ---------- ЧТЕНИЕ ИСТОЧНИКА ----------

def load_pending(source=SOURCE_CSV):
    path = Path(source)
    if not path.exists():
        raise FileNotFoundError(
            f"Не найден {source}. Сначала запустите fetch_pending.py"
        )

    with path.open(encoding="utf-8-sig") as f:
        reader = csv.DictReader(f, delimiter=";")
        rows = list(reader)

    result = []
    for r in rows:
        cid = (r.get("contract_id") or "").strip()
        if not cid:
            continue
        result.append({
            "contract_id": cid,
            "number": r.get("number", ""),
            "fio": r.get("fio", ""),
            "group": r.get("group", ""),
        })
    return result


# ---------- АКТИВАЦИЯ ----------

def activate_contract(session, contract_id):
    url = API_URL.format(contract_id=contract_id)
    payload = {
        "date": ACTIVATION_DATE,
        "fund_type": FUND_TYPE,
    }
    resp = session.patch(url, json=payload, timeout=30)
    if resp.status_code >= 400:
        raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:300]}")

    try:
        data = resp.json()
    except ValueError:
        return "OK"

    code = data.get("result_code", "")
    if code and code != "FLSCS":
        raise RuntimeError(f"result_code={code}, msg={data.get('result_message')}")
    return code or "OK"


# ---------- ЯДРО ----------

def run(commit=False, limit=None, source=SOURCE_CSV):
    entries = load_pending(source)
    print(f"Из {source} загружено: {len(entries)}")

    if not entries:
        print("⚠ Нечего активировать.")
        return []

    if limit:
        entries = entries[:limit]
        print(f"Ограничение: {len(entries)}")

    # DRY-RUN
    if not commit:
        print("\n[DRY-RUN] Активация НЕ выполняется. Первые 20:\n")
        for i, e in enumerate(entries[:20], 1):
            print(f"  {i:>3}. id={e['contract_id']:<12} {e['fio']}  ({e['group']})")
        if len(entries) > 20:
            print(f"  ... и ещё {len(entries) - 20}")
        print("\nЧтобы активировать реально: --commit")
        return entries

    # COMMIT
    print("\nАвторизация через Selenium...")
    session = login_with_selenium()

    print(f"\nАктивируем ({len(entries)} шт.)...\n")
    log_path = Path(LOG_CSV)
    with log_path.open("w", encoding="utf-8-sig", newline="") as logf:
        writer = csv.writer(logf, delimiter=";")
        writer.writerow([
            "timestamp", "contract_id", "number", "fio", "group",
            "result_code", "status", "error",
        ])
        for i, e in enumerate(entries, 1):
            ts = datetime.now().isoformat(timespec="seconds")
            try:
                code = activate_contract(session, e["contract_id"])
                print(f"[{i:>3}/{len(entries)}] OK  id={e['contract_id']:<12} {e['fio']}")
                writer.writerow([ts, e["contract_id"], e["number"], e["fio"],
                                 e["group"], code, "OK", ""])
            except Exception as err:
                print(f"[{i:>3}/{len(entries)}] ERR id={e['contract_id']} {e['fio']}: {err}")
                writer.writerow([ts, e["contract_id"], e["number"], e["fio"],
                                 e["group"], "", "ERROR", str(err)])
            time.sleep(PAUSE)

    print(f"\nГотово. Лог: {log_path}")
    return entries


# ---------- CLI ----------

def main_cli():
    parser = argparse.ArgumentParser(description="Активация договоров")
    parser.add_argument("--commit", action="store_true",
                        help="Реально активировать (без флага — dry-run).")
    parser.add_argument("--limit", type=int, default=None,
                        help="Не более N записей.")
    parser.add_argument("--source", default=SOURCE_CSV,
                        help=f"Источник (по умолчанию {SOURCE_CSV})")
    args = parser.parse_args()
    run(commit=args.commit, limit=args.limit, source=args.source)


if __name__ == "__main__":
    main_cli()