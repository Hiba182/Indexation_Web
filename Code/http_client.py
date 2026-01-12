import requests
import time
import urllib.robotparser
import urllib.parse
from bs4 import BeautifulSoup
from collections import deque
import heapq
import json
import os
class HttpClient (object):
    def __init__(self, url, timeout=10):
        self.url = url
        self.timeout = timeout
        self.delay = 0.5 
        self.headers = {'User-Agent': 'PoliteBot/1.0'}
        self.to_visit = []  # pour la priorité
        self.pending_urls = set()  
        self.visited = set()  
        parsed = urllib.parse.urlparse(url)
        self.allowed_domain = parsed.netloc
        self.add_url(url)   

    def get(self ,timeout=5):
        response = requests.get(self.url, timeout=timeout, headers=self.headers)
        time.sleep(self.delay)
        return response.text

    def post(self, data, timeout=5):
        response = requests.post(self.url, data=data, timeout=timeout, headers=self.headers)
        time.sleep(self.delay)
        return response.text
    def put(self, data, timeout=5):
        response = requests.put(self.url, data=data, timeout=timeout, headers=self.headers)
        time.sleep(self.delay)
        return response.text
    def delete(self, timeout=5):
        response = requests.delete(self.url, timeout=timeout, headers=self.headers)
        time.sleep(self.delay)
        return response.text

    def can_parse(self, url=None):
        """
        Vérifie si le crawler a le droit de parser la page selon robots.txt.
        Retourne True si autorisé, False sinon.
        """
        target_url = url or self.url
        parsed = urllib.parse.urlparse(target_url)
        domain = parsed.netloc
        if not domain:
            return False  
        
        robots_url = f"{parsed.scheme}://{domain}/robots.txt"
        rp = urllib.robotparser.RobotFileParser()
        rp.set_url(robots_url)
        try:
            rp.read()
            return rp.can_fetch(self.headers['User-Agent'], target_url)
        except Exception:
            # Si robots.txt n'est pas accessible, on assume que c'est autorisé
            return True
    def parse_html(self, html):
        """
        Méthode de parsing HTML basique.
        Retourne le HTML formaté.
        """
        soup = BeautifulSoup(html, 'html.parser')
        return soup

    def extract_title(self, html=None):
        """
        Extrait le titre de la page HTML.
        Si html n'est pas fourni, récupère le contenu via GET.
        Retourne le titre ou None si non trouvé.
        """
        if html is None:
            html = self.get()
        soup = self.parse_html(html)
        title_tag = soup.find('title')
        return title_tag.string.strip() if title_tag else None

    def extract_first_paragraph(self, html=None):
        """
        Extrait le premier paragraphe de la page HTML.
        Si html n'est pas fourni, récupère le contenu via GET.
        Retourne le texte du paragraphe ou None si non trouvé.
        """
        if html is None:
            html = self.get()
        soup = self.parse_html(html)
        p_tag = soup.find('p')
        return p_tag.get_text().strip() if p_tag else None

    def extract_links(self, html=None):
        """
        Extrait tous les liens de la page HTML.
        Si html n'est pas fourni, récupère le contenu via GET.
        Retourne une liste de dictionnaires avec 'text' et 'href'.
        """
        if html is None:
            html = self.get()
        soup = self.parse_html(html)
        links = []
        for a in soup.find_all('a', href=True):
            links.append({
                'text': a.get_text().strip(),
                'href': a['href']
            })
        return links

    def extract_description(self, html=None):
        """
        Extrait la description de la page.
        """
        if html is None:
            html = self.get()
        soup = BeautifulSoup(html, 'html.parser')
    
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc:
            return meta_desc.get('content', '')

        p = soup.find('p')
        return p.get_text().strip() if p else ''

    def extract_product_features(self, html=None):
        """
        Extrait les caractéristiques du produit (d'un dl ou table).
        """
        if html is None:
            html = self.get()
        soup = BeautifulSoup(html, 'html.parser')
        features = {}
        
        dl = soup.find('dl')
        if dl:
            dts = dl.find_all('dt')
            dds = dl.find_all('dd')
            for dt, dd in zip(dts, dds):
                features[dt.get_text().strip()] = dd.get_text().strip()
        return features

    def extract_product_reviews(self, html=None):
        """
        Extrait les avis produits.
        """
        if html is None:
            html = self.get()
        soup = BeautifulSoup(html, 'html.parser')
        reviews = []
        # Supposer des divs avec classe 'review'
        review_divs = soup.find_all('div', class_='review')
        for div in review_divs:
            review = {}
            date = div.find('time') or div.find(attrs={'data-date': True})
            if date:
                review['date'] = date.get('datetime') or date.get_text().strip()
            rating = div.find(attrs={'data-rating': True}) or div.find(class_='rating')
            if rating:
                review['rating'] = int(rating.get('data-rating', 0)) or 5  # default
            text = div.find('p') or div
            review['text'] = text.get_text().strip()
            id_elem = div.get('id')
            if id_elem:
                review['id'] = id_elem
            if review:
                reviews.append(review)
        return reviews

    def extract_page_data(self, url):
        """
        Extrait toutes les données d'une page.
        """
        self.url = url
        title = self.extract_title()
        description = self.extract_description()
        features = self.extract_product_features()
        links_data = self.extract_links()
        links = [urllib.parse.urljoin(url, link['href']) for link in links_data]
        reviews = self.extract_product_reviews()
        return {
            "url": url,
            "title": title,
            "description": description,
            "product_features": features,
            "links": links,
            "product_reviews": reviews
        }

    def add_url(self, url):
        """
        Ajoute une URL à la file d'attente avec priorité si elle n'a pas encore été visitée.
        Priorité 1 pour les URLs contenant 'product', 2 sinon.
        Seules les URLs du même domaine sont ajoutées.
        """
        parsed = urllib.parse.urlparse(url)
        if parsed.netloc != self.allowed_domain:
            return  
        if url not in self.visited and url not in self.pending_urls:
            priority = 1 if 'product' in url.lower() else 2
            heapq.heappush(self.to_visit, (priority, url))
            self.pending_urls.add(url)

    def get_next_url(self):
        """
        Récupère et marque comme visitée la prochaine URL dans la file (priorité haute d'abord).
        Retourne l'URL ou None si la file est vide.
        """
        if self.to_visit:
            priority, url = heapq.heappop(self.to_visit)
            self.pending_urls.remove(url)
            self.visited.add(url)
            return url
        return None

    def crawl(self, max_pages=50):
        """
        Effectue le crawling jusqu'à max_pages pages ou jusqu'à ce que la file soit vide.
        Extrait les liens de chaque page et les ajoute à la file.
        Collecte les données de chaque page.
        """
        self.results = []
        count = 0
        while len(self.visited) < max_pages and self.to_visit:
            current_url = self.get_next_url()
            if current_url:
                count += 1
                print(f"Traitement {count}: {current_url} (Visitées: {len(self.visited)})")
                self.url = current_url
                if self.can_parse(current_url):
                    try:
                        data = self.extract_page_data(current_url)
                        self.results.append(data)
                        links_data = data['links']  # already absolute
                        for link in links_data:
                            self.add_url(link)
                    except requests.exceptions.Timeout:
                        print(f"Timeout pour {current_url}, tentative de retry...")
                        try:
                            data = self.extract_page_data(current_url)
                            self.results.append(data)
                            links_data = data['links']
                            for link in links_data:
                                self.add_url(link)
                        except Exception as e2:
                            print(f"Échec retry pour {current_url}: {e2}")
                    except Exception as e:
                        print(f"Erreur lors du traitement de {current_url}: {e}")
                else:
                    print(f"Parsing non autorisé pour {current_url}")

if __name__ == "__main__":
    url = "https://web-scraping.dev/products"
    client = HttpClient(url)
    print("Début du crawling...")
    client.crawl(max_pages=50)
    print(f"Crawling terminé. Pages visitées : {len(client.visited)}")
    print(f"URLs restantes dans la file : {len(client.to_visit)}")
    
    # Créer le dossier output s'il n'existe pas
    os.makedirs('output', exist_ok=True)
    output_file = 'output/results.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        for result in client.results:
            json.dump(result, f, ensure_ascii=False)
            f.write('\n')
    print(f"Résultats sauvegardés dans {output_file}")