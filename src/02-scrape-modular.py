from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import os
from dotenv import load_dotenv

def main():
    """
    Main function to execute the web scraping task.
    """
    # Load environment variables from the .env file
    load_dotenv()

    # Initialize the WebDriver (make sure to have the appropriate WebDriver installed, e.g., ChromeDriver)
    driver = webdriver.Chrome()  # Or use any other WebDriver you prefer, such as Firefox

    try:
        # Open the initial URL
        driver.get('https://data.houseoffinance.se/otherDB/historicalArchive')

        # Wait for the redirection to md.nordu.net
        wait_for_url_contains(driver, 'md.nordu.net', 10)

        # Wait for the page to load and input field to be present
        wait_for_element(driver, By.ID, 'searchinput', 10)

        # Input the institution name and select it
        select_institution(driver, 'lund')

        # Click the 'Proceed to Login' button
        click_element(driver, By.ID, 'proceed')

        # Wait for redirection to idpv4.lu.se
        wait_for_url_contains(driver, 'idpv4.lu.se', 10)

        # Wait for a moment before proceeding
        time.sleep(1)

        # Enter the username and password
        login(driver)

        # Print the current URL to the console to confirm successful login
        print(driver.current_url)

        # Proceed with scraping tasks
        scrape_companies(driver)
    finally:
        # Close the driver after the tasks are done
        driver.quit()

def wait_for_url_contains(driver, url_fragment, timeout):
    """
    Wait for the URL to contain a specific fragment.
    
    :param driver: WebDriver instance
    :param url_fragment: Fragment of the URL to wait for
    :param timeout: Maximum time to wait in seconds
    """
    WebDriverWait(driver, timeout).until(EC.url_contains(url_fragment))

def wait_for_element(driver, by, identifier, timeout):
    """
    Wait for an element to be present on the page.
    
    :param driver: WebDriver instance
    :param by: Locator strategy (By.ID, By.XPATH, etc.)
    :param identifier: Identifier for locating the element
    :param timeout: Maximum time to wait in seconds
    """
    WebDriverWait(driver, timeout).until(EC.presence_of_element_located((by, identifier)))

def select_institution(driver, institution_name):
    """
    Select the institution by typing its name and choosing from suggestions.
    
    :param driver: WebDriver instance
    :param institution_name: Name of the institution to select
    """
    search_input = driver.find_element(By.ID, 'searchinput')
    search_input.send_keys(institution_name)
    time.sleep(2)  # Wait for the suggestions to appear

    # Select the institution from the suggestions
    lund_option = driver.find_element(By.XPATH, f"//div[contains(text(), '{institution_name.capitalize()} University')]")
    lund_option.click()

def click_element(driver, by, identifier):
    """
    Click an element on the page.
    
    :param driver: WebDriver instance
    :param by: Locator strategy (By.ID, By.XPATH, etc.)
    :param identifier: Identifier for locating the element
    """
    element = driver.find_element(by, identifier)
    element.click()

def login(driver):
    """
    Enter the login credentials and submit the login form.
    
    :param driver: WebDriver instance
    """
    username_input = driver.find_element(By.ID, 'username')
    password_input = driver.find_element(By.ID, 'password')

    # Load the username and password from the environment variables
    username_input.send_keys(os.getenv('username'))
    password_input.send_keys(os.getenv('password'))

    # Print the username to the console for verification
    print(username_input.get_attribute('value'))

    # Click the 'LOGGA IN' button to submit the form
    login_button = driver.find_element(By.CSS_SELECTOR, "input.btn-submit")
    login_button.click()

def scrape_companies(driver):
    """
    Scrape company data and download PDFs.
    
    :param driver: WebDriver instance
    """
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

if __name__ == "__main__":
    main()
