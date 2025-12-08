from langchain_core.tools import tool
from vector_store import get_retriever

@tool(response_format="content_and_artifact")
def retrieve_movies(query: str, genre: str = None, min_rating: float = None, k: int = 10):
    """
    Récupère des films pertinents via Neo4jVector avec recherche sémantique.
    
    Args:
        query: Description du type de film recherché (ex: "film d'action avec des combats")
        genre: Genre spécifique à filtrer (optionnel, ex: "Action", "Drama")
        min_rating: Note minimale souhaitée (optionnel, ex: 7.0)
        k: Nombre de résultats à récupérer (défaut: 10)
    
    Returns:
        Une chaîne formatée avec les films trouvés et leurs métadonnées.
    """
    try:
        retriever = get_retriever()
        
        if retriever is None:
            return "❌ Erreur: Le retriever n'a pas pu être initialisé.", []
        
        # Construction des filtres pour Neo4jVector
        filters = {}
        
        if genre:
            filters["all_genres"] = {"$like": genre}
        
        if min_rating:
            filters["rating"] = {"$gte": min_rating}
        
        # Recherche avec filtres si nécessaire
        if filters:
            results = retriever.similarity_search(
                query,
                k=k * 2,  # Récupérer plus pour compenser le filtrage
                filter=filters
            )
        else:
            results = retriever.similarity_search(query, k=k)
        
        if not results:
            filter_info = []
            if genre:
                filter_info.append(f"genre: {genre}")
            if min_rating:
                filter_info.append(f"note min: {min_rating}")
            
            filter_str = f" ({', '.join(filter_info)})" if filter_info else ""
            return f"❌ Aucun film trouvé pour cette recherche{filter_str}.", []
        
        # Limiter aux k premiers résultats
        results = results[:k]
        
        formatted_movies = []
        for doc in results:
            # Extraction du synopsis depuis page_content
            content_parts = doc.page_content.split("\n\n")
            overview = ""
            for part in content_parts:
                if not part.startswith("Titre :") and \
                   not part.startswith("Film réalisé par") and \
                   not part.startswith("Acteurs :") and \
                   not part.startswith("Genres :") and \
                   len(part) > 50:
                    overview = part
                    break
            
            movie_info = {
                "title": doc.metadata.get("title"),
                "overview": overview[:300] if overview else "Synopsis non disponible",
                "director": doc.metadata.get("director"),
                "actors": doc.metadata.get("main_actors"),
                "genres": doc.metadata.get("all_genres"),
                "rating": doc.metadata.get("rating"),
                "runtime": doc.metadata.get("runtime"),
                "release_date": doc.metadata.get("year", "")
            }
            formatted_movies.append(movie_info)
        
        # Sérialisation pour l'affichage
        serialized = "\n\n".join([
            f"🎬 {movie['title']} ({movie['release_date']})\n"
            f"⭐ Note: {movie['rating']}/10 | ⏱️ Durée: {movie['runtime']} min\n"
            f"🎪 Genres: {movie['genres']}\n"
            f"🎭 Réalisateur: {movie['director']}\n"
            f"👥 Acteurs: {movie['actors']}\n"
            f"📖 Résumé: {movie['overview']}"
            for movie in formatted_movies
        ])
        
        return serialized, formatted_movies
        
    except Exception as e:
        return f"❌ Erreur lors de la récupération: {str(e)}", []


@tool
def search_movies_by_filters(
    genre: str = None, 
    min_rating: float = None, 
    max_rating: float = None,
    min_year: str = None,
    director: str = None,
    k: int = 10
):
    """
    Recherche des films en utilisant uniquement des filtres (sans recherche sémantique).
    Utile pour des requêtes précises comme "films de Christopher Nolan avec note > 8".
    
    Args:
        genre: Genre du film (ex: "Action", "Drama")
        min_rating: Note minimale (ex: 7.0)
        max_rating: Note maximale (ex: 9.0)
        min_year: Année minimale (ex: "2010")
        director: Nom du réalisateur (ex: "Nolan")
        k: Nombre de résultats
    
    Returns:
        Liste des films correspondant aux critères.
    """
    try:
        retriever = get_retriever()
        
        if retriever is None:
            return "❌ Erreur: Le retriever n'a pas pu être initialisé."
        
        # Construction des filtres
        filters = {}
        
        if genre:
            filters["all_genres"] = {"$like": genre}
        
        if min_rating:
            filters["rating"] = filters.get("rating", {})
            filters["rating"]["$gte"] = min_rating
        
        if max_rating:
            filters["rating"] = filters.get("rating", {})
            filters["rating"]["$lte"] = max_rating
        
        if min_year:
            filters["year"] = {"$gte": min_year}
        
        if director:
            filters["director"] = {"$like": director}
        
        if not filters:
            return "❌ Aucun filtre spécifié. Utilisez retrieve_movies pour une recherche sémantique."
        
        # Recherche avec une requête générique + filtres
        results = retriever.similarity_search(
            "film",  # Requête neutre
            k=k,
            filter=filters
        )
        
        if not results:
            return f"❌ Aucun film trouvé avec ces critères: {filters}"
        
        # Formatage
        formatted_results = []
        for doc in results:
            formatted_results.append(
                f"🎬 {doc.metadata['title']} ({doc.metadata['year']})\n"
                f"⭐ {doc.metadata['rating']}/10 | 🎭 {doc.metadata['director']}\n"
                f"🎪 {doc.metadata['all_genres']}"
            )
        
        return "\n\n".join(formatted_results)
        
    except Exception as e:
        return f"❌ Erreur: {str(e)}"