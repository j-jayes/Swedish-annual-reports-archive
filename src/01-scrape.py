from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import requests
import os
from dotenv import load_dotenv

# Load environment variables from the .env file
load_dotenv()

# Initialize the WebDriver (make sure to have the appropriate WebDriver installed, e.g., ChromeDriver)
driver = webdriver.Chrome()  # Or use any other WebDriver you prefer, such as Firefox

# Open the initial URL
driver.get('https://data.houseoffinance.se/otherDB/historicalArchive')

# Wait for the redirection to md.nordu.net
WebDriverWait(driver, 10).until(EC.url_contains('md.nordu.net'))

# Wait for the page to load and input field to be present
WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, 'searchinput')))

# Input the institution name and select it
search_input = driver.find_element(By.ID, 'searchinput')
search_input.send_keys('lund')
time.sleep(2)  # Wait for the suggestions to appear

# Select Lund University
lund_option = driver.find_element(By.XPATH, "//div[contains(text(), 'Lund University')]")
lund_option.click()

# Click the 'Proceed to Login' button
proceed_button = driver.find_element(By.ID, 'proceed')
proceed_button.click()

WebDriverWait(driver, 10).until(EC.url_contains('idpv4.lu.se'))

# wait one second
time.sleep(1)

# Enter the username and password
username_input = driver.find_element(By.ID, 'username')
password_input = driver.find_element(By.ID, 'password')

# Load the username and password from the environment variables
username_input.send_keys(os.getenv('username'))
password_input.send_keys(os.getenv('password'))

# print username
print(username_input.get_attribute('value'))

# Click the 'LOGGA IN' button to submit the form
login_button = driver.find_element(By.CSS_SELECTOR, "input.btn-submit")
login_button.click()

# At this point, you should be logged in. You can proceed with your scraping tasks.

# Example: print the current URL to the console
print(driver.current_url)

# Don't forget to close the driver after you're done
# driver.quit()
# Locate all company sections
companies = driver.find_elements(By.CSS_SELECTOR, 'div.panel.panel-default')

for company in companies:
    # Click on each company section to expand
    company_title = company.find_element(By.CSS_SELECTOR, 'a.btn-lg')
    driver.execute_script("arguments[0].click();", company_title)
    
    # Wait for the PDFs to load
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div.panel-collapse.in')))
    
    # Locate all PDF links within the expanded company section
    pdf_links = company.find_elements(By.CSS_SELECTOR, 'div.panel-collapse.in a')
    
    for pdf_link in pdf_links:
        # Click each PDF link to trigger download
        driver.execute_script("arguments[0].click();", pdf_link)
        time.sleep(2)  # Wait for the download to start

# quit the driver
driver.quit()