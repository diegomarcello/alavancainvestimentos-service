import logging
import time
from typing import Optional, Dict, Any
import yaml
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BrowserScraper:
    """
    A class to handle browser emulation using Selenium for scraping data.
    """

    def __init__(self, headless: bool = True):
        """
        Initialize the BrowserScraper.

        Args:
            headless (bool): Whether to run the browser in headless mode.
        """
        self.headless = headless
        self.driver = self._setup_driver()

    def _setup_driver(self) -> webdriver.Chrome:
        """
        Sets up the Chrome WebDriver using webdriver-manager.

        Returns:
            webdriver.Chrome: The configured Chrome WebDriver instance.
        """
        chrome_options = Options()
        if self.headless:
            chrome_options.add_argument("--headless")
        
        # Add common options to avoid detection and improve stability
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")

        try:
            service = ChromeService(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
            logger.info("Chrome WebDriver initialized successfully.")
            return driver
        except Exception as e:
            logger.error(f"Failed to initialize Chrome WebDriver: {e}")
            raise

    def get_page_source(self, url: str, wait_for_element: Optional[str] = None, timeout: int = 10) -> str:
        """
        Navigates to a URL and returns the page source.

        Args:
            url (str): The URL to visit.
            wait_for_element (Optional[str]): CSS selector of an element to wait for before returning.
            timeout (int): Time to wait for the element in seconds.

        Returns:
            str: The HTML source of the page.
        """
        try:
            logger.info(f"Navigating to {url}")
            self.driver.get(url)

            if wait_for_element:
                try:
                    WebDriverWait(self.driver, timeout).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, wait_for_element))
                    )
                    logger.info(f"Element {wait_for_element} found.")
                except Exception as e:
                    logger.warning(f"Timeout waiting for element {wait_for_element}: {e}")

            return self.driver.page_source
        except Exception as e:
            logger.error(f"Error fetching page source from {url}: {e}")
            return ""

    def close(self):
        """
        Closes the browser and quits the driver.
        """
        if self.driver:
            self.driver.quit()
            logger.info("Browser closed.")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

def load_config(config_path: str = "../config/site.yaml") -> Dict[str, Any]:
    """
    Loads the site configuration from a YAML file.
    """
    try:
        with open(config_path, "r", encoding="utf-8") as file:
            return yaml.safe_load(file)
    except Exception as e:
        logger.error(f"Failed to load config from {config_path}: {e}")
        return {}

if __name__ == "__main__":
    # Example usage
    import os
    
    # Adjust path if running from this directory
    config_path = os.path.join(os.path.dirname(__file__), "..", "config", "site.yaml")
    
    config = load_config(config_path)
    
    if config and "sites" in config:
        # Let's try to scrape the first enabled site if it's a scraping type
        target_site = next((s for s in config["sites"] if s.get("enabled") and s.get("method") == "scraping"), None)
        
        if target_site:
            url = target_site["url"]
            logger.info(f"Testing scraper with site: {target_site['name']} ({url})")
            
            with BrowserScraper(headless=True) as scraper:
                # Just fetching the home page for demonstration
                html = scraper.get_page_source(url)
                print(f"Successfully fetched {len(html)} characters from {url}")
                
                # Save to file
                filename = f"{target_site['id']}_home.html"
                saved_path = scraper.save_page_source(html, filename)
                if saved_path:
                    print(f"HTML saved to: {saved_path}")
                    
                print("First 500 chars of HTML:")
                print(html[:500])
        else:
            print("No enabled scraping sites found in config.")
    else:
        print("Could not load configuration.")
