import streamlit as st

# O st.connection gerencia a engine e a session automaticamente
def get_connection():
    # 'type="sql"' cria uma conexão SQLAlchemy
    return st.connection("central_compras", type="sql", url="sqlite:///central_compras.db")

def get_session():
    conn = get_connection()
    return conn.session
