import streamlit as st
import time
from sqlalchemy.exc import IntegrityError
from database import get_session
from models import Usuario, Setor

# NÃO importe 'auth' aqui dentro para evitar erro circular.

def verificar_login():
    """
    Gerencia Login e Cadastro. Garante que todo usuário tenha um Setor.
    """
    # Inicializa variáveis de sessão
    if "autenticado" not in st.session_state:
        st.session_state.autenticado = False
        st.session_state.is_admin = False
        st.session_state.usuario_nome = ""
        st.session_state.setor_nome = ""

    if st.session_state.autenticado:
        return True

    session = get_session()

    # --- AUTO-CONFIGURAÇÃO INICIAL ---
    # 1. Cria Setores se não existirem
    if session.query(Setor).count() == 0:
        nucleos = [
            "Administrativo", "NPA", "NAP", "NMP", "NSC", 
            "NSM", "NDJPL", "NOSE", "NMCHE", "NMSG", "NMN", "NLAB"
        ]
        for n in nucleos:
            session.add(Setor(nome=n))
        session.commit()

    # 2. Cria Usuário ADMIN se não existir
    if session.query(Usuario).count() == 0:
        try:
            # Busca o setor Administrativo para vincular o chefe
            setor_adm = session.query(Setor).filter_by(nome="Administrativo").first()
            # Segurança caso algo falhe na busca
            if not setor_adm: 
                setor_adm = session.query(Setor).first()

            admin = Usuario(
                nome="Administrador",
                login="admin",
                senha="123",
                is_admin=True, # PERMISSÃO TOTAL
                setor_id=setor_adm.id
            )
            session.add(admin)
            session.commit()
            st.toast("Usuário 'admin' (senha: 123) criado com sucesso!", icon="🛡️")
        except Exception as e:
            session.rollback()
            st.error(f"Erro ao criar admin: {e}")

    # --- INTERFACE DE ACESSO ---
    # Layout centralizado usando 3 colunas [3]
    col1, col2, col3 = st.columns([4, 5])
    
    with col2:
        st.title("🏛️ Acesso CECOMP")
        tab_login, tab_cadastro = st.tabs(["🔑 Login", "📝 Novo Cadastro"])

        # ABA 1: LOGIN
        with tab_login:
            with st.form("login_form"):
                u = st.text_input("Usuário")
                p = st.text_input("Senha", type="password")
                
                if st.form_submit_button("Entrar", type="primary"):
                    user = session.query(Usuario).filter_by(login=u, senha=p).first()
                    
                    if user:
                        # CARREGA PERMISSÕES E DADOS NA SESSÃO [6][2]
                        st.session_state.autenticado = True
                        st.session_state.usuario_nome = user.nome
                        st.session_state.usuario_login = user.login
                        st.session_state.is_admin = user.is_admin # Define se vê menu Admin
                        
                        # Carrega o nome do setor (importante para o dashboard)
                        st.session_state.setor_id = user.setor_id
                        st.session_state.setor_nome = user.setor.nome if user.setor else "Geral"
                        
                        st.success(f"Bem-vindo(a), {user.nome}!")
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.error("Usuário ou senha incorretos.")

        # ABA 2: CADASTRO DE NOVOS USUÁRIOS
        with tab_cadastro:
            st.info("Crie sua conta. Seu perfil será de Operador.")
            
            # Carrega lista de setores para o Selectbox [1]
            todos_setores = session.query(Setor).order_by(Setor.nome).all()
            
            with st.form("cadastro_form"):
                nome_novo = st.text_input("Nome Completo")
                login_novo = st.text_input("Login de Acesso")
                senha_nova = st.text_input("Senha", type="password")
                
                # OBRIGATÓRIO: Escolher o Núcleo
                setor_escolhido = st.selectbox(
                    "Selecione seu Núcleo:",
                    options=todos_setores,
                    format_func=lambda x: x.nome
                )
                
                if st.form_submit_button("Criar Conta"):
                    if nome_novo and login_novo and senha_nova and setor_escolhido:
                        try:
                            novo_usuario = Usuario(
                                nome=nome_novo,
                                login=login_novo,
                                senha=senha_nova,
                                is_admin=False, # Novos usuários nunca são admin por padrão
                                setor_id=setor_escolhido.id # VINCULA AO ID DO SETOR
                            )
                            session.add(novo_usuario)
                            session.commit()
                            st.success("Cadastro realizado! Vá para a aba de Login para entrar.")
                        except IntegrityError:
                            session.rollback()
                            st.error("Este login já existe. Escolha outro.")
                    else:
                        st.warning("Preencha todos os campos.")

    return False

def logout():
    st.session_state.clear()
    st.rerun()
