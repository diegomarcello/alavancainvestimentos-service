import pandas as pd
import logging
import os
import unicodedata
from typing import List, Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def normalize_text(text: Any) -> str:
    """
    Normalizes text by removing accents and special characters.
    Example: 'São Paulo' -> 'Sao Paulo'
    """
    if not isinstance(text, str):
        return text
    
    # Normalize unicode characters (NFKD decomposition)
    normalized = unicodedata.normalize('NFKD', text)
    # Filter out non-spacing mark characters (accents) and encode back to ASCII
    # Also remove the replacement character if present
    return "".join([c for c in normalized if not unicodedata.combining(c)]).replace('\ufffd', '')

def clean_currency(value: Any) -> float:
    """
    Converts a Brazilian currency string (e.g., '2.090.745,83') to a float.
    """
    if pd.isna(value):
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    
    # Remove thousand separators (.) and replace decimal separator (,) with (.)
    clean_val = str(value).replace('.', '').replace(',', '.')
    try:
        return float(clean_val)
    except ValueError:
        return 0.0

def load_csv_data(file_path: str, encoding: str = 'utf-8', sep: str = ';') -> List[Dict[str, Any]]:
    """
    Reads a CSV file and returns a list of dictionaries.
    Handles Brazilian CSV formats and cleans corrupted headers.

    Args:
        file_path (str): Path to the CSV file.
        encoding (str): File encoding (default: 'utf-8' as the file seems to contain UTF-8 replacement chars).
        sep (str): Column separator (default: ';').

    Returns:
        List[Dict[str, Any]]: List of records.
    """
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        return []

    try:
        logger.info(f"Loading data from {file_path}")
        df = pd.read_csv(file_path, encoding=encoding, sep=sep)
        
        # Rename corrupted columns to clean names
        # The file contains replacement characters (\ufffd), so we match partial strings
        column_mapping = {}
        for col in df.columns:
            clean_col = normalize_text(col).strip()
            # Match both correct spelling and likely corrupted versions (missing chars)
            if ("imovel" in clean_col or "imvel" in clean_col) and "N" in clean_col:
                column_mapping[col] = "id_imovel"
            elif "Endereco" in clean_col or "Endereo" in clean_col:
                column_mapping[col] = "endereco"
            elif "Preco" in clean_col or "Preo" in clean_col:
                column_mapping[col] = "preco"
            elif "avaliacao" in clean_col or "avaliao" in clean_col:
                column_mapping[col] = "valor_avaliacao"
            elif "Descricao" in clean_col or "Descrio" in clean_col:
                column_mapping[col] = "descricao"
            elif "Modalidade" in clean_col:
                column_mapping[col] = "modalidade"
            elif "Link" in clean_col:
                column_mapping[col] = "link"
            else:
                column_mapping[col] = clean_col.lower().replace(" ", "_")
        
        df.rename(columns=column_mapping, inplace=True)
        logger.info(f"Renamed columns: {df.columns.tolist()}")

        # Clean numeric columns commonly found in Brazilian real estate data
        # "preco", "valor_avaliacao", "desconto"
        currency_cols = [col for col in df.columns if any(x in col for x in ['preco', 'valor', 'desconto'])]
        
        for col in currency_cols:
            df[col] = df[col].apply(clean_currency)

        # Convert to list of dicts
        records = df.to_dict(orient='records')
        logger.info(f"Successfully loaded {len(records)} records.")
        return records

    except Exception as e:
        logger.error(f"Error loading CSV: {e}")
        return []

if __name__ == "__main__":
    # Test with the specific file we found
    base_dir = os.path.dirname(__file__)
    csv_file = os.path.join(base_dir, "uploads", "Lista_imoveis_PR.csv")
    
    data = load_csv_data(csv_file)
    
    if data:
        print("\n--- First 3 Records ---")
        for i, record in enumerate(data[:3]):
            print(f"Record {i+1}: {record}")
