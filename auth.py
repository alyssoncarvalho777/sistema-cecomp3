import streamlit as st
import time
from sqlalchemy.exc import IntegrityError
from database import get_session
from models import Usuario, Setor

def verificar_login():
    """
    Gerencia Login e Cadastro com vinculação obrigatória de Núcleo.
    """
    if "autenticado" not in st.session_state:
        st.session_state.autenticado = False
        st.session_state.is_admin = False

    if st.session_state.autenticado:
        return True

    # Garante que os Setores/Núcleos existam no banco antes de desenhar a tela
    session = get_session()
    if session.query(Setor).count() == 0:
        nucleos_padrao = [
            "NPA", "NAP", "NMP", "NSC", "NSM", "NDJPL", 
            "NOSE", "NMCHE", "NMSG", "NMN", "NLAB", "Administrativo"
        ]
        for n in nucleos_padrao:
            session.add(Setor(nome=n))
        session.commit()

    # Layout Centralizado
    col1, col2, col3 = st.columns([2, 3]) # [2, 4] gerava erro, usando 3 valores agora.
    
    with col2:
        st.title("🏛️ CECOMP - SESAU/RO")
        
        tab_login, tab_cadastro = st.tabs(["🔑 Acessar", "📝 Criar Conta"])

        # --- ABA LOGIN ---
        with tab_login:
            with st.form("login_form"):
                u = st.text_input("Usuário")
                p = st.text_input("Senha", type="password")
                
                if st.form_submit_button("Entrar", type="primary"):
                    # Verifica se é o primeiro acesso absoluto (Banco vazio de usuários)
                    if session.query(Usuario).count() == 0:
                        try:
                            # Tenta pegar o setor Administrativo ou o primeiro que tiver
                            setor_adm = session.query(Setor).filter_by(nome="Administrativo").first()
                            if not setor_adm: setor_adm = session.query(Setor).first()
                            
                            admin = Usuario(
                                nome="Administrador", login="admin", senha="123", 
                                is_admin=True, setor_id=setor_adm.id
                            )
                            session.add(admin)
                            session.commit()
                            st.toast("Admin criado (admin/123)", icon="🛡️")
                        except Exception:
                            session.rollback()

                    # Busca usuário e carrega seus dados (incluindo o setor)
                    user = session.query(Usuario).filter_by(login=u, senha=p).first()
                    
                    if user:
                        st.session_state.autenticado = True
                        st.session_state.usuario_nome = user.nome
                        st.session_state.is_admin = user.is_admin
                        
                        # SALVA O NÚCLEO NA SESSÃO
                        st.session_state.setor_id = user.setor_id
                        st.session_state.setor_nome = user.setor.nome if user.setor else "Geral"
                        
                        st.success(f"Bem-vindo, {user.nome} ({st.session_state.setor_nome})")
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.error("Dados incorretos.")

        # --- ABA CADASTRO (COM NÚCLEO) ---
        with tab_cadastro:
            st.info("O seu usuário será vinculado ao Núcleo selecionado abaixo.")
            
            # Busca lista de núcleos para o selectbox
            lista_nucleos = session.query(Setor).order_by(Setor.nome).all()
            
            with st.form("cadastro_form"):
                nome = st.text_input("Nome Completo")
                login = st.text_input("Login")
                senha = st.text_input("Senha", type="password")
                
                # SELEÇÃO DO NÚCLEO [5]
                nucleo_selecionado = st.selectbox(
                    "Selecione seu Núcleo:", 
                    options=lista_nucleos,
                    format_func=lambda x: x.nome
                )
                
                if st.form_submit_button("Cadastrar"):
                    if nome and login and senha and nucleo_selecionado:
                        try:
                            novo = Usuario(
                                nome=nome, 
                                login=login, 
                                senha=senha,
                                setor_id=nucleo_selecionado.id # Vincula ao ID do objeto selecionado
                            )
                            session.add(novo)
                            session.commit()
                            st.success("Conta criada! Faça login.")
                        except IntegrityError:
                            session.rollback()
                            st.error("Login já existe.")
                    else:
                        st.warning("Preencha todos os campos.")
    
    return False

def logout():
    st.session_state.clear() # Limpa tudo (nome, admin, setor_id)
    st.rerun()
