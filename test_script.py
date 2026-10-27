import csv
import json
import os
import sys
import time
from decimal import Decimal, InvalidOperation
from pathlib import Path

from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

APP_URL = os.getenv("APP_URL", "http://localhost/SWE30009_Project/index.php")
HEADLESS = os.getenv("HEADLESS", "0") == "1"
BASE_DIR = Path(__file__).resolve().parent
CSV_FILE = BASE_DIR / "test_cases.csv"
SHOT_DIR = BASE_DIR / "screenshots"
RESULTS_FILE = BASE_DIR / "results.json"

MODEL_FIELDS = ["gpt5", "gpt5mini", "sonnet", "haiku",
                "geminipro", "geminiflash", "llama", "mistral"]

#Step (a): read the test cases from the CSV file
def read_test_cases():
    with open(CSV_FILE, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

#Step (b): launch a Chrome browser instance (Selenium Manager fetches the driver)
def create_driver():
    options = Options()
    if HEADLESS:
        options.add_argument("--headless=new")
    options.add_argument("--window-size=1280,1600")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    return webdriver.Chrome(options=options)

#Convert 'Rm1,060.00' to Decimal('1060.00')
def money_to_decimal(text):
    return Decimal(text.replace("RM", "").replace(",", "").strip())

#Steps (c)-(e): load page, enter data, click Calculate, compare result.
def run_test_case(driver, wait, test):
    driver.get(APP_URL)                                               # (c)

    for field in MODEL_FIELDS:                                        # (d)
        value = (test.get(field) or "").strip()
        if value:
            box = driver.find_element(By.ID, f"usage_{field}")
            box.clear()
            box.send_keys(value)

    batch_box = driver.find_element(By.ID, "batch")
    if test["batch"].strip().lower() == "yes" and not batch_box.is_selected():
        driver.find_element(By.CSS_SELECTOR, "label.switch").click()
    driver.find_element(By.ID, "calculate").click()

    # Wait until the page reloads with either a total or an error box.
    wait.until(lambda d: d.find_elements(By.ID, "total") or d.find_elements(By.ID, "error-box"))

    expected_error = (test.get("expected_error") or "").strip()
    expected_total = (test.get("expected_total") or "").strip()

    if driver.find_elements(By.ID, "error-box"):
        actual = driver.find_element(By.ID, "error-box").text
        passed = bool(expected_error) and expected_error.lower() in actual.lower()
        expected = f"error containing '{expected_error}'" if expected_error else expected_total
        target = driver.find_element(By.ID, "error-box")
    else:
        actual = driver.find_element(By.ID, "total").text
        target = driver.find_element(By.ID, "total")
        try:
            passed = (not expected_error) and money_to_decimal(actual) == Decimal(expected_total)
        except InvalidOperation:
            passed = False
        expected = expected_total or f"error containing '{expected_error}'"

    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", target)
    return passed, expected, actual


def main():
    test_cases = read_test_cases()
    SHOT_DIR.mkdir(exist_ok=True)
    results = []
    driver = create_driver()
    wait = WebDriverWait(driver, 10)

    print(f"Running {len(test_cases)} test cases against {APP_URL}\n" + "-" * 70)
    try:
        for test in test_cases:                                         # (g) repeat
            start = time.perf_counter()
            try:
                passed, expected, actual = run_test_case(driver, wait, test)
                status = "PASS" if passed else "FAIL"
            except (TimeoutException, WebDriverException) as exc:
                status, expected, actual = "ERROR", "-", f"{type(exc).__name__}: {str(exc).splitlines()[0]}"
            duration = round(time.perf_counter() - start, 2)

            shot = SHOT_DIR / f"{test['test_id']}_{status}.png"
            try:
                driver.save_screenshot(str(shot))                     # evidence of final bill
            except WebDriverException:
                pass

            # (f) display pass/fail status
            print(f"[{status}] {test['test_id']} - {test['description']}")
            print(f"        expected: {expected} | actual: {actual.replace(chr(10), ' ')} | {duration}s")
            results.append({"test_id": test["test_id"], "description": test["description"],
                            "status": status, "expected": expected,
                            "actual": actual, "duration_s": duration, "screenshot": shot.name})
    finally:
        driver.quit()

    RESULTS_FILE.write_text(json.dumps(results, indent=2), encoding="utf-8")
    passed_n = sum(r["status"] == "PASS" for r in results)
    print("-" * 70 + f"\nSummary: {passed_n}/{len(results)} passed, "
          f"{len(results) - passed_n} failed/errored")
    sys.exit(0 if passed_n == len(results) else 1)   # non-zero exit lets CI detect failures


if __name__ == "__main__":
    main()
