import psycopg2
import os
import time

from selenium import webdriver
from webdriver_manager.firefox import GeckoDriverManager

# from selenium.webdriver.chrome.service import Service
# from selenium.webdriver.chrome.options import Options
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service

from selenium.webdriver.common.by import By
from selenium.webdriver.common.alert import Alert
from selenium.common.exceptions import NoAlertPresentException
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def save_screenshot(driver, item_id, screenshot_directory, type):
    screenshot_filename = f"{item_id}_{type}.png"
    screenshot_path = os.path.join(screenshot_directory, screenshot_filename)

    # Try to save a screenshot
    try:
        driver.save_screenshot(screenshot_path)
    except Exception as e:
        print(f"Failed to save screenshot for item ID {item_id}: {str(e)}")
        screenshot_path = None  # If saving fails, set screenshot_path to None

    return screenshot_path


def extract_iframe_content(driver):
    iframe_text = ""
    try:
        WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located((By.TAG_NAME, "iframe")))
        iframes = driver.find_elements(By.TAG_NAME, "iframe")
    except TimeoutException:
        print("Timed out waiting for iframes to be present.")
        iframes = []

    for iframe in iframes:
        try:
            WebDriverWait(driver, 10).until(EC.frame_to_be_available_and_switch_to_it(iframe))
            iframe_body_text = driver.find_element(By.TAG_NAME, "body").text
            iframe_text += f"\n{iframe_body_text}"
            driver.switch_to.default_content()
        except Exception as e:
            print(f"Error while processing iframe: {e}")
            driver.switch_to.default_content()

    return iframe_text


def get_main_page_text(driver, attempt=1, max_attempts=5):
    entire_page_text = ""
    try:
        WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        entire_page_text = driver.execute_script("return document.documentElement.innerText").strip()
    except TimeoutException:
        return entire_page_text

    if not entire_page_text and attempt < max_attempts:
        print(f"No text found on main page, waiting and retrying... Attempt {attempt} of {max_attempts}")
        time.sleep(10)  # Wait for 10 seconds before retrying
        return get_main_page_text(driver, attempt + 1, max_attempts)
    else:
        return entire_page_text


def crawl_batch(conn, start_id, end_id):
    cursor = conn.cursor()

    cursor.execute("SELECT id, origin FROM global_100k WHERE is_crawled=0 AND id >= %s AND id < %s",
                   (start_id, end_id))
    urls_data = cursor.fetchall()

    options = Options()
    options.add_argument("--headless")  # Run in headless mode
    options.set_preference("extensions.webcompat.perform_ua_overrides", False)
    options.set_preference("extensions.webcompat.perform_injections", False)

    # Initialize WebDriver service
    webdriver_service = Service(GeckoDriverManager().install())
    driver = webdriver.Firefox(service=webdriver_service, options=options)
    driver.set_page_load_timeout(60)

    screenshot_directory = "screenshots_empty"
    os.makedirs(screenshot_directory, exist_ok=True)  # Create the directory if it does not exist

    for row in urls_data:
        item_id, url = row
        screenshot_path, is_error, full_text  = None, 0, ""

        driver.get("about:blank")
        try:
            try:
                print(f"Crawling: {url}")
                driver.get(url)
                driver.implicitly_wait(10)
            except TimeoutException:
                print(f"Page load timed out but continuing with available content for URL: {url}")

            alert_text = ""
            try:
                alert = Alert(driver)
                alert_text = "\n" + alert.text
                alert.accept()
                time.sleep(1)  # Adjust sleep time as necessary
            except NoAlertPresentException:
                pass

            entire_page_text = get_main_page_text(driver)

            iframe_text = extract_iframe_content(driver)
            # iframes = driver.find_elements(By.TAG_NAME, "iframe")
            # for iframe in iframes:
            #     driver.switch_to.frame(iframe)
            #     iframe_text += "\n" + driver.find_element(By.TAG_NAME, "body").text
            #     driver.switch_to.default_content()

            full_text = ' '.join([entire_page_text, alert_text, iframe_text])

            if not full_text.strip():
                full_text = "empty"
                screenshot_path = save_screenshot(driver, item_id, screenshot_directory, "empty")

        except Exception as e:
            is_error = 1
            full_text = str(e)  # Capture the error message as the full text
            screenshot_path = save_screenshot(driver, item_id, screenshot_directory, "error")

        print("text", full_text)

        update_query = """
                UPDATE global_100k 
                SET text = %s, is_crawled = 1, is_error = %s, screenshot_path = %s 
                WHERE id = %s
                """
        cursor.execute(update_query, (full_text, is_error, screenshot_path if screenshot_path else None, item_id))
        conn.commit()

    driver.quit()
    conn.commit()


def crawl_all():
    conn = psycopg2.connect("dbname='unsupported_crawl' user='uc_test'",port=5434)

    cursor = conn.cursor()
    cursor.execute("SELECT MIN(id), MAX(id) FROM global_100k WHERE is_crawled = 0")
    range_result = cursor.fetchone()

    if range_result:
        min_id, max_id = range_result
        chunk_size = 500

        for start_id in range(min_id, max_id + 1, chunk_size):
            end_id = start_id + chunk_size
            print(f"Crawling from ID {start_id} to {end_id}")
            crawl_batch(conn, start_id, end_id)

    cursor.close()
    conn.close()

def crawl_empty():
    conn = psycopg2.connect("dbname='unsupported_crawl' user='uc_test'", port=5434 )

    cursor = conn.cursor()
    cursor.execute("SELECT MIN(id), MAX(id) FROM global_100k WHERE is_crawled=1 and text='empty'")
    range_result = cursor.fetchone()

    if range_result:
        min_id, max_id = range_result
        chunk_size = 100

        for start_id in range(min_id, max_id + 1, chunk_size):
            end_id = start_id + chunk_size
            print(f"Crawling from ID {start_id} to {end_id}")
            crawl_batch(conn, start_id, end_id)

    cursor.close()
    conn.close()

if __name__ == "__main__":
    crawl_all()



