# Indexation Web - TP2

Système d'indexation inversée pour produits web-scrapés avec génération de multiples index pour recherche efficace.

## 1. Structure des Index

### Fichiers Générés
- `title_index.json` : Index des titres 
- `description_index.json` : Index des descriptions 
- `reviews_index.json` : Statistiques reviews 
- `brand_index.json` : Index marques 
- `origin_index.json` : Index origines 
- `other_features_index.json` : Index features 


## 2. Choix Techniques

### Lecture des Données
- **Format JSONL** : Lu ligne par ligne pour limiter l'impact des erreurs
- **Parsing indépendant** : Chaque ligne parsée séparément
- **Gestion d'erreurs** : Robustesse face aux erreurs de format individuelles

### Traitement des URLs
- **Extraction d'identifiant** : Numéro après le TLD pour identifier le produit
- **Gestion des variantes** : Support des variantes de produits dans l'URL
- **urllib.parse** : Utilisation pour l'analyse structurée des URLs

### Prétraitement Textuel
#### Tokenisation
- **Méthode** : Simple séparation par espaces
- **Choix délibéré** : Respecte les consignes du TP, reste explicite
- **Limites assumées** : Pas de stemming/avancé pour la simplicité

#### Normalisation
- **Casse** : Conversion systématique en minuscules
- **Ponctuation** : Suppression complète avec `string.punctuation`
- **Stopwords** : Liste minimale anglais
## 3. Features Supplémentaires Implémentées

### 23 Types de Features Indexés

#### Matériau et Composition
- **material** : "premium quality chocolate", "breathable fabric upper", "premium genuine leather"
- **caffeine_content** : "contains 100mg of caffeine per serving"
- **sugar_content** : "no added sugars"

#### Dimensions et Taille
- **sizes** : "available in small, medium, and large boxes"
- **fit** : "true to size"

#### Design et Esthétique
- **colors** : "available in a variety of colors including grey, dark grey, pink, and sand"
- **design** : "classic, sleek design", "unique cat ear design"
- **container** : "comes in a distinctive, reusable potion-like bottle"

#### Fonctionnalités
- **comfort** : "comfortable footbed", "cushioned footbed for added comfort"
- **durability** : "highly durable for active play"
- **safety** : "tested for safety and durability"
- **traction** : "durable rubber outsole for excellent grip"
- **light** : "led lights in the outsole"

#### Usage et Destination
- **purpose** : "ideal for gifting or self-indulgence", "aimed at enhancing gaming performance"
- **season** : "perfect for fall and winter wear"
- **versatility** : "perfect for both formal events and casual outings"

#### Entretien et Fermeture
- **care_instructions** : "store in a cool, dry place", "machine washable with cold water"
- **closure** : "adjustable buckle closure"
- **heel** : "sturdy high heel"

#### Saveurs et Variétés
- **flavors** : "available in orange and cherry flavors"



