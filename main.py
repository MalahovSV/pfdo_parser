"""
Точка входа проекта pfdo-parser.

Меню:
    1 — Выгрузка учеников (парсинг → gto_students.json)
    2 — Пересечение с pupils.csv (→ gto_matches.csv)
    3 — Проверка плана зачисления (dry-run)
    4 — Создание записей (реально)
    0 — Выход

Запуск:
    python main.py
"""

import sys
import time


MENU = """
========================================
  pfdo-parser
========================================
  1. Выгрузка учеников
     (парсинг ГТО-зачислений → gto_students.json)

  2. Пересечение с pupils.csv
     (→ gto_matches.csv)

  3. Проверка плана зачисления (dry-run)
     (только показать, что будет создано)

  4. Создание записей
     (реально создать договоры через API)

  0. Выход
========================================
"""


def pause():
    input("\nНажмите Enter, чтобы вернуться в меню...")


def action_parse():
    print("\n>>> Выгрузка учеников\n")
    from parser import run
    result = run()
    print(f"\n✓ Готово. Получено {len(result)} записей.")


def action_match():
    print("\n>>> Пересечение с pupils.csv\n")
    from find_matches import run
    result = run()
    print(f"\n✓ Готово. Совпадений: {len(result)}")


def action_plan():
    print("\n>>> Проверка плана (dry-run)\n")
    from create_records import run
    run(commit=False)


def action_create():
    print("\n>>> Создание записей\n")
    print("⚠️  ВНИМАНИЕ: будут реально созданы договоры через API.")
    print("   Убедитесь, что вы сначала проверили план (пункт 3).")
    answer = input("\nПродолжить? Введите 'да' для подтверждения: ").strip().lower()
    if answer != "да":
        print("Отменено.")
        return

    from create_records import run
    run(commit=True)


# ---------- ОСНОВНОЙ ЦИКЛ ----------

def main():
    while True:
        print(MENU)
        choice = input("Выбор: ").strip()

        if choice == "0":
            print("Выход.")
            sys.exit(0)

        elif choice == "1":
            try:
                action_parse()
            except Exception as err:
                print(f"\n✗ Ошибка: {type(err).__name__}: {err}")
            pause()

        elif choice == "2":
            try:
                action_match()
            except Exception as err:
                print(f"\n✗ Ошибка: {type(err).__name__}: {err}")
            pause()

        elif choice == "3":
            try:
                action_plan()
            except Exception as err:
                print(f"\n✗ Ошибка: {type(err).__name__}: {err}")
            pause()

        elif choice == "4":
            try:
                action_create()
            except Exception as err:
                print(f"\n✗ Ошибка: {type(err).__name__}: {err}")
            pause()

        else:
            print(f"Неизвестный пункт: {choice!r}")
            time.sleep(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nПрервано пользователем.")
        sys.exit(0)