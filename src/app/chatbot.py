import streamlit as st
import os
from dotenv import load_dotenv
from tools import retrieve_movies, search_movies_by_filters
from prompt import rag_prompt
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_classic.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from vector_store import get_retriever
import warnings

warnings.filterwarnings("ignore")
load_dotenv()

st.set_page_config(
    page_title="🎬 Movie Recommender RAG",
    page_icon="🎬",
    layout="wide"
)

# CSS personnalisé
st.markdown("""
    <style>
    .stAlert {
        padding: 1rem;
        margin: 1rem 0;
    }
    </style>
""", unsafe_allow_html=True)

st.title("🎬 Movie Recommender avec Graph RAG")
st.caption("Système de recommandation utilisant Neo4j et embeddings vectoriels")

# Initialisation de la session
if "messages_agent" not in st.session_state:
    st.session_state["messages_agent"] = [
        {
            "role": "assistant", 
            "content": "🎬 Bonjour! Je suis votre assistant cinéma intelligent. Je peux vous recommander des films basés sur vos préférences!\n\n**Exemples de questions:**\n- Recommande-moi un film d'action avec des effets spéciaux\n- Quels films de Christopher Nolan ont une note > 8?\n- Films de science-fiction philosophiques\n- Films d'horreur récents bien notés"
        }
    ]

# Initialisation de l'agent
if "agent" not in st.session_state:
    with st.spinner("🔄 Initialisation de l'agent et du vector store Neo4j..."):
        try:
            # Initialisation du Neo4jVector store
            retriever = get_retriever(use_existing=True)
            
            if retriever is None:
                st.error("❌ Impossible d'initialiser le vector store. Vérifiez votre connexion Neo4j.")
                st.stop()
            
            # Initialisation du LLM
            google_key = os.environ.get("GOOGLE_API_KEY")
            if not google_key:
                st.error("❌ GOOGLE_API_KEY non trouvée dans .env")
                st.stop()
            
            llm = ChatGoogleGenerativeAI(
                model="gemini-2.5-flash",
                convert_system_message_to_human=True,
                temperature=0.7
            )
            
            # Outils disponibles
            tools = [retrieve_movies, search_movies_by_filters]
            
            # Prompt de l'agent
            prompt = ChatPromptTemplate.from_messages([
                ("system", rag_prompt()),
                ("human", "{input}"),
                MessagesPlaceholder(variable_name="agent_scratchpad"),
            ])
            
            # Création de l'agent
            agent = create_tool_calling_agent(llm, tools, prompt)
            st.session_state["agent"] = AgentExecutor(
                agent=agent, 
                tools=tools, 
                verbose=True,
                handle_parsing_errors=True
            )
            
            st.success("✅ Agent initialisé avec succès!")
            
        except Exception as e:
            st.error(f"❌ Erreur lors de l'initialisation: {str(e)}")
            st.exception(e)
            st.stop()

# Affichage de l'historique
for msg in st.session_state.messages_agent:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Input utilisateur
if prompt := st.chat_input("🎬 Quelle sorte de film cherchez-vous?"):
    # Ajouter le message utilisateur
    st.session_state.messages_agent.append({"role": "user", "content": prompt})
    
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Générer la réponse
    with st.chat_message("assistant"):
        response_placeholder = st.empty()
        
        try:
            with st.spinner("🤔 Recherche en cours..."):
                response = st.session_state["agent"].invoke({"input": prompt})
                
                full_response = response["output"]
                
                response_placeholder.markdown(full_response)
                
                st.session_state.messages_agent.append({
                    "role": "assistant",
                    "content": full_response
                })
                
        except Exception as e:
            error_message = f"❌ Erreur lors de la génération: {str(e)}"
            response_placeholder.error(error_message)
            st.session_state.messages_agent.append({
                "role": "assistant",
                "content": error_message
            })

# Sidebar
with st.sidebar:
    st.header("ℹ️ Informations")
    
    st.markdown("""
    **🔧 Composants:**
    - 🧠 LLM: Gemini 2.0 Flash
    - 🗄️ Base: Neo4j
    - 📊 Vector Store: Neo4jVector
    - 🔍 Embeddings: MiniLM-L6-v2
    
    **🛠️ Outils disponibles:**
    - `retrieve_movies`: Recherche sémantique
    - `search_movies_by_filters`: Filtres précis
    """)
    
    st.divider()
    
    # Stats (si possible)
    try:
        retriever = get_retriever()
        if retriever:
            st.markdown("**📊 Statistiques:**")
            st.info("Vector store: ✅ Connecté")
    except:
        st.warning("⚠️ Stats non disponibles")
    
    st.divider()
    
    # Bouton reset
    if st.button("🗑️ Effacer l'historique", use_container_width=True):
        st.session_state.messages_agent = [
            {
                "role": "assistant", 
                "content": "🎬 Historique effacé! Posez-moi de nouvelles questions sur les films."
            }
        ]
        st.rerun()
    
    st.divider()
    
    # Exemples de requêtes
    st.markdown("**💡 Exemples de questions:**")
    example_queries = [
        "Films d'action des années 2010",
        "Christopher Nolan note > 8",
        "Science-fiction philosophique",
        "Comédies romantiques bien notées"
    ]
    
    for query in example_queries:
        if st.button(f"📝 {query}", use_container_width=True):
            st.session_state.messages_agent.append({"role": "user", "content": query})
            st.rerun()