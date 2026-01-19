import streamlit as st
import time
from sqlalchemy.exc import IntegrityError
from database import get_session
from models import Usuario

def verificar_login():
    """
    Controla o acesso ao sistema.
    Retorna True se autenticado, False caso contrário.
    """
    if "autenticado" not in st.session_state:
        st.session_state.autenticado = False
        st.session_state.is_admin = False

    if st.session_state.autenticado:
        return True

    # Tela de Login Centralizada
    col1, col2, col3 = st.columns([3, 4])
    with col2:
        st.title("🏛️ CECOMP - SESAU/RO")
        
        tab_login, tab_cadastro = st.tabs(["🔑 Acessar", "📝 Criar Conta"])

        # --- ABA DE LOGIN ---
        with tab_login:
            with st.form("login_form"):
                u = st.text_input("Usuário")
                p = st.text_input("Senha", type="password")
                
                if st.form_submit_button("Entrar", type="primary"):
                    session = get_session()
                    
                    # Rotina de Primeiro Acesso: Cria Admin se o banco estiver vazio
                    if session.query(Usuario).count() == 0:
                        try:
                            admin = Usuario(
                                nome="Administrador", 
                                login="admin", 
                                senha="123", 
                                is_admin=True
                            )
                            session.add(admin)
                            session.commit()
                            st.toast("Usuário 'admin' criado com sucesso!", icon="🛡️")
                        except Exception:
                            session.rollback()

                    # Validação de Credenciais
                    user = session.query(Usuario).filter_by(login=u, senha=p).first()
                    
                    if user:
                        st.session_state.autenticado = True
                        st.session_state.usuario_nome = user.nome
                        st.session_state.is_admin = user.is_admin
                        st.success("Login realizado com sucesso!")
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.error("Usuário ou senha incorretos.")

        # --- ABA DE CADASTRO ---
        with tab_cadastro:
            st.info("Novos cadastros possuem perfil de acesso básico.")
            with st.form("cadastro_form"):
                nome_novo = st.text_input("Nome Completo")
                login_novo = st.text_input("Usuário Desejado")
                senha_novo = st.text_input("Senha", type="password")
                
                if st.form_submit_button("Cadastrar"):
                    if nome_novo and login_novo and senha_novo:
                        session = get_session()
                        try:
                            # Cria usuário comum (is_admin=False)
                            novo = Usuario(nome=nome_novo, login=login_novo, senha=senha_novo)
                            session.add(novo)
                            session.commit()
                            st.success("Conta criada! Faça login na aba ao lado.")
                        except IntegrityError:
                            session.rollback()
                            st.error("Erro: Este nome de usuário já existe.")
                    else:
                        st.warning("Preencha todos os campos.")
    
    return False

def logout():
    st.session_state.autenticado = False
    st.session_state.usuario_nome = ""
    st.session_state.is_admin = False
    st.rerun()
