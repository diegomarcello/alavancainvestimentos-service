import logging
import os
import time
import pandas as pd
from typing import List, Dict, Any
from app.data.scraper import BrowserScraper, load_config
from app.data.extractor import DataExtractor

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """
    Main orchestration function:
    1. Load site configuration.
    2. Iterate through enabled sites.
    3. Scrape data (if method is scraping).
    4. Extract data using selectors.
    5. Organize and save to CSV.
    """
    logger.info("Starting Alavanca Investimentos Service...")

    # 1. Load Configuration
    config_path = os.path.join(os.path.dirname(__file__), "config", "site.yaml")
    config = load_config(config_path)
    
    if not config or "sites" not in config:
        logger.error("Failed to load configuration or no sites found.")
        return

    extracted_data_list = []
    output_dir = "tmp-al-service"
    
    # Initialize Scraper (headless)
    with BrowserScraper(headless=True) as scraper:
        
        for site in config["sites"]:
            # Only process enabled sites with method 'scraping'
            if not site.get("enabled") or site.get("method") != "scraping":
                continue

            logger.info(f"Processing site: {site['name']} ({site['url']})")
            
            # Determine URLs to scrape
            # If endpoints are defined, construct them. Otherwise, just scrape the base URL.
            urls_to_scrape = []
            
            if "endpoints" in site:
                for endpoint in site["endpoints"]:
                    # For demonstration, we'll try to fill parameters with defaults or placeholders
                    # In a real scenario, we might iterate over a list of tickers
                    
                    # Hack: For Status Invest, let's try a specific ticker if the path has placeholders
                    path = endpoint["path"]
                    if "{ticker}" in path and "{asset_type}" in path:
                        # Add a few sample assets
                        urls_to_scrape.append({"url": site["url"] + path.format(asset_type="acoes", ticker="PETR4"), "ticker": "PETR4"})
                        urls_to_scrape.append({"url": site["url"] + path.format(asset_type="acoes", ticker="VALE3"), "ticker": "VALE3"})
                    else:
                        urls_to_scrape.append({"url": site["url"] + path, "ticker": "N/A"})
            else:
                urls_to_scrape.append({"url": site["url"], "ticker": "HOME"})

            # Scrape each URL
            for item in urls_to_scrape:
                url = item["url"]
                ticker = item["ticker"]
                
                logger.info(f"Scraping URL: {url}")
                html_content = scraper.get_page_source(url)
                
                if not html_content:
                    logger.warning(f"No content fetched for {url}")
                    continue

                # Save raw HTML
                filename = f"{site['id']}_{ticker}_{int(time.time())}.html"
                saved_path = scraper.save_page_source(html_content, filename, output_dir=output_dir)
                
                # Extract Data
                selectors = site.get("selectors", {})
                extractor = DataExtractor(html_content)
                
                record = {
                    "site_id": site["id"],
                    "site_name": site["name"],
                    "ticker": ticker,
                    "url": url,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "saved_file": saved_path
                }

                # Generic extraction based on selectors
                if selectors:
                    for key, selector in selectors.items():
                        # Try extracting text first
                        value = extractor.extract_text(selector)
                        # If simple text is empty, maybe it's a list or table? 
                        # For now, let's keep it simple string extraction
                        record[key] = value if value else "N/A"
                
                extracted_data_list.append(record)
                logger.info(f"Extracted data for {ticker}")

    # 5. Generate CSV
    if extracted_data_list:
        df = pd.DataFrame(extracted_data_list)
        csv_path = os.path.join(output_dir, "consolidated_data.csv")
        df.to_csv(csv_path, index=False, encoding="utf-8-sig")
        logger.info(f"Data saved to {csv_path}")
        print(f"\n--- Processing Complete ---")
        print(f"Total records: {len(df)}")
        print(f"CSV location: {csv_path}")
        print(df.head())
    else:
        logger.warning("No data extracted.")

if __name__ == "__main__":
    main()
