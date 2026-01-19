import streamlit as st
from sqlalchemy.exc import IntegrityError
from database import get_session
from models import Usuario
import time

def verificar_login():
    """
    Gerencia a autenticação e o cadastro de novos usuários.
    Retorna True se o usuário estiver logado, caso contrário exibe as telas de auth.
    """
    # Inicializa estado de autenticação se não existir
    if "autenticado" not in st.session_state:
        st.session_state.autenticado = False

    # Se já estiver autenticado, retorna True para liberar o App
    if st.session_state.autenticado:
        return True

    st.title("🏛️ CECOMP - SESAU/RO")

    # [1] Criação de abas para separar Login de Cadastro
    tab_login, tab_cadastro = st.tabs(["🔑 Login", "📝 Criar Conta"])

    # --- ABA 1: LOGIN (Código existente) ---
    with tab_login:
        with st.form("login_seguro"):
            u = st.text_input("Usuário")
            # [4] Input de senha mascarado
            p = st.text_input("Senha", type="password")
            
            # [5] Botão de submissão obrigatório para fechar o form
            if st.form_submit_button("Entrar"):
                session = get_session()
                # Busca usuário no banco
                user = session.query(Usuario).filter_by(login=u, senha=p).first()
                
                if user:
                    st.session_state.autenticado = True
                    st.session_state.usuario_nome = user.nome
                    st.success(f"Bem-vindo, {user.nome}!")
                    time.sleep(1)
                    st.rerun() # [6] Recarrega a página para atualizar o estado
                else:
                    st.error("Usuário ou senha incorretos.")

    # --- ABA 2: CADASTRO (Nova Funcionalidade) ---
    with tab_cadastro:
        st.markdown("### Novo Usuário")
        # [3] Uso de formulário para agrupar os dados de cadastro
        with st.form("form_cadastro"):
            nome_novo = st.text_input("Nome Completo")
            login_novo = st.text_input("Definir Login (Usuário)")
            senha_nova = st.text_input("Definir Senha", type="password")
            senha_confirma = st.text_input("Confirmar Senha", type="password")
            
            # Botão de submissão do cadastro
            submit_cadastro = st.form_submit_button("Cadastrar Usuário")

            if submit_cadastro:
                # Validações básicas
                if not nome_novo or not login_novo or not senha_nova:
                    st.warning("Preencha todos os campos obrigatórios.")
                elif senha_nova != senha_confirma:
                    st.error("As senhas não coincidem.")
                else:
                    session = get_session()
                    try:
                        # [2] Lógica do SQLAlchemy para inserir dados
                        novo_usuario = Usuario(
                            nome=nome_novo,
                            login=login_novo,
                            senha=senha_nova
                        )
                        session.add(novo_usuario)
                        session.commit()
                        st.success("Usuário cadastrado com sucesso! Faça login na outra aba.")
                    except IntegrityError:
                        # Captura erro se o login já existir (devido ao unique=True no models.py)
                        session.rollback()
                        st.error(f"O login '{login_novo}' já está em uso. Escolha outro.")
                    except Exception as e:
                        session.rollback()
                        st.error(f"Erro ao cadastrar: {e}")

    return False

def logout():
    """Remove a autenticação e recarrega a página."""
    st.session_state.autenticado = False
    st.session_state.usuario_nome = ""
    st.rerun()
