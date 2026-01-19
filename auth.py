import streamlit as st
import time
from sqlalchemy.exc import IntegrityError
from database import get_session
from models import Usuario

# --- NOTA: Não fazemos "from auth import..." aqui para evitar erro circular ---

def verificar_login():
    """
    Controla o acesso ao sistema.
    Retorna True se autenticado, False caso contrário.
    Gerencia Login e Cadastro de novos usuários.
    """
    # 1. Inicializa variáveis de sessão se não existirem 
    if "autenticado" not in st.session_state:
        st.session_state.autenticado = False
        st.session_state.is_admin = False

    # 2. Se já estiver logado, libera o acesso imediatamente
    if st.session_state.autenticado:
        return True

    # 3. Interface de Login (Centralizada)
    col1, col2, col3 = st.columns([2, 3]) # Coluna do meio mais larga para o form
    
    with col2:
        st.title("🏛️ CECOMP - SESAU/RO")
        
        # Cria abas para alternar entre entrar e criar conta 
        tab_login, tab_cadastro = st.tabs(["🔑 Acessar", "📝 Criar Conta"])

        # --- ABA DE LOGIN ---
        with tab_login:
            with st.form("login_form"): # 
                u = st.text_input("Usuário")
                p = st.text_input("Senha", type="password") # 
                
                # Botão de submissão do formulário
                if st.form_submit_button("Entrar", type="primary"):
                    session = get_session()
                    
                    # ROTINA DE PRIMEIRO ACESSO:
                    # Se não houver nenhum usuário no banco, cria o Admin automaticamente.
                    if session.query(Usuario).count() == 0:
                        try:
                            admin = Usuario(
                                nome="Administrador", 
                                login="admin", 
                                senha="123", 
                                is_admin=True # Define como admin
                            )
                            session.add(admin)
                            session.commit()
                            st.toast("Usuário 'admin' criado automaticamente!", icon="🛡️") # 
                        except Exception as e:
                            session.rollback()
                            st.error(f"Erro ao criar admin: {e}")

                    # Validação de Credenciais
                    user = session.query(Usuario).filter_by(login=u, senha=p).first()
                    
                    if user:
                        # Atualiza o estado da sessão [1]
                        st.session_state.autenticado = True
                        st.session_state.usuario_nome = user.nome
                        st.session_state.is_admin = user.is_admin
                        
                        st.success("Login realizado com sucesso!")
                        time.sleep(0.5)
                        st.rerun() # Recarrega a página para entrar no app 
                    else:
                        st.error("Usuário ou senha incorretos.")

        # --- ABA DE CADASTRO ---
        with tab_cadastro:
            st.info("Novos cadastros possuem perfil de acesso básico (Operador).")
            
            with st.form("cadastro_form"):
                nome_novo = st.text_input("Nome Completo")
                login_novo = st.text_input("Usuário Desejado")
                senha_novo = st.text_input("Senha", type="password")
                
                if st.form_submit_button("Cadastrar"):
                    # Validação simples de campos vazios
                    if nome_novo and login_novo and senha_novo:
                        session = get_session()
                        try:
                            # Cria usuário comum (is_admin=False por padrão no models.py)
                            novo = Usuario(nome=nome_novo, login=login_novo, senha=senha_novo)
                            session.add(novo)
                            session.commit()
                            st.success("Conta criada! Faça login na aba ao lado.")
                        except IntegrityError:
                            # Captura erro se o login já existir (unique=True)
                            session.rollback()
                            st.error("Erro: Este nome de usuário já está em uso.")
                    else:
                        st.warning("Preencha todos os campos para cadastrar.")
    
    # Retorna False para impedir que o resto do app (app.py) carregue antes do login
    return False

def logout():
    """Limpa a sessão e recarrega a página."""
    st.session_state.autenticado = False
    st.session_state.usuario_nome = ""
    st.session_state.is_admin = False
    st.rerun() #
