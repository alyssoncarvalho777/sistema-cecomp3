import streamlit as st

def get_connection():
    # Cria a conexão SQL usando o segredo ou padrão local
    return st.connection("central_compras", type="sql", url="sqlite:///central_compras.db")

def get_session():
    conn = get_connection()
    return conn.session
