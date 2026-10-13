import re
import time
import json
import requests

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.options import Options

from models.Data import Data


register_data = Data("./data")

BASE_URL = "https://navigator.edu22.info"
LOGIN_URL = f"{BASE_URL}/app/signin"
API_URL = "https://api-navigator.edu22.info/v3/record-mark/record-mark"


# -------------------- Авторизация --------------------

def authorization(browser, timeout=15):
    wait = WebDriverWait(browser, timeout)
    browser.get(LOGIN_URL)

    login_input = wait.until(EC.element_to_be_clickable(
        (By.CSS_SELECTOR, 'input[autocomplete="username"]')))
    login_input.clear()
    login_input.send_keys(register_data.login)

    password_input = wait.until(EC.element_to_be_clickable(
        (By.CSS_SELECTOR, 'input[type="password"]')))
    password_input.clear()
    password_input.send_keys(register_data.password)

    wait.until(EC.element_to_be_clickable((
        By.XPATH, '//button[.//span[normalize-space(text())="Войти"]]'
    ))).click()

    # Ждём, пока форма логина исчезнет — значит, вход прошёл
    wait.until(EC.invisibility_of_element_located(
        (By.CSS_SELECTOR, 'input[autocomplete="username"]')))

    # Дать приложению сохранить токен в localStorage
    time.sleep(2)


# -------------------- Сессия requests с токеном --------------------

def make_session(browser):
    session = requests.Session()

    # Переносим cookies
    for c in browser.get_cookies():
        session.cookies.set(c["name"], c["value"], domain=c.get("domain"))

    # Достаём JWT из localStorage (ключ — id_token)
    token = browser.execute_script("""
        return (
            localStorage.getItem('id_token') ||
            localStorage.getItem('token') ||
            localStorage.getItem('access_token') ||
            localStorage.getItem('auth_token') ||
            localStorage.getItem('jwt') ||
            null
        );
    """)
    if not token:
        raise RuntimeError("Токен не найден в localStorage")

    print(f"Токен найден (длина {len(token)})")

    session.headers.update({
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        "Authorization": f"Bearer {token}",
        "Referer": f"{BASE_URL}/app/contract/list",
        "Origin": BASE_URL,
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
        ),
    })
    return session


# -------------------- Выгрузка через API --------------------

def fetch_all(session, per_page=100):
    """Забирает все записи постранично."""
    all_items = []
    page = 1
    total_pages = None

    while True:
        params = {
            "page": page,
            "per-page": per_page,
            "search[fund_type][]": [1, 2, 3],
            "search[status]": 60,   # 60 = «Расторгнутые/Архив»
            "expand": "certificate_brief,program,group",
            "sort": "-created_at",
        }
        resp = session.get(API_URL, params=params, timeout=30)
        if resp.status_code == 401:
            raise RuntimeError("401 Unauthorized — токен не подошёл")
        resp.raise_for_status()
        payload = resp.json()
        items = payload.get("data", [])
        all_items.extend(items)

        if total_pages is None:
            total_pages = int(resp.headers.get("X-Pagination-Page-Count", 0))
            total_count = resp.headers.get("X-Pagination-Total-Count")
            print(f"Всего записей: {total_count}, страниц: {total_pages}")

        print(f"  страница {page}/{total_pages}: получено {len(items)}")

        if page >= total_pages or not items:
            break
        page += 1
        time.sleep(0.2)   # пауза между запросами, чтобы не злить API

    return all_items


# -------------------- Фильтрация --------------------

def normalize(s: str) -> str:
    """Схлопывает пробелы и приводит к нижнему регистру."""
    return re.sub(r'\s+', ' ', s).strip().lower()


def extract_fio(cb: dict) -> str:
    return " ".join(filter(None, [
        cb.get("soname", ""),
        cb.get("name", ""),
        cb.get("phname", ""),
    ]))


def filter_by_program(items, keyword="ГТО. Быстрее"):
    kw = normalize(keyword)
    result = []
    for item in items:
        program = item.get("program", {}).get("name", "")
        if kw in normalize(program):
            cb = item.get("certificate_brief", {}) or {}
            result.append({
                "fio": extract_fio(cb),
                "number": cb.get("number"),
                "program": program,
                "group": (item.get("group") or {}).get("name"),
                "date_start": item.get("date_start"),
                "date_stop": item.get("date_stop"),
            })
    return result


# -------------------- Точка входа --------------------

if __name__ == "__main__":
    browser = None
    try:
        options = Options()
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        # options.add_argument("--headless=new")   # раскомментируйте на сервере

        browser = webdriver.Chrome(options=options)
        print("Авторизация...")
        authorization(browser)

        print("Готовим сессию requests...")
        session = make_session(browser)

        print("Выгружаем записи через API...")
        items = fetch_all(session, per_page=100)

        print(f"\nВсего записей: {len(items)}")
        gto = filter_by_program(items, "ГТО. Быстрее")
        print(f"Найдено ГТО-учеников: {len(gto)}\n")

        for row in gto:
            print(f"  {row['fio']:<40} {row['number']}  {row['program']}")

        with open("gto_students.json", "w", encoding="utf-8") as f:
            json.dump(gto, f, ensure_ascii=False, indent=2)
        print("\nРезультат сохранён в gto_students.json")

    except Exception as err:
        print(f"Ошибка: {type(err).__name__}: {err}")
    finally:
        if browser is not None:
            browser.quit()