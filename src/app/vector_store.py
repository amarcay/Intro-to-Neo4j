from langchain_community.graphs import Neo4jGraph
from langchain_neo4j import Neo4jVector
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings


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
    try:
        graph = Neo4jGraph(
            url=url,
            username=username,
            password=password,
            refresh_schema=False
        )
        # Test de connexion
        graph.query("RETURN 1")
        print("Connexion Neo4j établie")
        return graph
    except Exception as e:
        print(f"Erreur de connexion Neo4j: {e}")
        raise


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
         head(collect(DISTINCT director.name)) AS director_name,
         collect(DISTINCT actor.name)[0..10] AS actors
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
    ORDER BY movie.vote_average DESC
    LIMIT {limit}
    """
    
    results = graph.query(cypher_query)
    print(f"🎬 {len(results)} films récupérés depuis Neo4j")
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

    # Nettoyage des données
    director = record.get("director_name") or "Unknown"
    actors = [a for a in record.get("actors", []) if a]
    main_actors = ", ".join(actors[:5]) if actors else "Unknown"
    genres = [g for g in record.get("genres", []) if g]
    all_genres = ", ".join(genres) if genres else "Unknown"
    tagline = (record.get("tagline") or "").strip()
    
    # Construction du contenu enrichi
    content_parts = [f"Titre : {record.get('title', 'Unknown')}"]
    if tagline:
        content_parts.append(tagline)
    content_parts.extend([
        overview,
        f"Film réalisé par {director}",
        f"Acteurs : {main_actors}",
        f"Genres : {all_genres}"
    ])
    content = "\n\n".join(content_parts)
    
    # Catégorisation
    rating = float(record.get("rating", 0))
    rating_category = "high" if rating >= 7 else "medium" if rating >= 5 else "low"
    
    runtime = int(record.get("runtime", 0)) if record.get("runtime") else 0
    length_category = "long" if runtime >= 120 else "medium" if runtime >= 90 else "short"
    
    # Année de sortie
    release_date = str(record.get("release_date", ""))
    year = release_date.split("-")[0] if release_date else "Unknown"
    
    metadata = {
        "title": record.get("title", "Unknown"),
        "release_date": release_date,
        "year": year,
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
        id=f"movie_{metadata['movie_id']}"
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
    
    print(f"{len(movie_documents)} documents créés")
    return movie_documents


def create_neo4j_vector_store(
    url="bolt://localhost:7687",
    username="neo4j",
    password="password",
    model_name="sentence-transformers/all-MiniLM-L6-v2",
    index_name="movie_embeddings",
    use_existing=False
):
    """
    Crée ou charge un Neo4jVector store.
    
    Args:
        url: URL Neo4j
        username: Nom d'utilisateur
        password: Mot de passe
        model_name: Modèle d'embeddings
        index_name: Nom de l'index
        use_existing: Si True, utilise l'index existant
        
    Returns:
        Neo4jVector: Vector store Neo4j
    """
    print("\n🚀 Initialisation du vector store Neo4j...")
    
    embeddings = HuggingFaceEmbeddings(model_name=model_name)
    
    # Si on veut utiliser l'index existant
    if use_existing:
        print("Chargement depuis l'index existant...")
        try:
            vector_store = Neo4jVector.from_existing_index(
                embedding=embeddings,
                url=url,
                username=username,
                password=password,
                index_name=index_name,
            )
            print("Vector store chargé!")
            return vector_store
        except Exception as e:
            print(f"Index non trouvé, création d'un nouvel index...")
            use_existing = False
    
    # Créer un nouvel index
    if not use_existing:
        print("Connexion à Neo4j et récupération des films...")
        graph = connect_to_neo4j(url, username, password)
        
        results = fetch_movies_from_neo4j(graph, limit=500)
        movie_documents = create_documents(results)
        
        if not movie_documents:
            print("❌ Aucun document trouvé!")
            return None
        
        print(f"\nCréation de l'index vectoriel dans Neo4j...")
        print(f"   Index: {index_name}")
        print(f"   Documents: {len(movie_documents)}")
        
        # CRÉATION DE L'INDEX VECTORIEL DANS NEO4J
        vector_store = Neo4jVector.from_documents(
            documents=movie_documents,
            embedding=embeddings,
            url=url,
            username=username,
            password=password,
            index_name=index_name,
            node_label="MovieVector",
            embedding_node_property="embedding",
            text_node_property="text"
        )
        
        print(f"\n Vector store créé avec succès!")
        print(f" {len(movie_documents)} films indexés dans Neo4j")
        
        return vector_store


# Variable globale pour le retriever
_retriever = None


def get_retriever(use_existing=True):
    """
    Retourne le retriever Neo4jVector, en le créant si nécessaire.
    
    Args:
        use_existing: Si True, tente de charger l'index existant
        
    Returns:
        Neo4jVector: Vector store configuré
    """
    global _retriever
    
    if _retriever is None:
        print("Initialisation du retriever Neo4jVector...")
        _retriever = create_neo4j_vector_store(use_existing=use_existing)
    
    return _retriever


def main():
    """
    Fonction principale pour exécuter le pipeline complet.
    """
    print("🎬 Démarrage du système de recommandation de films\n")
    
    retriever = create_neo4j_vector_store(use_existing=False)
    
    if retriever:
        print("Système initialisé avec succès!")
        
        # Test de recherche
        print("Test de recherche...")
        results = retriever.similarity_search(
            "Un film d'action avec des effets spéciaux",
            k=3
        )
        
        print(f"{len(results)} films trouvés:")
        for i, doc in enumerate(results, 1):
            print(f"\n{i}. {doc.metadata['title']}")
            print(f"   Note: {doc.metadata['rating']}/10")
            print(f"   Réalisateur: {doc.metadata['director']}")
    
    return retriever


if __name__ == "__main__":
    retriever = main()