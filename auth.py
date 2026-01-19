import streamlit as st
from database import get_session
from models import Usuario

def verificar_login():
    """Retorna True se o usuário estiver logado, caso contrário exibe a tela de login."""
    if "autenticado" not in st.session_state:
        st.session_state.autenticado = False

    if st.session_state.autenticado:
        return True

    # Tela de Login
    st.title("🏛️ CECOMP - SESAU/RO")
    
    with st.form("login_seguro"):
        u = st.text_input("Usuário")
        p = st.text_input("Senha", type="password")
        
        # O botão de envio é obrigatório para fechar o form
        if st.form_submit_button("Entrar"):
            session = get_session()
            user = session.query(Usuario).filter_by(login=u, senha=p).first()
            
            if user:
                st.session_state.autenticado = True
                st.session_state.usuario_nome = user.nome
                st.rerun() # Recarrega a página para entrar no sistema
            else:
                st.error("Credenciais inválidas.")
    
    return False

def logout():
    st.session_state.autenticado = False
    st.rerun()
