import pandas as pd
import spacy
import logging
from typing import List, Dict, Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HouseAdvisor:
    """
    A class to analyze a list of houses, extract features from text,
    and make suggestions based on user preferences.
    """

    def __init__(self, model_name: str = "pt_core_news_sm"):
        """
        Initialize the HouseAdvisor with a spaCy model.
        
        Args:
            model_name (str): The name of the spaCy model to load. Default is Portuguese.
        """
        try:
            self.nlp = spacy.load(model_name)
            logger.info(f"Loaded spaCy model: {model_name}")
        except OSError:
            logger.warning(f"Model '{model_name}' not found. Downloading...")
            from spacy.cli import download
            download(model_name)
            self.nlp = spacy.load(model_name)
            logger.info(f"Downloaded and loaded spaCy model: {model_name}")

    def extract_features(self, text: str) -> Dict[str, Any]:
        """
        Extracts relevant features from the house description using NLP.
        
        Args:
            text (str): The description text.

        Returns:
            Dict[str, Any]: A dictionary of extracted features (keywords, entities).
        """
        doc = self.nlp(text.lower())
        
        features = {
            "keywords": [],
            "amenities": []
        }

        # Define some common amenities to look for (lemmatized)
        amenity_keywords = {
            "piscina", "churrasqueira", "garagem", "vaga", "varanda", 
            "jardim", "quintal", "academia", "sauna", "segurança", 
            "portaria", "metro", "metrô", "onibus", "ônibus"
        }

        for token in doc:
            # Check for amenities
            if token.lemma_ in amenity_keywords:
                features["amenities"].append(token.lemma_)
            
            # Extract nouns and adjectives as general keywords
            if token.pos_ in ["NOUN", "ADJ"] and not token.is_stop:
                features["keywords"].append(token.lemma_)
        
        # Remove duplicates
        features["amenities"] = list(set(features["amenities"]))
        features["keywords"] = list(set(features["keywords"]))
        
        return features

    def score_house(self, house: Dict[str, Any], preferences: Dict[str, Any]) -> float:
        """
        Calculates a score for a house based on user preferences.
        
        Args:
            house (Dict[str, Any]): House data (must contain 'price' and 'description').
            preferences (Dict[str, Any]): User preferences (max_price, required_amenities).
        
        Returns:
            float: A score representing how well the house matches the preferences.
        """
        score = 0.0
        
        # 1. Price Score (Higher is better if below max_price)
        price = house.get("price", float('inf'))
        max_price = preferences.get("max_price")
        
        if max_price:
            if price <= max_price:
                score += 50  # Base score for being within budget
                # Add bonus for being significantly cheaper (up to 20 points)
                saving_ratio = (max_price - price) / max_price
                score += saving_ratio * 20
            else:
                return 0.0  # Eliminate if over budget (or give negative score)

        # 2. Amenities Score (NLP extracted)
        description = house.get("description", "")
        extracted = self.extract_features(description)
        house_amenities = set(extracted["amenities"])
        
        required_amenities = set(preferences.get("required_amenities", []))
        
        # Check matches
        matches = house_amenities.intersection(required_amenities)
        score += len(matches) * 10  # 10 points per matched amenity
        
        # Penalty for missing required amenities? (Optional)
        # missing = required_amenities - house_amenities
        # score -= len(missing) * 5

        # 3. Location Score (Simple string match for now)
        preferred_location = preferences.get("location")
        if preferred_location and preferred_location.lower() in house.get("location", "").lower():
            score += 30

        return score

    def suggest_best_houses(self, houses: List[Dict[str, Any]], preferences: Dict[str, Any], top_n: int = 3) -> List[Dict[str, Any]]:
        """
        Filters and ranks a list of houses based on preferences.
        
        Args:
            houses (List[Dict[str, Any]]): List of house dictionaries.
            preferences (Dict[str, Any]): User preferences.
            top_n (int): Number of top suggestions to return.
        
        Returns:
            List[Dict[str, Any]]: The top N ranked houses with their scores.
        """
        df = pd.DataFrame(houses)
        
        # Ensure necessary columns exist
        if "price" not in df.columns or "description" not in df.columns:
            logger.error("House list must contain 'price' and 'description' fields.")
            return []

        # Calculate score for each house
        scored_houses = []
        for house in houses:
            score = self.score_house(house, preferences)
            house_with_score = house.copy()
            house_with_score["score"] = score
            house_with_score["extracted_features"] = self.extract_features(house.get("description", ""))
            
            if score > 0: # Only keep relevant matches
                scored_houses.append(house_with_score)
        
        # Sort by score descending
        scored_houses.sort(key=lambda x: x["score"], reverse=True)
        
        return scored_houses[:top_n]

if __name__ == "__main__":
    # Example Usage
    advisor = HouseAdvisor()
    
    sample_houses = [
        {
            "id": 1,
            "title": "Apartamento Centro",
            "price": 450000,
            "location": "Centro, São Paulo",
            "description": "Lindo apartamento com 2 quartos, varanda e vaga de garagem. Próximo ao metrô."
        },
        {
            "id": 2,
            "title": "Casa com Piscina",
            "price": 850000,
            "location": "Morumbi, São Paulo",
            "description": "Casa ampla com 3 suítes, piscina, churrasqueira e jardim. Segurança 24h."
        },
        {
            "id": 3,
            "title": "Kitnet Simples",
            "price": 200000,
            "location": "Centro, São Paulo",
            "description": "Kitnet reformada, sem garagem. Ótima localização."
        }
    ]
    
    user_prefs = {
        "max_price": 900000,
        "required_amenities": ["piscina", "churrasqueira"],
        "location": "São Paulo"
    }
    
    print(f"Analyzing {len(sample_houses)} houses based on preferences: {user_prefs}")
    suggestions = advisor.suggest_best_houses(sample_houses, user_prefs)
    
    print("\n--- Suggestions ---")
    for i, house in enumerate(suggestions, 1):
        print(f"{i}. {house['title']} - Score: {house['score']:.2f}")
        print(f"   Price: R$ {house['price']}")
        print(f"   Amenities Found: {house['extracted_features']['amenities']}")
        print(f"   Description: {house['description']}\n")
