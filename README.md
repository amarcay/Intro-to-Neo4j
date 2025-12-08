# 🎬 Movie Chat Agent RAG

Ce projet est un assistant intelligent (Chatbot) capable de répondre à des questions sur les films en utilisant une architecture RAG (Retrieval-Augmented Generation) couplée à une base de données de graphe Neo4j.

> [!NOTE]
> **Contexte du projet** : Ce projet a été réalisé dans le cadre d'un cours sur **Neo4j**. Si l'objectif académique était de découvrir cette base de données, j'ai personnellement profité de cette opportunité pour aller plus loin et explorer les concepts du **Graph RAG** (Retrieval-Augmented Generation sur des graphes).

## 🎥 Démonstration

![Démonstration](example/example.mov)

## 🚀 Fonctionnalités

-   **Interface de Chat** : Une interface conviviale construite avec Streamlit.
-   **RAG Hybride** : Utilise la puissance de Neo4j pour combiner recherche vectorielle et recherche par graphe.
-   **LLM** : Propulsé par Google Gemini (Gemini 2.5 Flash).
-   **Import de Données** : Scripts pour importer des données de films depuis TMDB et OMDb.
-   **Outils** : L'agent dispose d'outils pour rechercher des informations spécifiques dans la base de connaissances.

## 🛠️ Outils de l'Agent

L'agent dispose d'outils spécifiques pour interroger la base de données :

### 1. `retrieve_movies` (Recherche Sémantique)
Cet outil utilise le **Vector Search** pour trouver des films basés sur le sens de la requête. Il est idéal pour des questions vagues ou descriptives (ex: "films de science-fiction psychologique").

![Exemple retrieve_movies](example/retrieve_movies.png)

### 2. `search_movies_by_filters` (Recherche Exacte)
Cet outil permet de filtrer la base de données avec des critères précis (année, réalisateur, genre, note). Il est utilisé quand l'utilisateur donne des contraintes explicites.

![Exemple search_movies_by_filters](example/search_movies_by_filters.png)

## 🧠 Comment fonctionne le Graph RAG ?

Contrairement à un RAG classique qui se base uniquement sur la similarité vectorielle, le **Graph RAG** combine la recherche sémantique avec la structure relationnelle du graphe. Dans ce projet, nous utilisons une approche hybride :

1.  **Recherche Vectorielle (Point d'entrée)** :
    Lorsqu'une question est posée, le système convertit la requête en vecteur et recherche d'abord les films les plus similaires sémantiquement dans le `VectorStore` (basé sur les résumés, titres, etc.).

2.  **Traversée du Graphe (Contexte élargi)** :
    À partir de ces films initiaux, l'algorithme navigue dans le graphe Neo4j en suivant les relations définies (ex: `DIRECTED`, `HAS_GENRE`, `ACTED_IN`). Cela permet de découvrir des films connexes qui n'auraient peut-être pas été trouvés par simple similarité de texte, mais qui sont pertinents grâce à leurs liens (même réalisateur, même genre, etc.).

Cette méthode permet d'enrichir le contexte fourni au LLM avec des informations structurées et interconnectées, offrant ainsi des réponses plus précises et complètes.

## 🛠️ Stack Technique

-   **Langage** : Python 3.10+
-   **Interface** : [Streamlit](https://streamlit.io/)
-   **Orchestration IA** : [LangChain](https://www.langchain.com/)
-   **Base de Données** : [Neo4j](https://neo4j.com/) (Graph Database)
-   **Modèle IA** : Google Generative AI (Gemini)
-   **Gestionnaire de paquets** : `uv`

## ⚙️ Prérequis

-   Python 3.10 ou supérieur
-   Une instance Neo4j (Locale ou AuraDB)
-   Clés API pour :
    -   Google AI (Gemini)
    -   TMDB (The Movie Database)
    -   OMDb (Open Movie Database)

## 📦 Installation

1.  **Cloner le dépôt**

    ```bash
    git clone https://github.com/amarcay/Intro-to-Neo4j-GraphRAG.git
    cd neo
    ```

2.  **Installer les dépendances**

    Ce projet utilise `uv` pour la gestion des dépendances.

    ```bash
    # Si vous n'avez pas uv : pip install uv
    uv sync
    ```


3.  **Configuration**

    Créez un fichier `.env` à la racine du projet et ajoutez vos variables d'environnement :

    ```env
    # Neo4j
    NEO4J_URI=bolt://localhost:7687
    NEO4J_USER=neo4j
    NEO4J_PASSWORD=votre_mot_de_passe

    # APIs
    GOOGLE_API_KEY=votre_google_api_key
    TMDB_API_KEY=votre_tmdb_bearer_token
    OMDB_API_KEY=votre_omdb_api_key
    OMDB_BASE_URL=http://www.omdbapi.com/
    ```

## 💾 Import des Données

Avant d'utiliser le chatbot, vous devez peupler votre base de données Neo4j. Deux scripts sont disponibles :

-   **Import via TMDB** (Recommandé pour les données récentes et détaillées) :
    ```bash
    python src/app/upload_data.py
    ```

-   **Import via OMDb** :
    ```bash
    python src/app/movie_neo4j.py
    ```

## ▶️ Démarrage

Lancez l'application Streamlit :

```bash
streamlit run src/app/chatbot.py
```

L'application sera accessible à l'adresse `http://localhost:8501`.

## 📂 Structure du Projet

```
neo/
├── src/
│   ├── app/
│   │   ├── chatbot.py       # Point d'entrée de l'application Streamlit
│   │   ├── upload_data.py   # Script d'import TMDB
│   │   ├── movie_neo4j.py   # Script d'import OMDb
│   │   ├── tools.py         # Définition des outils pour l'agent
│   │   ├── prompt.py        # Templates de prompt
│   │   └── vector_store.py  # Gestion du retriever et vector store
│   └── api/                 # Modèles de données (optionnel)
├── pyproject.toml           # Configuration du projet et dépendances
└── .env                     # Variables d'environnement (non versionné)
```
