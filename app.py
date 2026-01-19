import streamlit as st
from auth import verificar_login, logout
from database import get_connection
from models import Base

# Configuração da página deve ser a primeira linha executável
st.set_page_config(page_title="CECOMP - SESAU/RO", layout="wide")

# Inicializa o banco de dados (cria tabelas se não existirem)
conn = get_connection()
Base.metadata.create_all(conn.engine)

# Verifica Login
if verificar_login():
    st.sidebar.title(f"👤 {st.session_state.usuario_nome}")
    if st.sidebar.button("Sair"):
        logout()
    
    st.write("### Bem-vindo ao Sistema")
    st.info("👈 Utilize o menu lateral para navegar entre os módulos.")
