from langchain_core.tools import tool
from vector_store import get_retriever

@tool(response_format="content_and_artifact")
def retrieve_movies(query: str, genre: str = None, min_rating: float = None):
    """
    Récupère des films pertinents via le Graph Retriever.
    
    Args:
        query: Description du type de film recherché (ex: "film d'action avec des combats")
        genre: Genre spécifique à filtrer (optionnel, ex: "Action", "Drama")
        min_rating: Note minimale souhaitée (optionnel, ex: 7.0)
    
    Returns:
        Une chaîne formatée avec les films trouvés et leurs métadonnées.
    """
    try:
        retriever = get_retriever()
        
        if retriever is None:
            return "Erreur: Le retriever n'a pas pu être initialisé.", []
        
        results = retriever.invoke(query)
        
        if not results:
            return "Aucun film trouvé pour cette recherche.", []
        
        filtered_results = []
        for doc in results:
            if genre and genre.lower() not in doc.metadata.get("all_genres", "").lower():
                continue
            
            if min_rating and doc.metadata.get("rating", 0) < min_rating:
                continue
            
            filtered_results.append(doc)
        
        if not filtered_results:
            return f"Aucun film trouvé correspondant aux critères (genre: {genre}, note min: {min_rating}).", []
        
        formatted_movies = []
        for doc in filtered_results[:10]:
            movie_info = {
                "title": doc.metadata.get("title"),
                "overview": doc.page_content.split("\n\n")[2] if len(doc.page_content.split("\n\n")) > 2 else "",
                "director": doc.metadata.get("director"),
                "actors": doc.metadata.get("main_actors"),
                "genres": doc.metadata.get("all_genres"),
                "rating": doc.metadata.get("rating"),
                "runtime": doc.metadata.get("runtime"),
                "release_date": doc.metadata.get("release_date", "")[:4]
            }
            formatted_movies.append(movie_info)
        
        serialized = "\n\n".join([
            f"{movie['title']} ({movie['release_date']})\n"
            f"Note: {movie['rating']}/10 | Durée: {movie['runtime']} min\n"
            f"Genres: {movie['genres']}\n"
            f"Réalisateur: {movie['director']}\n"
            f"Acteurs: {movie['actors']}\n"
            f"Résumé: {movie['overview'][:200]}..."
            for movie in formatted_movies
        ])
        
        return serialized, formatted_movies
        
    except Exception as e:
        return f"Erreur lors de la récupération: {str(e)}", []
