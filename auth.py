import streamlit as st
import time
from sqlalchemy.exc import IntegrityError
from database import get_session
from models import Usuario, Setor

# --- ATENÇÃO: NENHUMA IMPORTAÇÃO DE 'auth' AQUI ---

def verificar_login():
    """
    Gerencia a autenticação e o cadastro de usuários.
    Inclui validação de confirmação de senha.
    """
    # 1. Inicializa variáveis de estado da sessão
    if "autenticado" not in st.session_state:
        st.session_state.autenticado = False
        st.session_state.is_admin = False
        st.session_state.usuario_nome = ""
        st.session_state.usuario_login = ""
        st.session_state.setor_nome = ""

    # 2. Se já estiver logado, libera o acesso
    if st.session_state.autenticado:
        return True

    # 3. Inicialização de Dados Básicos (Setores e Admin)
    session = get_session()
    
    # Garante que existam setores
    if session.query(Setor).count() == 0:
        nucleos_padrao = [
            "Administrativo", "NPA", "NAP", "NMP", "NSC", 
            "NSM", "NDJPL", "NOSE", "NMCHE", "NMSG", "NMN", "NLAB"
        ]
        for n in nucleos_padrao:
            session.add(Setor(nome=n))
        session.commit()

    # Garante que exista o Admin
    if session.query(Usuario).count() == 0:
        try:
            setor_adm = session.query(Setor).filter_by(nome="Administrativo").first()
            if not setor_adm: 
                setor_adm = session.query(Setor).first()
            
            if setor_adm:
                admin = Usuario(
                    nome="Administrador", 
                    login="admin", 
                    senha="123", 
                    is_admin=True, 
                    setor_id=setor_adm.id
                )
                session.add(admin)
                session.commit()
                st.toast("Usuário 'admin' criado automaticamente!", icon="🛡️")
        except Exception:
            session.rollback()

    # 4. Interface de Login/Cadastro
    col1, col2, col3 = st.columns([1, 2, 3]) 
    
    with col2:
        st.title("🏛️ CECOMP - SESAU/RO")
        
        tab_login, tab_cadastro = st.tabs(["🔑 Acessar", "📝 Criar Conta"])

        # --- ABA LOGIN ---
        with tab_login:
            with st.form("login_form"):
                u = st.text_input("Usuário")
                p = st.text_input("Senha", type="password")
                
                if st.form_submit_button("Entrar", type="primary"):
                    user = session.query(Usuario).filter_by(login=u, senha=p).first()
                    
                    if user:
                        st.session_state.autenticado = True
                        st.session_state.usuario_nome = user.nome
                        st.session_state.usuario_login = user.login
                        st.session_state.is_admin = user.is_admin
                        
                        st.session_state.setor_id = user.setor_id
                        st.session_state.setor_nome = user.setor.nome if user.setor else "Indefinido"
                        
                        st.success(f"Bem-vindo, {user.nome}!")
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.error("Usuário ou senha incorretos.")

        # --- ABA CADASTRO (COM CONFIRMAÇÃO DE SENHA) ---
        with tab_cadastro:
            st.info("Preencha os dados para solicitar acesso.")
            
            lista_nucleos = session.query(Setor).order_by(Setor.nome).all()
            
            with st.form("cadastro_form"):
                nome = st.text_input("Nome Completo")
                login = st.text_input("Login Desejado")
                
                # Campos de Senha
                c_senha1, c_senha2 = st.columns(2)
                with c_senha1:
                    senha = st.text_input("Senha", type="password")
                with c_senha2:
                    senha_confirm = st.text_input("Confirmar Senha", type="password")
                
                nucleo_sel = st.selectbox(
                    "Selecione seu Núcleo:", 
                    options=lista_nucleos,
                    format_func=lambda x: x.nome
                )
                
                if st.form_submit_button("Cadastrar"):
                    # 1. Verifica se campos estão preenchidos
                    if not (nome and login and senha and senha_confirm and nucleo_sel):
                        st.warning("Preencha todos os campos.")
                    
                    # 2. Verifica se as senhas coincidem
                    elif senha != senha_confirm:
                        st.error("⚠️ As senhas não coincidem. Tente novamente.")
                    
                    # 3. Tenta cadastrar
                    else:
                        try:
                            novo = Usuario(
                                nome=nome, 
                                login=login, 
                                senha=senha, 
                                is_admin=False, 
                                setor_id=nucleo_sel.id
                            )
                            session.add(novo)
                            session.commit()
                            st.success("Cadastro realizado com sucesso! Faça login.")
                        except IntegrityError:
                            session.rollback()
                            st.error("Erro: Este login já está em uso.")
    
    return False

def logout():
    st.session_state.clear()
    st.rerun()
