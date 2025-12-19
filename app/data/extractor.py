import logging
import json
from typing import Dict, Any, List, Optional
from bs4 import BeautifulSoup

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataExtractor:
    """
    A class to extract specific data from HTML content using BeautifulSoup.
    """

    def __init__(self, html_content: str, parser: str = "html.parser"):
        """
        Initialize the DataExtractor.

        Args:
            html_content (str): The raw HTML content to parse.
            parser (str): The parser to use (default: "html.parser").
        """
        self.soup = BeautifulSoup(html_content, parser)

    def extract_text(self, selector: str) -> Optional[str]:
        """
        Extracts text from the first element matching the CSS selector.
        
        Args:
            selector (str): CSS selector to find the element.

        Returns:
            Optional[str]: Stripped text content or None if not found.
        """
        element = self.soup.select_one(selector)
        return element.get_text(strip=True) if element else None

    def extract_attribute(self, selector: str, attribute: str) -> Optional[str]:
        """
        Extracts a specific attribute from the first element matching the CSS selector.

        Args:
            selector (str): CSS selector to find the element.
            attribute (str): The attribute name to extract (e.g., 'href', 'src').

        Returns:
            Optional[str]: The attribute value or None if not found.
        """
        element = self.soup.select_one(selector)
        return element.get(attribute) if element else None

    def extract_list(self, selector: str) -> List[str]:
        """
        Extracts a list of text content from all elements matching the CSS selector.

        Args:
            selector (str): CSS selector to find the elements.

        Returns:
            List[str]: A list of stripped text strings.
        """
        elements = self.soup.select(selector)
        return [el.get_text(strip=True) for el in elements]

    def extract_table(self, selector: str) -> List[Dict[str, str]]:
        """
        Extracts data from a simple HTML table into a list of dictionaries.
        Assumes the first row contains headers.

        Args:
            selector (str): CSS selector for the table element.

        Returns:
            List[Dict[str, str]]: A list of rows, where keys are headers.
        """
        table = self.soup.select_one(selector)
        if not table:
            return []

        data = []
        headers = []
        
        # Try to find headers in thead, or first tr
        thead = table.find('thead')
        if thead:
            header_row = thead.find('tr')
        else:
            header_row = table.find('tr')

        if header_row:
            headers = [th.get_text(strip=True) for th in header_row.find_all(['th', 'td'])]

        # Iterate over rows (skip the first if we used it as header and it was in tbody or direct child)
        rows = table.find_all('tr')
        start_index = 1 if not thead and rows and rows[0] == header_row else 0

        for row in rows[start_index:]:
            cells = row.find_all(['td', 'th'])
            if len(cells) == len(headers):
                row_data = {headers[i]: cells[i].get_text(strip=True) for i in range(len(headers))}
                data.append(row_data)
        
        return data

    def to_json(self, data: Any) -> str:
        """
        Converts a dictionary or list to a JSON string.
        """
        return json.dumps(data, indent=4, ensure_ascii=False)

if __name__ == "__main__":
    # Example Usage
    html_sample = """
    <html>
        <body>
            <div id="stock-info">
                <h1 class="ticker">PETR4</h1>
                <span class="price">34.50</span>
                <div class="details">
                    <p>Sector: Energy</p>
                </div>
            </div>
            <table id="financials">
                <thead>
                    <tr>
                        <th>Year</th>
                        <th>Revenue</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>2023</td>
                        <td>500B</td>
                    </tr>
                    <tr>
                        <td>2022</td>
                        <td>450B</td>
                    </tr>
                </tbody>
            </table>
        </body>
    </html>
    """

    extractor = DataExtractor(html_sample)
    
    extracted_data = {
        "ticker": extractor.extract_text("h1.ticker"),
        "price": extractor.extract_text("span.price"),
        "sector": extractor.extract_text("div.details p"),
        "financials": extractor.extract_table("#financials")
    }

    print("Extracted Data JSON:")
    print(extractor.to_json(extracted_data))
