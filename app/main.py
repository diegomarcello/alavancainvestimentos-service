import logging
import os
import time
import glob
import pandas as pd
from typing import List, Dict, Any
from app.data.scraper import BrowserScraper
from app.data.extractor import DataExtractor
from app.data.loader import load_csv_data

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """
    Main orchestration function:
    1. Load data from CSV using loader.
    2. Iterate through each property link.
    3. Scrape HTML and save it.
    4. Extract content from #dadosImovel.
    5. Save enriched data to DataFrame and export to Excel.
    """
    logger.info("Starting Alavanca Investimentos Service...")

    # 1. Load Data
    # Assuming the file is in app/data/uploads/Lista_imoveis_PR.csv based on previous context
    input_csv = os.path.join(os.path.dirname(__file__), "data", "uploads", "Lista_imoveis_PR.csv")
    
    if not os.path.exists(input_csv):
        logger.error(f"Input file not found: {input_csv}")
        return

    logger.info(f"Loading data from {input_csv}...")
    records = load_csv_data(input_csv)
    
    # LIMIT FOR TESTING
    # records = records[:3]
    # logger.info(f"Running in TEST MODE: Processing only {len(records)} records.")
    
    if not records:
        logger.warning("No records found in CSV.")
        return

    logger.info(f"Loaded {len(records)} records. Starting scraping...")

    processed_records = []
    output_dir = "tmp-al-service"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Initialize Scraper
    with BrowserScraper(headless=True) as scraper:
        # Process all records
        for i, record in enumerate(records): 
            url = record.get("link")
            id_imovel = record.get("id_imovel", "unknown")
            
            if not url:
                logger.warning(f"Record {i} has no link. Skipping.")
                continue

            logger.info(f"Processing record {i+1}/{len(records)}: {id_imovel}")
            
            try:
                # Check for existing file
                html_content = ""
                if id_imovel and id_imovel != "unknown":
                    pattern = f"imovel_{id_imovel}_*.html"
                    existing_files = glob.glob(os.path.join(output_dir, pattern))
                    if existing_files:
                        # Use the most recent file
                        latest_file = sorted(existing_files)[-1]
                        logger.info(f"Validation: File for {id_imovel} already exists ({os.path.basename(latest_file)}). Skipping download.")
                        try:
                            with open(latest_file, "r", encoding="utf-8") as f:
                                html_content = f.read()
                            record["saved_html_path"] = latest_file
                        except Exception as e:
                            logger.warning(f"Failed to read existing file {latest_file}: {e}. Will re-scrape.")
                            html_content = ""

                if not html_content:
                    # Scrape URL
                    html_content = scraper.get_page_source(url)
                    
                    if not html_content:
                        logger.warning(f"Failed to retrieve content for {url}")
                        record["scraping_status"] = "failed"
                        processed_records.append(record)
                        continue
    
                    # Save raw HTML
                    filename = f"imovel_{id_imovel}_{int(time.time())}.html"
                    saved_path = scraper.save_page_source(html_content, filename, output_dir=output_dir)
                    record["saved_html_path"] = saved_path
                
                # Extract Data from #dadosImovel
                extractor = DataExtractor(html_content)
                details = extractor.extract_property_details()
                
                if details:
                    # Merge structured details into the record
                    record.update(details)
                    logger.info(f"Extracted detailed properties for {id_imovel}")
                else:
                    logger.warning(f"Element #dadosImovel details could not be extracted for {id_imovel}")
                    
                # Also keep raw text for backup/debugging
                raw_text = extractor.extract_element_text("#dadosImovel", separator="\n")
                record["raw_dados_imovel"] = raw_text if raw_text else "Not Found"

                record["scraping_status"] = "success"
                processed_records.append(record)

            except Exception as e:
                logger.error(f"Error processing {url}: {e}")
                record["scraping_status"] = "error"
                record["error_message"] = str(e)
                processed_records.append(record)

    # 5. Generate Excel
    if processed_records:
        df = pd.DataFrame(processed_records)
        excel_path = os.path.join(output_dir, "imoveis_enriched.xlsx")
        
        try:
            df.to_excel(excel_path, index=False)
            logger.info(f"Data saved to {excel_path}")
            print(f"\n--- Processing Complete ---")
            print(f"Total processed: {len(df)}")
            print(f"Excel location: {excel_path}")
        except Exception as e:
            logger.error(f"Failed to save Excel: {e}")
            # Fallback to CSV
            csv_path = os.path.join(output_dir, "imoveis_enriched.csv")
            df.to_csv(csv_path, index=False, encoding="utf-8-sig")
            logger.info(f"Saved to CSV fallback: {csv_path}")
    else:
        logger.warning("No data processed.")

if __name__ == "__main__":
    main()
