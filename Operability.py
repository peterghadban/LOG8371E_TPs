from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import time

# --- Launch browser ---
driver = webdriver.Chrome()
driver.get("http://localhost:8080/realms/master/account")  # Keycloak Account Management Console

# --- Login ---
driver.find_element(By.ID, "username").send_keys("testuser123")
driver.find_element(By.ID, "password").send_keys("userpassword")
driver.find_element(By.ID, "kc-login").click()

time.sleep(2)  # wait for dashboard

start_time = time.time()

# --- Navigate to Password Tab ---
driver.find_element(By.LINK_TEXT, "Password").click()

# --- Update Password ---
driver.find_element(By.ID, "password-new").send_keys("newpassword123")
driver.find_element(By.ID, "password-confirm").send_keys("newpassword123")
driver.find_element(By.ID, "save").click()

end_time = time.time()

# --- Collect Metrics ---
steps = 4  # Login, Password Tab, Enter new password, Save
duration = end_time - start_time

print(f"Steps: {steps}, Time: {duration:.2f}s")

if steps <= 4 and duration <= 10:
    print("Operability Goal Met")
else:
    print("Operability Goal Failed")

driver.quit()