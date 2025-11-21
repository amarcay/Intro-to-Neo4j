import streamlit as st
import os
from dotenv import load_dotenv
from tools import *
from prompt import *
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from vector_store import get_retriever
import warnings

warnings.filterwarnings("ignore")
load_dotenv()

st.set_page_config(
    page_title="Chat Agent RAG",
    page_icon="🤖",
    layout="centered"
)

st.title("🤖 Chat Agent RAG")
st.caption("Posez vos questions sur les films!")

if "messages_agent" not in st.session_state:
    st.session_state["messages_agent"] = [
        {"role": "assistant", "content": "Bonjour! Je suis votre assistant intelligent. Posez-moi des questions sur les films!"}
    ]

if "agent" not in st.session_state:
    with st.spinner("Initialisation de l'agent..."):
        try:
            # Initialisation du retriever (Neo4j + Vector Store)
            get_retriever()
            
            google_key = os.environ["GOOGLE_API_KEY"]
            llm = ChatGoogleGenerativeAI(
                model="gemini-2.5-flash",
                convert_system_message_to_human=True
            )
            
            tools = [retrieve_movies]
            
            prompt = ChatPromptTemplate.from_messages([
                ("system", rag_prompt()),
                ("human", "{input}"),
                MessagesPlaceholder(variable_name="agent_scratchpad"),
            ])
            
            agent = create_tool_calling_agent(llm, tools, prompt)
            st.session_state["agent"] = AgentExecutor(agent=agent, tools=tools, verbose=True)
            
            st.success("Agent initialisé avec succès!")
        except Exception as e:
            st.error(f"Erreur lors de l'initialisation de l'agent: {str(e)}")
            st.stop()

for msg in st.session_state.messages_agent:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

if prompt := st.chat_input("Posez votre question..."):
    st.session_state.messages_agent.append({"role": "user", "content": prompt})
    
    with st.chat_message("user"):
        st.write(prompt)
    
    with st.chat_message("assistant"):
        response_placeholder = st.empty()
        
        try:
            with st.spinner("Réflexion en cours..."):
                response = st.session_state["agent"].invoke({"input": prompt})
                
                full_response = response["output"]
                
                response_placeholder.write(full_response)
                
                st.session_state.messages_agent.append({
                    "role": "assistant",
                    "content": full_response
                })
                
        except Exception as e:
            error_message = f"Erreur lors de la génération de la réponse: {str(e)}"
            response_placeholder.error(error_message)
            st.session_state.messages_agent.append({
                "role": "assistant",
                "content": error_message
            })

with st.sidebar:
    st.header("ℹ️ Informations")
    st.write("Cet agent utilise:")
    st.write("- 🧠 Modèle: Gemini 2.5 Flash")
    st.write("- 🔧 Outils: Recherche de films")
    st.write("- 📚 RAG pour des réponses contextuelles")
    
    st.divider()
    
    if st.button("🗑️ Effacer l'historique", use_container_width=True):
        st.session_state.messages_agent = [
            {"role": "assistant", "content": "Bonjour! Je suis votre assistant intelligent. Posez-moi des questions sur les films!"}
        ]
        st.rerun()
    
    st.divider()
    st.caption("💡 Astuce: Posez des questions détaillées pour obtenir de meilleures réponses!")