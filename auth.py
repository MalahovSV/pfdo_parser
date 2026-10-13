"""
Авторизация на navigator.edu22.info и создание requests.Session
с Bearer-токеном из localStorage.
"""
import time
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from models.Data import Data

register_data = Data("./data")

BASE_URL = "https://navigator.edu22.info"
LOGIN_URL = f"{BASE_URL}/app/signin"


def authorization(browser, timeout=15):
    """Логинится в браузере. После возврата форма логина исчезла."""
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

    wait.until(EC.invisibility_of_element_located(
        (By.CSS_SELECTOR, 'input[autocomplete="username"]')))
    time.sleep(2)   # дать Vue сохранить id_token в localStorage


def make_session(browser):
    """Возвращает requests.Session с Authorization: Bearer <id_token>."""
    session = requests.Session()

    for c in browser.get_cookies():
        session.cookies.set(c["name"], c["value"], domain=c.get("domain"))

    token = browser.execute_script("""
        return (
            localStorage.getItem('id_token') ||
            localStorage.getItem('token') ||
            localStorage.getItem('access_token') ||
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
        "Referer": f"{BASE_URL}/app/contract/create",
        "Origin": BASE_URL,
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
        ),
    })
    return session


def login_with_selenium():
    """Шорткат: запускает Chrome, логинится, возвращает готовую session."""
    from selenium.webdriver.chrome.options import Options
    options = Options()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    browser = webdriver.Chrome(options=options)
    try:
        authorization(browser)
        session = make_session(browser)
    finally:
        browser.quit()
    return session