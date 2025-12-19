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

    def extract_element_text(self, selector: str, separator: str = "\n") -> Optional[str]:
        """
        Extracts all text from an element, using a separator for child elements.
        Useful for preserving structure in complex elements.

        Args:
            selector (str): CSS selector to find the element.
            separator (str): Separator to join text parts (default: newline).

        Returns:
            Optional[str]: Joined text content or None if not found.
        """
        element = self.soup.select_one(selector)
        if not element:
            return None
        return element.get_text(separator=separator, strip=True)

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

    def extract_property_details(self) -> Dict[str, Any]:
        """
        Extracts specific property details from the Caixa Imóveis page structure.
        Targeting #dadosImovel and its children.
        """
        details = {}
        container = self.soup.select_one("#dadosImovel")
        if not container:
            return details

        # --- Helpers ---
        def get_text_after_label(label_text, container=container):
            """Finds a label and returns the text immediately following it (usually in strong/b or next sibling)."""
            if not container: return None
            # Strategy 1: Look for text node, then check parent's strong/b siblings
            elements = container.find_all(string=lambda text: text and label_text in text)
            for text in elements:
                # Case 1: <span>Label: <strong>Value</strong></span>
                parent = text.parent
                strong = parent.find(['strong', 'b'])
                if strong:
                    return strong.get_text(strip=True)
                
                # Case 2: Label is in strong, value is next text node
                # Case 3: Label is text, value is in next sibling tag
                next_tag = parent.find_next(['strong', 'b', 'span'])
                if next_tag:
                     return next_tag.get_text(strip=True)
            return None

        # --- 1. Localização e Identificação ---
        # Cidade/Bairro (Header)
        h5 = container.select_one("h5")
        if h5:
            # Extract text excluding hidden inputs
            details["Cidade_Bairro"] = "".join([c for c in h5.contents if isinstance(c, str)]).strip()
        
        details["Numero_Imovel"] = get_text_after_label("Número do imóvel")
        details["Matricula"] = get_text_after_label("Matrícula(s)")
        details["Inscricao_Imobiliaria"] = get_text_after_label("Inscrição imobiliária")
        
        # Address
        related_box = container.select_one(".related-box")
        if related_box:
            addr_node = related_box.find(string=lambda text: text and "Endereço:" in text)
            if addr_node:
                # Usually: <p><strong>Endereço:</strong><br>VALUE...</p>
                # We get the parent paragraph and try to extract text ignoring the label
                p_tag = addr_node.find_parent("p")
                if p_tag:
                    full_text = p_tag.get_text(separator=" ", strip=True)
                    details["Endereco"] = full_text.replace("Endereço:", "").strip()
            
            # CEP (Often part of address, but let's try to extract if distinct or regex)
            if "Endereco" in details:
                import re
                cep_match = re.search(r"\d{5}-\d{3}", details["Endereco"])
                details["CEP"] = cep_match.group(0) if cep_match else "N/A"

        # --- 2. Valores e Datas ---
        # Usually in the first paragraph of .content
        content_div = container.select_one(".content")
        if content_div:
            p_val = content_div.select_one("p")
            if p_val:
                text = p_val.get_text(separator=" ", strip=True)
                
                # Regex for values
                import re
                val_aval = re.search(r"Valor de avaliação:?\s*(R\$\s*[\d\.,]+)", text, re.IGNORECASE)
                details["Valor_Avaliacao"] = val_aval.group(1) if val_aval else None
                
                val_min = re.search(r"Valor mínimo.*:?\s*(R\$\s*[\d\.,]+)", text, re.IGNORECASE)
                details["Valor_Minimo"] = val_min.group(1) if val_min else None
                
                # Leilão Dates/Values (if present in table or text)
                # Looking for "1º Leilão" patterns
                leilao1 = re.search(r"1º Leilão.*:?\s*(\d{2}/\d{2}/\d{4})", text, re.IGNORECASE)
                details["Data_1_Leilao"] = leilao1.group(1) if leilao1 else None
                
                leilao2 = re.search(r"2º Leilão.*:?\s*(\d{2}/\d{2}/\d{4})", text, re.IGNORECASE)
                details["Data_2_Leilao"] = leilao2.group(1) if leilao2 else None

                # Fallback: if no specific leilao dates found, try generic "Data Leilão"
                if not details["Data_1_Leilao"]:
                     leilao_generic = re.search(r"Data.*Leilão.*:?\s*(\d{2}/\d{2}/\d{4})", text, re.IGNORECASE)
                     if leilao_generic:
                         details["Data_1_Leilao"] = leilao_generic.group(1)

        # --- 3. Características do Imóvel ---
        details["Tipo_Imovel"] = get_text_after_label("Tipo de imóvel")
        details["Area_Terreno"] = get_text_after_label("Área do terreno")
        details["Area_Privativa"] = get_text_after_label("Área privativa")
        details["Quartos"] = get_text_after_label("Quartos")
        details["Garagem"] = get_text_after_label("Garagem")
        
        # Description (often contains distribution)
        if related_box:
             desc_node = related_box.find(string=lambda text: text and "Descrição:" in text)
             if desc_node:
                 p_desc = desc_node.find_parent("p")
                 if p_desc:
                     details["Descricao"] = p_desc.get_text(separator=" ", strip=True).replace("Descrição:", "").strip()

        # --- 4. Detalhes do Leilão ---
        details["Edital"] = get_text_after_label("Edital") # Might not be present in all
        details["Averbacao_Leiloes"] = get_text_after_label("Averbação dos leilões")
        
        # --- 5. Condições de Pagamento ---
        # Looking for "FORMAS DE PAGAMENTO ACEITAS" in related box
        if related_box:
             pag_node = related_box.find(string=lambda text: text and "FORMAS DE PAGAMENTO ACEITAS" in text)
             if pag_node:
                 p_pag = pag_node.find_parent("p")
                 if p_pag:
                     # This is usually a blob of text. We can just capture the whole paragraph.
                     details["Condicoes_Pagamento"] = p_pag.get_text(separator=" ", strip=True)

        return details

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
