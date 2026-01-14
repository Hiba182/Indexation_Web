import json
import string
import re
from urllib.parse import urlparse
from pathlib import Path
import nltk
from nltk.corpus import stopwords
import math

nltk.download('stopwords', quiet=True)
STOPWORDS = set(stopwords.words('english'))

def load_json(path):
    """Load a JSON file"""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

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

def load_indexes(input_dir):
    """Load all indexes from the input directory"""
    indexes = {}
    index_files = [
        "title_index.json",
        "description_index.json",
        "reviews_index.json",
        "brand_index.json",
        "origin_index.json"
    ]
    
    for file_name in index_files:
        file_path = input_dir / file_name
        if file_path.exists():
            indexes[file_name.replace("_index.json", "_index")] = load_json(file_path)
    
    return indexes

def load_synonyms(synonyms_path):
    """Load synonyms dictionary from JSON file"""
    return load_json(synonyms_path)

def process_query(query):
    """Process a query: tokenize and clean"""
    return tokenize_and_clean(query)

def normalize_query(query):
    """Normalize query: lowercase """
    if not query:
        return ""
    return query.lower()

def augment_query_with_synonyms(tokens, synonyms):
    """Augment query tokens with synonyms for origins"""
    augmented = set(tokens)
    
    # Create reverse mapping: synonym -> canonical
    synonym_to_canonical = {}
    for canonical, syns in synonyms.items():
        for syn in syns:
            synonym_to_canonical[syn] = canonical
    
    for token in tokens:
        # If token is a synonym, add the canonical
        if token in synonym_to_canonical:
            augmented.add(synonym_to_canonical[token])
        # If token is canonical, add all synonyms
        elif token in synonyms:
            augmented.update(synonyms[token])
    
    return list(augmented)

def verify_atleast_one_token(query_tokens, index):
    """Filter documents where at least one of the query tokens is present
    Returns: set of urls
    """
    matching_urls = set()
    for token in query_tokens:
        if token in index:
            matching_urls.update(index[token].keys())
    return matching_urls

def verify_all_tokens(query_tokens, index):
    """Filter documents where all query tokens are present 
    Returns: set of urls
    """
    if not query_tokens:
        return set()
    
    # Start with urls that have the first token
    matching_urls = set(index.get(query_tokens[0], {}).keys())
    
    # Intersect with urls that have each subsequent token
    for token in query_tokens[1:]:
        if token in index:
            matching_urls &= set(index[token].keys())
        else:
            return set() 
    
    return matching_urls

def bm25_score(query_tokens, doc_url, index, total_docs, avg_doc_len, k1=1.5, b=0.75):
    """Calculate BM25 score for a document given query tokens"""
    score = 0.0
    doc_len = 0 
    
    # For simplicity, assume doc_len is sum of term frequencies
    # In practice, you'd store document lengths
    for token in index:
        if doc_url in index[token]:
            doc_len += len(index[token][doc_url])
    
    if doc_len == 0:
        return 0.0
    
    for token in query_tokens:
        if token not in index or doc_url not in index[token]:
            continue
        
        tf = len(index[token][doc_url])  # term frequency
        df = len(index[token])  # document frequency
        
        idf = math.log((total_docs - df + 0.5) / (df + 0.5))
        numerator = tf * (k1 + 1)
        denominator = tf + k1 * (1 - b + b * doc_len / avg_doc_len)
        score += idf * numerator / denominator
    
    return score

def exact_match_score(query_tokens, doc_url, index):
    """Check if query tokens appear consecutively in the document"""
    if not query_tokens or len(query_tokens) < 2:
        return 0
    
    for token in query_tokens:
        if token not in index or doc_url not in index[token]:
            return 0
    
    # Check if positions are consecutive
    positions = []
    for i, token in enumerate(query_tokens):
        pos_list = index[token][doc_url]
        if i == 0:
            positions = [(pos, i) for pos in pos_list]
        else:
            new_positions = []
            for pos, prev_i in positions:
                if pos + 1 in pos_list:
                    new_positions.append((pos + 1, i))
            positions = new_positions
            if not positions:
                return 0
    
    return 1 if positions else 0

def linear_score(query_tokens, doc_url, indexes, synonyms):
    """Linear combination of various scoring features"""
    score = 0
    
    title_index = indexes.get("title_index", {})
    desc_index = indexes.get("description_index", {})
    reviews_index = indexes.get("reviews_index", {})
    brand_index = indexes.get("brand_index", {})
    origin_index = indexes.get("origin_index", {})
    
    # Weights
    w_tf_title = 1
    w_tf_desc = 0.8
    w_position_title = 0.5
    w_position_desc = 0.3
    w_reviews = 0.6
    w_exact_match = 2.0
    w_brand_match = 0.7
    w_origin_match = 0.7
    
    # Term frequency in title
    tf_title = sum(len(title_index.get(token, {}).get(doc_url, [])) for token in query_tokens)
    score += w_tf_title * tf_title
    
    # Term frequency in description
    tf_desc = sum(len(desc_index.get(token, {}).get(doc_url, [])) for token in query_tokens)
    score += w_tf_desc * tf_desc
    
    # Position bonus (earlier positions better)
    min_pos_title = min((pos for token in query_tokens for pos in title_index.get(token, {}).get(doc_url, [float('inf')])), default=float('inf'))
    if min_pos_title < float('inf'):
        score += w_position_title / (min_pos_title + 1)
    
    min_pos_desc = min((pos for token in query_tokens for pos in desc_index.get(token, {}).get(doc_url, [float('inf')])), default=float('inf'))
    if min_pos_desc < float('inf'):
        score += w_position_desc / (min_pos_desc + 1)
    
    # Reviews score
    if doc_url in reviews_index:
        review_data = reviews_index[doc_url]
        score += w_reviews * review_data.get("mean_mark", 0)
    
    # Exact match bonus
    exact_title = exact_match_score(query_tokens, doc_url, title_index)
    exact_desc = exact_match_score(query_tokens, doc_url, desc_index)
    score += w_exact_match * (exact_title + exact_desc)
    
    # Brand match
    for token in query_tokens:
        for brand, urls in brand_index.items():
            if token.lower() in brand.lower() and doc_url in urls:
                score += w_brand_match
                break
    
    # Origin match with synonyms
    for token in query_tokens:
        canonical = None
        for can, syns in synonyms.items():
            if token == can or token in syns:
                canonical = can
                break
        if canonical and doc_url in origin_index.get(canonical, []):
            score += w_origin_match
    
    return score

def load_documents(jsonl_path):
    """Load documents from JSONL file"""
    documents = []
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            documents.append(json.loads(line.strip()))
    return documents

def format_results(documents, urls):
    """Format selected documents as JSON lines"""
    results = []
    url_set = set(urls)
    for doc in documents:
        if doc["url"] in url_set:
            results.append(doc)
    return results

def verify_atleast_one_token_combined(query_tokens, indexes):
    """Check if at least one token appears in any index"""
    all_docs = set()
    for index_name, index in indexes.items():
        for token in query_tokens:
            docs = index.get(token, {})
            all_docs.update(docs.keys())
    return list(all_docs)

def verify_all_tokens_combined(query_tokens, indexes):
    """Check if all tokens appear in any index (allowing different indexes)"""
    if not query_tokens:
        return []
    
    # Start with documents that have the first token
    result_docs = None
    
    for token in query_tokens:
        token_docs = set()
        for index_name, index in indexes.items():
            docs = index.get(token, {})
            token_docs.update(docs.keys())
        
        if result_docs is None:
            result_docs = token_docs
        else:
            result_docs = result_docs.intersection(token_docs)
    
    return list(result_docs)

def linear_score_improved(query_tokens, doc_url, indexes, synonyms):
    """Improved linear combination with better weights and features"""
    score = 0
    
    title_index = indexes.get("title_index", {})
    desc_index = indexes.get("description_index", {})
    reviews_index = indexes.get("reviews_index", {})
    brand_index = indexes.get("brand_index", {})
    origin_index = indexes.get("origin_index", {})
    
    # Adjusted weights based on testing
    w_tf_title = 1.5      # Increased importance for titles
    w_tf_desc = 1.0       # Baseline for descriptions
    w_position_title = 0.8  # Position matters more in titles
    w_position_desc = 0.4  # Less important in descriptions
    w_reviews = 0.5       # Reviews are secondary
    w_exact_match = 3.0   # Exact matches very important
    w_brand_match = 1.2   # Brand matches important
    w_origin_match = 1.0  # Origin matches relevant
    
    # Term frequency in title
    tf_title = sum(len(title_index.get(token, {}).get(doc_url, [])) for token in query_tokens)
    score += w_tf_title * tf_title
    
    # Term frequency in description
    tf_desc = sum(len(desc_index.get(token, {}).get(doc_url, [])) for token in query_tokens)
    score += w_tf_desc * tf_desc
    
    # Position bonus (earlier positions better)
    min_pos_title = min((pos for token in query_tokens for pos in title_index.get(token, {}).get(doc_url, [float('inf')])), default=float('inf'))
    if min_pos_title < float('inf'):
        score += w_position_title / (min_pos_title + 1)
    
    min_pos_desc = min((pos for token in query_tokens for pos in desc_index.get(token, {}).get(doc_url, [float('inf')])), default=float('inf'))
    if min_pos_desc < float('inf'):
        score += w_position_desc / (min_pos_desc + 1)
    
    # Reviews frequency
    tf_reviews = sum(len(reviews_index.get(token, {}).get(doc_url, [])) for token in query_tokens)
    score += w_reviews * tf_reviews
    
    # Exact match bonus
    exact = exact_match_score(query_tokens, doc_url, desc_index)
    score += w_exact_match * exact
    
    # Brand match bonus
    brand_match = any(token in brand_index and doc_url in brand_index[token] for token in query_tokens)
    if brand_match:
        score += w_brand_match
    
    # Origin match bonus
    origin_match = any(token in origin_index and doc_url in origin_index[token] for token in query_tokens)
    if origin_match:
        score += w_origin_match
    
    return score

def run_tests(indexes, documents, synonyms):
    """Run a comprehensive test suite for the search system"""
    test_queries = [
        # Basic text queries
        "chocolate",
        "leather sneakers",
        "cat beanie",
        
        # Multi-term queries
        "chocolate candy",
        "light up sneakers",
        
        # Origin queries (with synonyms)
        "america",  # Should expand to usa
        "france",   # Should expand to fr
        
        # Brand queries
        "ChocoDelight",
        "TimelessFootwear",
        
        # Mixed queries
        "italian leather",
        "usa chocolate",
        
        # Non-existent terms
        "nonexistent product",
        "",
    ]
    
    results = {}
    
    for query in test_queries:
        print(f"\n=== Testing query: '{query}' ===")
        
        # Process query
        tokens = process_query(query)
        augmented = augment_query_with_synonyms(tokens, synonyms)
        
        print(f"Tokens: {tokens}")
        print(f"Augmented: {augmented}")
        
        # Test filtering on description index
        desc_index = indexes.get("description_index", {})
        or_results = verify_atleast_one_token(augmented, desc_index)
        and_results = verify_all_tokens(augmented, desc_index)
        
        print(f"OR results: {len(or_results)} documents")
        print(f"AND results: {len(and_results)} documents")
        
        # Test scoring on top results
        scored_results = []
        for url in or_results:
            bm25 = bm25_score(augmented, url, desc_index, len(documents), 50)
            exact = exact_match_score(augmented, url, desc_index)
            linear = linear_score(augmented, url, indexes, synonyms)
            scored_results.append({
                'url': url,
                'bm25': bm25,
                'exact': exact,
                'linear': linear
            })
        
        # Sort by linear score (our main scoring)
        scored_results.sort(key=lambda x: x['linear'], reverse=True)
        
        print("Top 3 results by linear score:")
        for i, result in enumerate(scored_results[:3]):
            print(f"  {i+1}. {result['url'][:50]}... | BM25: {result['bm25']:.3f} | Exact: {result['exact']} | Linear: {result['linear']:.3f}")
        
        results[query] = {
            'tokens': tokens,
            'augmented': augmented,
            'or_count': len(or_results),
            'and_count': len(and_results),
            'top_results': scored_results[:5]
        }
    
    return results

def analyze_results(test_results):
    """Analyze test results and provide insights"""
   
    print("ANALYSIS OF TEST RESULTS")
   
    
    # Summary statistics
    total_queries = len(test_results)
    queries_with_results = sum(1 for r in test_results.values() if r['or_count'] > 0)
    avg_results_per_query = sum(r['or_count'] for r in test_results.values()) / total_queries
    
    print(f"Total queries tested: {total_queries}")
    print(f"Queries with results: {queries_with_results} ({queries_with_results/total_queries*100:.1f}%)")
    print(f"Average results per query: {avg_results_per_query:.1f}")
    
    # Query type analysis
    print("\nQuery Type Analysis:")
    for query, result in test_results.items():
        if result['or_count'] == 0:
            print(f"  '{query}' -> NO RESULTS")
        elif result['and_count'] == 0:
            print(f"  '{query}' -> {result['or_count']} OR results, 0 AND results")
        else:
            ratio = result['or_count'] / result['and_count'] if result['and_count'] > 0 else float('inf')
            print(f"  '{query}' -> {result['or_count']} OR, {result['and_count']} AND (ratio: {ratio:.1f})")
    
    # Scoring analysis
    print("\nScoring Analysis:")
    bm25_scores = []
    linear_scores = []
    exact_matches = 0
    
    for result in test_results.values():
        for doc_result in result['top_results']:
            bm25_scores.append(doc_result['bm25'])
            linear_scores.append(doc_result['linear'])
            if doc_result['exact'] > 0:
                exact_matches += 1
    
    if bm25_scores:
        print(f"BM25 scores - Min: {min(bm25_scores):.3f}, Max: {max(bm25_scores):.3f}, Avg: {sum(bm25_scores)/len(bm25_scores):.3f}")
    if linear_scores:
        print(f"Linear scores - Min: {min(linear_scores):.3f}, Max: {max(linear_scores):.3f}, Avg: {sum(linear_scores)/len(linear_scores):.3f}")
    print(f"Exact matches found: {exact_matches}")

if __name__ == "__main__":
    # Define paths
    input_dir = Path(__file__).resolve().parent.parent / "input"
    tp2_input = Path(__file__).resolve().parent.parent.parent / "TP2" / "Input" / "products.jsonl"
    synonyms_path = input_dir / "origin_synonyms.json"
    
    # Load indexes
    indexes = load_indexes(input_dir)
    print(f"Loaded {len(indexes)} indexes")
    
    # Load synonyms
    synonyms = load_synonyms(synonyms_path)
    print(f"Loaded synonyms for {len(synonyms)} origins")
    
    # Load original documents
    documents = load_documents(str(tp2_input))
    print(f"Loaded {len(documents)} documents")
    
    # Run comprehensive tests
    test_results = run_tests(indexes, documents, synonyms)
    
    # Analyze results
    analyze_results(test_results)
    
    # Save test results
    output_dir = Path(__file__).resolve().parent.parent / "Output"
    output_dir.mkdir(exist_ok=True)
    test_output = output_dir / "test_results.json"
    
    with open(test_output, "w", encoding="utf-8") as f:
        json.dump(test_results, f, ensure_ascii=False, indent=2)
    
    print(f"\nTest results saved to {test_output}")
