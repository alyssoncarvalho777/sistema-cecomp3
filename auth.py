import streamlit as st
import time
from sqlalchemy.exc import IntegrityError
from database import get_session
from models import Usuario, Setor

def verificar_login():
    """
    Gerencia Login e Cadastro. Garante a criação correta dos Setores.
    """
    # 1. Inicializa Variáveis de Sessão
    if "autenticado" not in st.session_state:
        st.session_state.autenticado = False
        st.session_state.is_admin = False
        st.session_state.usuario_nome = ""
        st.session_state.setor_nome = ""

    if st.session_state.autenticado:
        return True

    session = get_session()

    # --- CORREÇÃO: GARANTIR QUE SETORES EXISTAM ---
    # Verifica se a tabela de setores está vazia. Se estiver, preenche.
    if session.query(Setor).count() == 0:
        # Lista completa de setores correta
        lista_setores = [
            "Administrativo", "NPA", "NAP", "NMP", "NSC", 
            "NSM", "NDJPL", "NOSE", "NMCHE", "NMSG", "NMN", "NLAB"
        ]
        for nome_setor in lista_setores:
            session.add(Setor(nome=nome_setor))
        session.commit() # Salva os setores no banco

    # --- CORREÇÃO: CRIAR ADMIN VINCULADO AO SETOR CORRETO ---
    if session.query(Usuario).count() == 0:
        try:
            # Busca o setor "Administrativo" que acabamos de criar
            setor_adm = session.query(Setor).filter_by(nome="Administrativo").first()
            
            # Se por algum motivo falhar, pega o primeiro da lista
            if not setor_adm:
                setor_adm = session.query(Setor).first()

            if setor_adm:
                admin = Usuario(
                    nome="Administrador",
                    login="admin",
                    senha="123",
                    is_admin=True,
                    setor_id=setor_adm.id # Vincula o ID do setor
                )
                session.add(admin)
                session.commit()
                st.toast("Admin criado com sucesso (Setor: Administrativo)", icon="🛡️")
        except Exception as e:
            session.rollback()
            st.error(f"Erro na inicialização: {e}")

    # --- INTERFACE ---
    # Layout corrigido com 3 colunas (proporção 1:4:1 para centralizar)
    col1, col2, col3 = st.columns([1, 2, 3])
    
    with col2:
        st.title("🏛️ Sistema CECOMP")
        tab_login, tab_cadastro = st.tabs(["🔑 Acessar", "📝 Novo Cadastro"])

        # ABA 1: LOGIN
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
                        
                        # Carrega o nome do setor para o App usar depois
                        if user.setor:
                            st.session_state.setor_id = user.setor.id
                            st.session_state.setor_nome = user.setor.nome
                        else:
                            st.session_state.setor_nome = "Sem Setor"

                        st.success(f"Bem-vindo(a), {user.nome}!")
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.error("Dados incorretos.")

        # ABA 2: CADASTRO CORRETO
        with tab_cadastro:
            st.info("Preencha seus dados para solicitar acesso.")
            
            # Busca os setores AGORA garantidos no banco
            opcoes_setores = session.query(Setor).order_by(Setor.nome).all()
            
            with st.form("cadastro_form"):
                nome = st.text_input("Nome Completo")
                login = st.text_input("Login Desejado")
                senha = st.text_input("Senha", type="password")
                
                # Selectbox exibindo o nome, mas retornando o Objeto Setor
                setor_selecionado = st.selectbox(
                    "Selecione seu Núcleo/Setor:",
                    options=opcoes_setores,
                    format_func=lambda x: x.nome
                )
                
                if st.form_submit_button("Criar Conta"):
                    if nome and login and senha and setor_selecionado:
                        try:
                            # Cria usuário padrão (Operador)
                            novo = Usuario(
                                nome=nome,
                                login=login,
                                senha=senha,
                                is_admin=False,
                                setor_id=setor_selecionado.id # Pega o ID do objeto selecionado
                            )
                            session.add(novo)
                            session.commit()
                            st.success("Conta criada! Vá para a aba 'Acessar' para entrar.")
                        except IntegrityError:
                            session.rollback()
                            st.error("Erro: Este login já existe.")
                    else:
                        st.warning("Preencha todos os campos.")

    return False

def logout():
    st.session_state.clear()
    st.rerun()
