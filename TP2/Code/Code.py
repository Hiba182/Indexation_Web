import json
import string
import re
from urllib.parse import urlparse
from pathlib import Path

STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "with"
}

def load_jsonl(path):
    documents = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            documents.append(json.loads(line))
    return documents

def tokenize_and_clean(text):
    """Tokenize by space, remove punctuation and stopwords, convert to lowercase
    Returns: list of tokens (only non-stopword tokens)
    """
    if not text:
        return []
    text = text.lower()
    text = text.translate(str.maketrans('', '', string.punctuation))
    tokens = text.split()
    tokens = [token for token in tokens if token and token not in STOPWORDS]
    
    return tokens


def create_inverted_index(documents, field):
    """Create inverted index for a specific field (title or description)
    Returns: dict with structure {token: {url: [positions]}}
    where positions are the indices in the cleaned token list
    """
    inverted_index = {}
    
    for doc in documents:
        url = doc.get("url", "")
        text = doc.get(field, "")
      
        tokens = tokenize_and_clean(text)

        for position, token in enumerate(tokens):
            if token not in inverted_index:
                inverted_index[token] = {}
            
            if url not in inverted_index[token]:
                inverted_index[token][url] = []
            
            inverted_index[token][url].append(position)
    
    return inverted_index


def create_reviews_index(documents):
    """Create reviews index for each document (non-inverted)
    Returns: dict with structure {url: {"total_reviews": int, "mean_mark": float, "last_rating": int}}
    """
    reviews_index = {}
    
    for doc in documents:
        url = doc.get("url", "")
        reviews = doc.get("product_reviews", [])
        
        if reviews:
            total_reviews = len(reviews)
            ratings = [review.get("rating", 0) for review in reviews]
            mean_mark = sum(ratings) / total_reviews if total_reviews > 0 else 0
            last_rating = reviews[-1].get("rating", 0) if reviews else 0
        else:
            total_reviews = 0
            mean_mark = 0
            last_rating = 0
        
        reviews_index[url] = {
            "total_reviews": total_reviews,
            "mean_mark": round(mean_mark, 1),
            "last_rating": last_rating
        }
    
    return reviews_index


def create_brand_index(documents):
    """Create inverted index for product brands
    Returns: dict with structure {brand: [urls]}
    """
    brand_index = {}
    
    for doc in documents:
        url = doc.get("url", "")
        product_features = doc.get("product_features", {})
        
        brand = product_features.get("brand", "")
        if brand:
            brand = brand.lower()
            if brand not in brand_index:
                brand_index[brand] = []
            if url not in brand_index[brand]:
                brand_index[brand].append(url)
    
    return brand_index


def create_origin_index(documents):
    """Create inverted index for product origin
    Returns: dict with structure {origin: [urls]}
    """
    origin_index = {}
    
    for doc in documents:
        url = doc.get("url", "")
        product_features = doc.get("product_features", {})

        origin = product_features.get("made in", "") or product_features.get("origin", "") or product_features.get("country", "")
        if origin:
            origin = origin.lower()
            if origin not in origin_index:
                origin_index[origin] = []
            if url not in origin_index[origin]:
                origin_index[origin].append(url)
    
    return origin_index


def create_other_features_index(documents):
    """Create inverted index for other product features (excluding brand and origin)
    Returns: dict with structure {feature_type: {feature_value: [urls]}}
    """
    other_features_index = {}
    
    # Features to exclude
    excluded_features = {"brand", "made in", "origin", "country"}
    
    for doc in documents:
        url = doc.get("url", "")
        product_features = doc.get("product_features", {})
    
        for feature_type, feature_value in product_features.items():
            if feature_type.lower() in excluded_features:
                continue
                
            if not feature_type or not feature_value:
                continue
            
            feature_type = feature_type.lower()
            
            if isinstance(feature_value, str):
                feature_value = feature_value.lower()
            else:
                feature_value = str(feature_value).lower()
            
         
            if feature_type not in other_features_index:
                other_features_index[feature_type] = {}
            
            if feature_value not in other_features_index[feature_type]:
                other_features_index[feature_type][feature_value] = []
            
            if url not in other_features_index[feature_type][feature_value]:
                other_features_index[feature_type][feature_value].append(url)
    
    return other_features_index


if __name__ == "__main__":
    
    jsonl_path = Path(__file__).resolve().parent.parent / "Input" / "products.jsonl"
    documents = load_jsonl(str(jsonl_path))
    title_index = create_inverted_index(documents, "title")
    description_index = create_inverted_index(documents, "description")
    reviews_index = create_reviews_index(documents)
    brand_index = create_brand_index(documents)
    origin_index = create_origin_index(documents)
    other_features_index = create_other_features_index(documents)
    output_dir = Path(__file__).resolve().parent.parent / "Output"
    output_dir.mkdir(exist_ok=True)
    
    with open(output_dir / "title_index.json", "w", encoding="utf-8") as f:
        json.dump(title_index, f, ensure_ascii=False, indent=2)
    
    with open(output_dir / "description_index.json", "w", encoding="utf-8") as f:
        json.dump(description_index, f, ensure_ascii=False, indent=2)
    
    with open(output_dir / "reviews_index.json", "w", encoding="utf-8") as f:
        json.dump(reviews_index, f, ensure_ascii=False, indent=2)
    
    with open(output_dir / "brand_index.json", "w", encoding="utf-8") as f:
        json.dump(brand_index, f, ensure_ascii=False, indent=2)
    
    with open(output_dir / "origin_index.json", "w", encoding="utf-8") as f:
        json.dump(origin_index, f, ensure_ascii=False, indent=2)
    
    with open(output_dir / "other_features_index.json", "w", encoding="utf-8") as f:
        json.dump(other_features_index, f, ensure_ascii=False, indent=2)
    print(f"Indexes saved to {output_dir}")
    print(f"  - title_index.json: {len(title_index)} tokens")
    print(f"  - description_index.json: {len(description_index)} tokens")
    print(f"  - reviews_index.json: {len(reviews_index)} documents")
    print(f"  - brand_index.json: {len(brand_index)} brands")
    print(f"  - origin_index.json: {len(origin_index)} origins")
    print(f"  - other_features_index.json: {len(other_features_index)} feature types")

  