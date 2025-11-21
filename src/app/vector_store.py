from langchain_community.graphs import Neo4jGraph
from langchain_core.documents import Document
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_graph_retriever import GraphRetriever
from graph_retriever.strategies import Eager


def connect_to_neo4j(url="bolt://localhost:7687", username="neo4j", password="password"):
    """
    Établit une connexion à la base de données Neo4j.
    
    Args:
        url: URL de connexion Neo4j
        username: Nom d'utilisateur
        password: Mot de passe
        
    Returns:
        Neo4jGraph: Instance de connexion au graphe
    """
    graph = Neo4jGraph(
        url=url,
        username=username,
        password=password,
        refresh_schema=False
    )
    return graph


def fetch_movies_from_neo4j(graph, limit=500):
    """
    Récupère les films depuis Neo4j avec leurs métadonnées.
    
    Args:
        graph: Instance Neo4jGraph
        limit: Nombre maximum de films à récupérer
        
    Returns:
        list: Liste des résultats de la requête
    """
    cypher_query = f"""
    MATCH (movie:Movie)-[:HAS_GENRE]->(genre:Genre)
    WHERE movie.overview IS NOT NULL AND movie.overview <> ''
    OPTIONAL MATCH (movie)<-[:DIRECTED]-(director:Director)
    OPTIONAL MATCH (movie)<-[:ACTED_IN]-(actor:Actor)
    WITH movie, 
         collect(DISTINCT genre.name) AS genres,
         director.name AS director_name,
         collect(DISTINCT actor.name) AS actors
    RETURN movie.title AS title, 
           movie.overview AS overview,
           movie.tagline AS tagline,
           movie.release_date AS release_date,
           movie.vote_average AS rating,
           movie.runtime AS runtime,
           movie.id AS movie_id,
           genres,
           director_name,
           actors
    LIMIT {limit}
    """
    
    results = graph.query(cypher_query)
    print(f" {len(results)} films récupérés depuis Neo4j")
    return results


def create_document_from_record(record):
    """
    Crée un Document LangChain à partir d'un enregistrement Neo4j.
    
    Args:
        record: Enregistrement de film depuis Neo4j
        
    Returns:
        Document: Document LangChain ou None si invalide
    """
    overview = record.get("overview", "")
    if not overview or str(overview).strip() == "":
        return None

    director = record.get("director_name", "Unknown")
    actors = record.get("actors", [])
    main_actors = ", ".join(actors[:5]) if actors else "Unknown"
    genres = record.get("genres", [])
    all_genres = ", ".join(genres) if genres else "Unknown"
    tagline = record.get("tagline", "")
    
    content_parts = [
        f"Titre : {record.get('title', 'Unknown')}",
    ]
    if tagline:
        content_parts.append(tagline)
    content_parts.extend([
        overview,
        f"Film réalisé par {director}",
        f"Acteurs : {main_actors}",
        f"Genres : {all_genres}"
    ])
    content = "\n\n".join(content_parts)
    
    rating = float(record.get("rating", 0))
    rating_category = "high" if rating >= 7 else "medium" if rating >= 5 else "low"
    
    runtime = int(record.get("runtime", 0))
    length_category = "long" if runtime >= 120 else "medium" if runtime >= 90 else "short"
    
    metadata = {
        "title": record.get("title", "Unknown"),
        "release_date": str(record.get("release_date", "")),
        "rating": rating,
        "rating_category": rating_category,
        "runtime": runtime,
        "length_category": length_category,
        "all_genres": all_genres,
        "director": director,
        "main_actors": main_actors,
        "movie_id": str(record.get("movie_id", ""))
    }
    
    doc = Document(
        page_content=content,
        metadata=metadata,
        id=metadata["title"]
    )
    
    return doc


def create_documents(results):
    """
    Crée une liste de documents à partir des résultats Neo4j.
    
    Args:
        results: Liste des résultats de la requête Neo4j
        
    Returns:
        list: Liste de Documents LangChain
    """
    movie_documents = []
    
    for record in results:
        doc = create_document_from_record(record)
        if doc:
            movie_documents.append(doc)
    
    print(f"📄 {len(movie_documents)} documents créés")
    return movie_documents

def create_vector_store(documents, model_name="sentence-transformers/all-MiniLM-L6-v2"):
    """
    Crée un vector store à partir des documents.
    
    Args:
        documents: Liste de documents
        model_name: Nom du modèle d'embeddings
        
    Returns:
        InMemoryVectorStore: Vector store créé
    """
    print("\n Création des embeddings...")
    embeddings = HuggingFaceEmbeddings(model_name=model_name)
    
    print(" Création du vector store...")
    vector_store = InMemoryVectorStore.from_documents(
        documents=documents,
        embedding=embeddings
    )
    
    print(f" {len(documents)} documents ajoutés au vector store!")
    return vector_store


def create_graph_retriever(vector_store, k=10, start_k=5, max_depth=3):
    """
    Crée un Graph Retriever pour la recherche.
    
    Args:
        vector_store: Vector store contenant les documents
        k: Nombre de résultats à retourner
        start_k: Nombre de résultats initiaux
        max_depth: Profondeur maximale de recherche
        
    Returns:
        GraphRetriever: Retriever configuré
    """
    print("\n Création du Graph Retriever...")
    
    retriever = GraphRetriever(
        store=vector_store,
        edges=[
            ("director", "director"),
            ("all_genres", "all_genres"),
            ("rating_category", "rating_category"),
            ("main_actors", "main_actors")
        ],
        strategy=Eager(
            k=k,
            start_k=start_k,
            max_depth=max_depth
        )
    )
    
    print(" Graph Retriever créé!")
    return retriever

_retriever = None

def get_retriever():
    """
    Retourne le retriever, en le créant si nécessaire.
    """
    global _retriever
    if _retriever is None:
        print(" Initialisation du retriever...")
        _retriever = main()
    return _retriever

def main():
    """
    Fonction principale pour exécuter le pipeline complet.
    """
    print("Démarrage du système de recommandation de films\n")
    
    print(" Connexion à Neo4j...")
    graph = connect_to_neo4j()
    
    results = fetch_movies_from_neo4j(graph, limit=500)
    
    movie_documents = create_documents(results)
    
    if len(movie_documents) == 0:
        print(" Aucun document trouvé!")
        return None
    
    vector_store = create_vector_store(movie_documents)
    
    retriever = create_graph_retriever(vector_store)
    
    print("\n Système initialisé avec succès!")
    print(f" Total: {len(movie_documents)} films indexés")
    
    return retriever


if __name__ == "__main__":
    retriever = main()