import streamlit as st
import time
from sqlalchemy.exc import IntegrityError
from database import get_session
from models import Usuario

def verificar_login():
    """
    Gerencia autenticação, cria admin padrão se necessário e salva permissões na sessão.
    """
    if "autenticado" not in st.session_state:
        st.session_state.autenticado = False
        st.session_state.is_admin = False # Padrão seguro

    if st.session_state.autenticado:
        return True

    st.title("🏛️ CECOMP - SESAU/RO")
    
    # Abas para Login e Cadastro
    tab_login, tab_cadastro = st.tabs(["🔑 Login", "📝 Criar Conta"])

    # --- ABA LOGIN ---
    with tab_login:
        with st.form("login_seguro"):
            u = st.text_input("Usuário")
            p = st.text_input("Senha", type="password")
            
            if st.form_submit_button("Entrar"):
                session = get_session()
                
                # VERIFICAÇÃO CRÍTICA: Se não houver usuários, cria o Admin automaticamente
                if session.query(Usuario).count() == 0:
                    try:
                        admin = Usuario(
                            nome="Administrador do Sistema", 
                            login="admin", 
                            senha="123", 
                            is_admin=True  # Define como admin supremo
                        )
                        session.add(admin)
                        session.commit()
                        st.toast("Usuário 'admin' criado automaticamente!", icon="ℹ️")
                    except Exception as e:
                        session.rollback()
                
                # Busca usuário e verifica senha
                user = session.query(Usuario).filter_by(login=u, senha=p).first()
                
                if user:
                    st.session_state.autenticado = True
                    st.session_state.usuario_nome = user.nome
                    st.session_state.is_admin = user.is_admin # Salva permissão [1]
                    
                    st.success(f"Bem-vindo, {user.nome}!")
                    time.sleep(1)
                    st.rerun() # Recarrega a página [2]
                else:
                    st.error("Credenciais inválidas.")

    # --- ABA CADASTRO ---
    with tab_cadastro:
        st.caption("Novos usuários são criados com perfil comum (sem acesso a configurações).")
        with st.form("form_cadastro"):
            nome_novo = st.text_input("Nome Completo")
            login_novo = st.text_input("Login Desejado")
            senha_nova = st.text_input("Senha", type="password")
            
            if st.form_submit_button("Cadastrar"):
                if nome_novo and login_novo and senha_nova:
                    session = get_session()
                    try:
                        # Cria usuário comum (is_admin=False por padrão no model)
                        novo = Usuario(nome=nome_novo, login=login_novo, senha=senha_nova)
                        session.add(novo)
                        session.commit()
                        st.success("Usuário criado! Faça login na outra aba.")
                    except IntegrityError:
                        session.rollback()
                        st.error("Erro: Este login já está em uso.")
                else:
                    st.warning("Preencha todos os campos.")

    return False

def logout():
    st.session_state.autenticado = False
    st.session_state.usuario_nome = ""
    st.session_state.is_admin = False
    st.rerun()
