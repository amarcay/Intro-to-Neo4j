import requests
from neo4j import GraphDatabase
import time
import os
from dotenv import load_dotenv


load_dotenv()

# Configuration
TMDB_API_KEY = os.environ['TMDB_API_KEY']
TMDB_BASE_URL = "https://api.themoviedb.org/3"

# Configuration Neo4j
NEO4J_URI = os.environ['NEO4J_URI']
NEO4J_USER = os.environ['NEO4J_USER']
NEO4J_PASSWORD = os.environ['NEO4J_PASSWORD']

class TMDBNeo4jImporter:
    def __init__(self, uri, user, password, tmdb_token):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self.headers = {
            "accept": "application/json",
            "Authorization": f"Bearer {tmdb_token}"
        }
    
    def close(self):
        self.driver.close()
    
    def clear_database(self):
        """Supprime toutes les données de la base (optionnel)"""
        with self.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
            print("   ✓ Base de données nettoyée")
    
    def drop_constraints(self):
        """Supprime les contraintes qui pourraient causer des conflits"""
        with self.driver.session() as session:
            try:
                # Lister toutes les contraintes
                result = session.run("SHOW CONSTRAINTS")
                constraints = list(result)
                
                if not constraints:
                    print("   ℹ️  Aucune contrainte trouvée")
                    return
                
                print(f"   ℹ️  {len(constraints)} contrainte(s) trouvée(s)")
                
                deleted_count = 0
                # Supprimer toutes les contraintes
                for record in constraints:
                    constraint_name = record.get("name", "")
                    
                    if constraint_name:
                        try:
                            session.run(f"DROP CONSTRAINT `{constraint_name}` IF EXISTS")
                            print(f"   ✓ Contrainte supprimée: {constraint_name}")
                            deleted_count += 1
                        except Exception as e:
                            print(f"   ⚠️  Impossible de supprimer {constraint_name}: {e}")
                
                if deleted_count > 0:
                    print(f"   ✅ {deleted_count} contrainte(s) supprimée(s)")
                            
            except Exception as e:
                print(f"   ⚠️  Erreur: {e}")
    
    # ========== GENRES ==========
    def fetch_genres(self):
        """Récupère tous les genres de films"""
        url = f"{TMDB_BASE_URL}/genre/movie/list?language=fr"
        response = requests.get(url, headers=self.headers)
        
        if response.status_code == 200:
            return response.json().get('genres', [])
        return []
    
    def create_genres(self, genres):
        """Crée les nœuds Genre dans Neo4j"""
        with self.driver.session() as session:
            for genre in genres:
                session.execute_write(self._create_genre_node, genre)
    
    @staticmethod
    def _create_genre_node(tx, genre):
        # Utiliser MERGE sur 'id' au lieu de 'name' pour éviter les conflits
        query = """
        MERGE (g:Genre {id: $id})
        SET g.name = $name
        RETURN g
        """
        tx.run(query, id=genre['id'], name=genre['name'])
    
    # ========== MOVIES ==========
    def fetch_popular_movies(self, max_pages=50):
        """Récupère les films populaires (environ 1000 films)"""
        all_movies = []
        
        for page in range(1, max_pages + 1):
            url = f"{TMDB_BASE_URL}/discover/movie"
            params = {
                'language': 'fr-FR',
                'page': page,
                'sort_by': 'popularity.desc',
                'include_adult': 'false',
                'include_video': 'false'
            }
            
            response = requests.get(url, headers=self.headers, params=params)
            
            if response.status_code == 200:
                data = response.json()
                movies = data.get('results', [])
                all_movies.extend(movies)
                
                print(f"  Page {page}/{max_pages}: {len(movies)} films récupérés")
                
                if page >= data.get('total_pages', 0):
                    break
            else:
                print(f"  Erreur page {page}: {response.status_code}")
                break
            
            time.sleep(0.25)  # Respecter les limites de l'API
        
        return all_movies
    
    def fetch_upcoming_movies(self, max_pages=5):
        """Récupère les films à venir"""
        all_movies = []
        
        for page in range(1, max_pages + 1):
            url = f"{TMDB_BASE_URL}/movie/upcoming"
            params = {
                'language': 'fr-FR',
                'page': page
            }
            
            response = requests.get(url, headers=self.headers, params=params)
            
            if response.status_code == 200:
                data = response.json()
                movies = data.get('results', [])
                all_movies.extend(movies)
                
                print(f"  Page {page}/{max_pages}: {len(movies)} films à venir")
                
                if page >= data.get('total_pages', 0):
                    break
            else:
                break
            
            time.sleep(0.25)
        
        return all_movies
    
    def fetch_movie_details(self, movie_id):
        """Récupère les détails complets d'un film"""
        url = f"{TMDB_BASE_URL}/movie/{movie_id}"
        params = {
            'language': 'fr-FR',
            'append_to_response': 'credits,keywords'
        }
        
        response = requests.get(url, headers=self.headers, params=params)
        
        if response.status_code == 200:
            return response.json()
        return None
    
    def create_movie_with_relations(self, movie_data):
        """Crée un film avec toutes ses relations (genres, acteurs, réalisateur)"""
        with self.driver.session() as session:
            session.execute_write(self._create_movie_node, movie_data)
    
    @staticmethod
    def _create_movie_node(tx, movie):
        # Créer le nœud Movie
        query_movie = """
        MERGE (m:Movie {id: $id})
        SET m.title = $title,
            m.original_title = $original_title,
            m.overview = $overview,
            m.release_date = $release_date,
            m.popularity = $popularity,
            m.vote_average = $vote_average,
            m.vote_count = $vote_count,
            m.poster_path = $poster_path,
            m.backdrop_path = $backdrop_path,
            m.runtime = $runtime,
            m.budget = $budget,
            m.revenue = $revenue,
            m.tagline = $tagline,
            m.status = $status
        """
        
        tx.run(query_movie,
            id=movie.get('id'),
            title=movie.get('title', ''),
            original_title=movie.get('original_title', ''),
            overview=movie.get('overview', ''),
            release_date=movie.get('release_date', ''),
            popularity=movie.get('popularity', 0),
            vote_average=movie.get('vote_average', 0),
            vote_count=movie.get('vote_count', 0),
            poster_path=movie.get('poster_path', ''),
            backdrop_path=movie.get('backdrop_path', ''),
            runtime=movie.get('runtime', 0),
            budget=movie.get('budget', 0),
            revenue=movie.get('revenue', 0),
            tagline=movie.get('tagline', ''),
            status=movie.get('status', '')
        )
        
        # Créer les relations avec les genres
        for genre in movie.get('genres', []):
            query_genre = """
            MATCH (m:Movie {id: $movie_id})
            MERGE (g:Genre {id: $genre_id})
            MERGE (m)-[:HAS_GENRE]->(g)
            """
            tx.run(query_genre, movie_id=movie.get('id'), genre_id=genre['id'])
        
        # Créer les acteurs et relations
        credits = movie.get('credits', {})
        for actor in credits.get('cast', [])[:10]:  # Top 10 acteurs
            query_actor = """
            MATCH (m:Movie {id: $movie_id})
            MERGE (a:Actor {id: $actor_id})
            SET a.name = $name,
                a.profile_path = $profile_path
            MERGE (a)-[r:ACTED_IN]->(m)
            SET r.character = $character,
                r.order = $order
            """
            tx.run(query_actor,
                movie_id=movie.get('id'),
                actor_id=actor.get('id'),
                name=actor.get('name', ''),
                profile_path=actor.get('profile_path', ''),
                character=actor.get('character', ''),
                order=actor.get('order', 999)
            )
        
        # Créer le réalisateur
        for crew in credits.get('crew', []):
            if crew.get('job') == 'Director':
                query_director = """
                MATCH (m:Movie {id: $movie_id})
                MERGE (d:Director {id: $director_id})
                SET d.name = $name,
                    d.profile_path = $profile_path
                MERGE (d)-[:DIRECTED]->(m)
                """
                tx.run(query_director,
                    movie_id=movie.get('id'),
                    director_id=crew.get('id'),
                    name=crew.get('name', ''),
                    profile_path=crew.get('profile_path', '')
                )
    



def main():
    print("🎬 Import TMDB vers Neo4j")
    print("=" * 50)
    
    # Vérifier le token TMDB
    if TMDB_API_KEY == 'votre_bearer_token_ici':
        print("\n❌ ERREUR: Configurez votre token TMDB!")
        print("\n📝 Pour obtenir un token:")
        print("   1. Créez un compte sur https://www.themoviedb.org/")
        print("   2. Allez dans Settings > API")
        print("   3. Copiez votre 'API Read Access Token' (Bearer)")
        print("   4. Configurez: export TMDB_API_KEY='votre_token'")
        return
    
    print(f"\n🔑 Token TMDB: {TMDB_API_KEY[:20]}...")
    
    # Connexion Neo4j
    print(f"\n🔌 Connexion à Neo4j: {NEO4J_URI}")
    
    try:
        importer = TMDBNeo4jImporter(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, TMDB_API_KEY)
        print("   ✓ Connexion réussie!")
    except Exception as e:
        print(f"\n❌ Erreur Neo4j: {e}")
        return
    
    try:
        # Demander si on veut nettoyer la base
        print("\n⚠️  Des données existent déjà dans Neo4j.")
        print("   Options:")
        print("   1. Nettoyer la base et réimporter (DELETE ALL)")
        print("   2. Continuer (les doublons seront ignorés)")
        
        choice = input("\nVotre choix (1 ou 2) [2]: ").strip() or "2"
        
        if choice == "1":
                print("\n🗑️  Suppression des contraintes existantes...")
                importer.drop_constraints()

                print("\n🗑️  Nettoyage de la base...")
                importer.clear_database()
        else:
            print("\n➡️  Les données existantes seront préservées")
    except Exception as e:
        print(f"\n❌ Erreur lors du choix de nettoyage: {e}")
        return
    
    try:
        # 1. Importer les genres
        print("\n📂 Import des genres...")
        genres = importer.fetch_genres()
        if genres:
            importer.create_genres(genres)
            print(f"   ✓ {len(genres)} genres importés")
        
        # 2. Importer les films populaires
        print("\n🎥 Import des films populaires (1000 films)...")
        popular_movies = importer.fetch_popular_movies(max_pages=50)
        print(f"   ✓ {len(popular_movies)} films récupérés")
        
        # 3. Importer les films à venir
        print("\n🗓️  Import des films à venir...")
        upcoming_movies = importer.fetch_upcoming_movies(max_pages=5)
        print(f"   ✓ {len(upcoming_movies)} films à venir récupérés")
        
        # Combiner tous les films
        all_movies = popular_movies + upcoming_movies
        
        # 4. Importer les détails complets de chaque film
        print(f"\n💾 Import des détails dans Neo4j ({len(all_movies)} films)...")
        
        for idx, movie in enumerate(all_movies, 1):
            movie_id = movie.get('id')
            
            # Récupérer les détails complets
            details = importer.fetch_movie_details(movie_id)
            
            if details:
                importer.create_movie_with_relations(details)
                
                if idx % 50 == 0:
                    print(f"   ✓ {idx}/{len(all_movies)} films importés")
            
            time.sleep(0.25)  # Respecter les limites de l'API
        
        print(f"\n✅ Import terminé: {len(all_movies)} films importés!")
        
        print("\n📊 Statistiques:")
        print(f"   - {len(genres)} genres")
        print(f"   - {len(popular_movies)} films populaires")
        print(f"   - {len(upcoming_movies)} films à venir")
        print(f"   - Total: {len(all_movies)} films avec détails complets")
        
        print("\n✨ Base de données Neo4j prête!")
        
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        importer.close()
        print("\n🔌 Connexion fermée")


if __name__ == "__main__":
    main()