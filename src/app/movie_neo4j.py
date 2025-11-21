import requests
from neo4j import GraphDatabase
import time
from datetime import datetime
from dotenv import load_dotenv
import os

load_dotenv()

OMDB_API_KEY = os.environ['OMDB_API_KEY']
OMDB_BASE_URL = os.environ['OMDB_BASE_URL']

# Configuration Neo4j
NEO4J_URI = os.environ['NEO4J_URI']
NEO4J_USER = os.environ['NEO4J_USER']
NEO4J_PASSWORD = os.environ['NEO4J_PASSWORD']

class MovieImporter:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
    
    def close(self):
        self.driver.close()
    
    def create_movie(self, movie_data):
        """Crée un nœud Movie dans Neo4j avec toutes les informations"""
        with self.driver.session() as session:
            session.execute_write(self._create_movie_node, movie_data)
    
    @staticmethod
    def _create_movie_node(tx, movie_data):
        query = """
        MERGE (m:Movie {imdbID: $imdbID})
        SET m.title = $title,
            m.year = $year,
            m.type = $type,
            m.plot = $plot,
            m.poster = $poster,
            m.director = $director,
            m.actors = $actors,
            m.genre = $genre,
            m.runtime = $runtime,
            m.imdbRating = $imdbRating,
            m.released = $released,
            m.updated_at = datetime()
    
        WITH m
    
        // --- Réalisateurs ---
        UNWIND split(m.director, ", ") AS directorName
        MERGE (d:Director {name: directorName})
        MERGE (m)-[:DIRECTED_BY]->(d)
    
        // --- Acteurs ---
        WITH m
        UNWIND split(m.actors, ", ") AS actorName
        MERGE (a:Actor {name: actorName})
        MERGE (a)-[:ACTED_IN]->(m)
    
        // --- Genres ---
        WITH m
        UNWIND split(m.genre, ", ") AS genreName
        MERGE (g:Genre {name: genreName})
        MERGE (m)-[:HAS_GENRE]->(g)
        """
        tx.run(query, **movie_data)

def search_movies_by_year(year, api_key):
    """Recherche des films par année"""
    movies = []
    page = 1
    
    while True:
        params = {
            'apikey': api_key,
            's': 'movie',  # Recherche générique
            'y': year,
            'type': 'movie',
            'page': page
        }
        
        response = requests.get(OMDB_BASE_URL, params=params)
        
        if response.status_code == 401:
            print(f"\n❌ Erreur 401: Clé API invalide ou non activée")
            print("   Vérifiez votre email pour activer la clé")
            return []
        
        if response.status_code != 200:
            print(f"Erreur API: {response.status_code}")
            break
        
        data = response.json()
        
        if data.get('Response') == 'False':
            break
        
        search_results = data.get('Search', [])
        if not search_results:
            break
        
        movies.extend(search_results)
        
        # Vérifier s'il y a plus de pages
        total_results = int(data.get('totalResults', 0))
        if len(movies) >= total_results:
            break
        
        page += 1
        time.sleep(0.2)  # Respecter les limites de l'API
    
    return movies

def get_movie_details(imdb_id, api_key):
    """Récupère les détails complets d'un film"""
    params = {
        'apikey': api_key,
        'i': imdb_id,
        'plot': 'full',
        'r': 'json'
    }
    
    response = requests.get(OMDB_BASE_URL, params=params)
    
    if response.status_code == 200:
        data = response.json()
        if data.get('Response') == 'True':
            return data
    
    return None

def main():
    print("🎬 Importation de films OMDb vers Neo4j")
    print("=" * 50)
    
    # Vérifier la clé API
    if OMDB_API_KEY == 'votre_cle_api_ici':
        print("\n❌ ERREUR: Vous devez configurer votre clé API OMDb!")
        print("\n📝 Pour obtenir une clé API gratuite:")
        print("   1. Visitez: http://www.omdbapi.com/apikey.aspx")
        print("   2. Choisissez le plan FREE (1000 requêtes/jour)")
        print("   3. Vérifiez votre email pour activer la clé")
        print("   4. Configurez la clé dans le script ou via variable d'environnement:")
        print("      export OMDB_API_KEY='votre_cle'")
        return
    
    print(f"\n🔑 Clé API: {OMDB_API_KEY[:8]}..." if len(OMDB_API_KEY) > 8 else f"\n🔑 Clé API: {OMDB_API_KEY}")
    
    # Initialiser la connexion Neo4j
    importer = MovieImporter(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    
    try:
        movies_collected = []
        current_year = datetime.now().year
        
        # Collecter des films des dernières années jusqu'à avoir 1000
        print("\n📥 Collecte des films récents...")
        
        for year in range(current_year, current_year - 10, -1):
            if len(movies_collected) >= 1000:
                break
            
            print(f"\nRecherche des films de {year}...")
            year_movies = search_movies_by_year(year, OMDB_API_KEY)
            movies_collected.extend(year_movies)
            print(f"  ✓ {len(year_movies)} films trouvés")
            time.sleep(0.3)
        
        # Limiter à 1000 films
        movies_to_import = movies_collected[:1000]
        print(f"\n📊 Total de films à importer: {len(movies_to_import)}")
        
        # Importer chaque film avec ses détails complets
        print("\n💾 Import dans Neo4j...")
        success_count = 0
        
        for idx, movie in enumerate(movies_to_import, 1):
            imdb_id = movie.get('imdbID')
            
            if not imdb_id:
                continue
            
            # Récupérer les détails complets
            details = get_movie_details(imdb_id, OMDB_API_KEY)
            
            if details:
                movie_data = {
                    'imdbID': details.get('imdbID', ''),
                    'title': details.get('Title', ''),
                    'year': details.get('Year', ''),
                    'type': details.get('Type', ''),
                    'plot': details.get('Plot', ''),
                    'poster': details.get('Poster', ''),
                    'director': details.get('Director', ''),
                    'actors': details.get('Actors', ''),
                    'genre': details.get('Genre', ''),
                    'runtime': details.get('Runtime', ''),
                    'imdbRating': details.get('imdbRating', ''),
                    'released': details.get('Released', '')
                }
                
                importer.create_movie(movie_data)
                success_count += 1
                
                if idx % 10 == 0:
                    print(f"  ✓ {idx}/{len(movies_to_import)} films importés")
            
            # Respecter les limites de l'API (1000 requêtes/jour gratuit)
            time.sleep(0.3)
        
        print(f"\n✅ Import terminé: {success_count} films importés avec succès!")
        
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
    
    finally:
        importer.close()
        print("\n🔌 Connexion Neo4j fermée")

if __name__ == "__main__":
    main()