import streamlit as st
import time
from sqlalchemy.exc import IntegrityError
from database import get_session
from models import Usuario

def verificar_login():
    """
    Controla o acesso ao sistema.
    """
    if "autenticado" not in st.session_state:
        st.session_state.autenticado = False
        st.session_state.is_admin = False

    if st.session_state.autenticado:
        return True

    # --- CORREÇÃO AQUI ---
    # Passamos 3 valores na lista para preencher as 3 variáveis (col1, col2, col3)
    col1, col2, col3 = st.columns([1, 2, 3]) 
    
    with col2: # O formulário fica centralizado na coluna do meio
        st.title("🏛️ CECOMP - SESAU/RO")
        
        tab_login, tab_cadastro = st.tabs(["🔑 Acessar", "📝 Criar Conta"])

        # --- ABA DE LOGIN ---
        with tab_login:
            with st.form("login_form"):
                u = st.text_input("Usuário")
                p = st.text_input("Senha", type="password")
                
                if st.form_submit_button("Entrar", type="primary"):
                    session = get_session()
                    
                    # Cria Admin se banco vazio
                    if session.query(Usuario).count() == 0:
                        try:
                            admin = Usuario(nome="Admin", login="admin", senha="123", is_admin=True)
                            session.add(admin)
                            session.commit()
                            st.toast("Admin criado (admin/123)", icon="🛡️")
                        except:
                            session.rollback()

                    user = session.query(Usuario).filter_by(login=u, senha=p).first()
                    
                    if user:
                        st.session_state.autenticado = True
                        st.session_state.usuario_nome = user.nome
                        st.session_state.is_admin = user.is_admin
                        st.success("Sucesso!")
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.error("Dados incorretos.")

        # --- ABA DE CADASTRO ---
        with tab_cadastro:
            st.info("Novos cadastros possuem perfil básico.")
            with st.form("cadastro_form"):
                nome = st.text_input("Nome")
                login = st.text_input("Login")
                senha = st.text_input("Senha", type="password")
                
                if st.form_submit_button("Cadastrar"):
                    if nome and login and senha:
                        session = get_session()
                        try:
                            novo = Usuario(nome=nome, login=login, senha=senha)
                            session.add(novo)
                            session.commit()
                            st.success("Criado! Faça login.")
                        except IntegrityError:
                            session.rollback()
                            st.error("Login já existe.")
                    else:
                        st.warning("Preencha tudo.")
    
    return False

def logout():
    st.session_state.autenticado = False
    st.rerun()
