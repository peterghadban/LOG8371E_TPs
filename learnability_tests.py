import subprocess, time, requests, sys
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# --- CONFIG ---
ROOT_URL = "http://localhost:8080/realms/master/account/"
AMC_URL = "http://localhost:8080/realms/master/account/"
USERNAME = "admin"
PASSWORD = "admin"
TIMEOUT = 90  

# --- First HTTP response ---
def first_response_test():
    print("=== Test 1: First HTTP response ===")
    start_time = time.time()
    status = None
    for i in range(TIMEOUT):
        try:
            r = requests.get(ROOT_URL, timeout=2)
            status = r.status_code
            elapsed = round(time.time() - start_time, 2)
            print(f"First response code: {status} after {elapsed}s")
            return 
        except requests.exceptions.RequestException:
            time.sleep(1)
    print(f"No response within {TIMEOUT}s")
    
# --- Selenium login test ---
def selenium_login_test():
    print("\n=== Test 2: Selenium login ===")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
    driver.set_window_size(1280, 900)

    try:
        driver.get(AMC_URL)
        wait = WebDriverWait(driver, TIMEOUT)

        # Wait for login form
        user_box = wait.until(EC.presence_of_element_located((By.ID, "username")))
        pass_box = driver.find_element(By.ID, "password")
        login_btn = driver.find_element(By.ID, "kc-login")

        # Fill login form
        user_box.clear(); user_box.send_keys(USERNAME)
        pass_box.clear(); pass_box.send_keys(PASSWORD)
        login_btn.click()

        # Wait until login button disappears 
        wait.until_not(EC.presence_of_element_located((By.ID, "kc-login")))
        wait.until(EC.url_contains("/account"))

        print("Login successful: Account Management Console loaded")
    except Exception as e:
        print(f"Login failed: {e}")
    finally:
        driver.quit()
        
# --- MAIN ---
if __name__ == "__main__":
    first_response_test()
    selenium_login_test()

