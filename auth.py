import streamlit as st
import time
from sqlalchemy.exc import IntegrityError
from database import get_session
from models import Usuario, Setor

# --- ATENÇÃO: NENHUMA IMPORTAÇÃO DE 'auth' AQUI ---

def verificar_login():
    """
    Gerencia a autenticação e o cadastro de usuários.
    Retorna True se o usuário estiver autenticado, False caso contrário.
    """
    # 1. Inicializa estado da sessão
    if "autenticado" not in st.session_state:
        st.session_state.autenticado = False
        st.session_state.is_admin = False

    # 2. Se já estiver logado, libera o acesso
    if st.session_state.autenticado:
        return True

    # 3. Inicialização de Dados Básicos (Garante que existam Setores e Admin)
    session = get_session()
    
    # Cria setores padrão se a tabela estiver vazia
    if session.query(Setor).count() == 0:
        nucleos_padrao = [
            "NPA", "NAP", "NMP", "NSC", "NSM", "NDJPL", 
            "NOSE", "NMCHE", "NMSG", "NMN", "NLAB", "Administrativo"
        ]
        for n in nucleos_padrao:
            session.add(Setor(nome=n))
        session.commit()

    # Cria usuário Admin padrão se a tabela de usuários estiver vazia
    if session.query(Usuario).count() == 0:
        try:
            # Tenta vincular ao setor "Administrativo", ou pega o primeiro disponível
            setor_adm = session.query(Setor).filter_by(nome="Administrativo").first()
            if not setor_adm: 
                setor_adm = session.query(Setor).first()
            
            if setor_adm: # Só cria se houver setor
                admin = Usuario(
                    nome="Administrador", 
                    login="admin", 
                    senha="123", 
                    is_admin=True, 
                    setor_id=setor_adm.id
                )
                session.add(admin)
                session.commit()
                st.toast("Usuário 'admin' (senha: 123) criado automaticamente!", icon="🛡️")
        except Exception as e:
            session.rollback()
            # Opcional: print(f"Erro ao criar admin: {e}")

    # 4. Interface de Login (Centralizada)
    # Cria 3 colunas para que o formulário fique na do meio (col2)
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
                    # Busca usuário no banco
                    user = session.query(Usuario).filter_by(login=u, senha=p).first()
                    
                    if user:
                        # Preenche a sessão com dados do usuário
                        st.session_state.autenticado = True
                        st.session_state.usuario_nome = user.nome
                        st.session_state.is_admin = user.is_admin
                        
                        # Salva dados do setor para usar nos processos
                        st.session_state.setor_id = user.setor_id
                        st.session_state.setor_nome = user.setor.nome if user.setor else "Indefinido"
                        
                        st.success(f"Bem-vindo, {user.nome}!")
                        time.sleep(0.5)
                        st.rerun() # Recarrega para entrar no app.py
                    else:
                        st.error("Usuário ou senha incorretos.")

        # --- ABA CADASTRO ---
        with tab_cadastro:
            st.info("Seu usuário será vinculado ao Núcleo selecionado.")
            
            # Carrega lista de setores para o dropdown
            lista_nucleos = session.query(Setor).order_by(Setor.nome).all()
            
            with st.form("cadastro_form"):
                nome = st.text_input("Nome Completo")
                login = st.text_input("Login Desejado")
                senha = st.text_input("Senha", type="password")
                
                # Selectbox obrigatório para vincular ao núcleo
                nucleo_sel = st.selectbox(
                    "Selecione seu Núcleo:", 
                    options=lista_nucleos,
                    format_func=lambda x: x.nome
                )
                
                if st.form_submit_button("Cadastrar"):
                    if nome and login and senha and nucleo_sel:
                        try:
                            # Cria novo usuário (sempre is_admin=False por segurança)
                            novo = Usuario(
                                nome=nome, 
                                login=login, 
                                senha=senha, 
                                setor_id=nucleo_sel.id
                            )
                            session.add(novo)
                            session.commit()
                            st.success("Cadastro realizado! Faça login na aba ao lado.")
                        except IntegrityError:
                            session.rollback()
                            st.error("Erro: Este login já está em uso.")
                    else:
                        st.warning("Preencha todos os campos.")
    
    # Retorna False para impedir que o resto do app carregue antes do login
    return False

def logout():
    """Limpa a sessão e recarrega a página de login."""
    st.session_state.clear()
    st.rerun()
