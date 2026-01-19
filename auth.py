import streamlit as st
import pandas as pd
from sqlalchemy.exc import OperationalError
from database import get_connection, get_session
from models import Base, Setor, Modalidade, FaseTemplate, Processo, Usuario

st.set_page_config(page_title="CECOMP - SESAU/RO", layout="wide", page_icon="🏛️")

conn = get_connection()
session = get_session()

# --- RECUPERAÇÃO AUTOMÁTICA DE BANCO DE DADOS ---
# Se a estrutura mudou (novas colunas setor_id), reseta o banco.
try:
    session.query(Usuario).first()
except OperationalError:
    Base.metadata.drop_all(conn.engine)
    Base.metadata.create_all(conn.engine)
    st.toast("Banco atualizado para nova estrutura de Núcleos.", icon="🔄")
except Exception:
    Base.metadata.create_all(conn.engine)

# Garante criação das tabelas
Base.metadata.create_all(conn.engine)

# Autenticação
if not verificar_login():
    st.stop()

# --- MODAL DE NOVO PROCESSO (AUTO-VINCULADO AO NÚCLEO) ---
@st.dialog("Novo Processo")
def modal_novo_processo():
    session = get_session()
    mods = session.query(Modalidade).all()
    
    if not mods:
        st.warning("Sem modalidades cadastradas.")
        if st.button("Fechar"): st.rerun()
        return

    # Recupera o Núcleo do usuário logado da sessão [1]
    user_setor_id = st.session_state.get("setor_id")
    user_setor_nome = st.session_state.get("setor_nome", "Indefinido")

    st.caption(f"Este processo será vinculado automaticamente ao: **{user_setor_nome}**")
    
    with st.form("form_novo_processo_modal"):
        c1, c2 = st.columns(2)
        with c1:
            sei = st.text_input("Número SEI")
            valor = st.number_input("Valor (R$)", min_value=0.0, format="%.2f")
        with c2:
            mod_sel = st.selectbox("Modalidade", mods, format_func=lambda x: x.nome)
            objeto = st.text_area("Objeto")

        if st.form_submit_button("Salvar Processo"):
            if not sei or not objeto:
                st.error("Preencha SEI e Objeto.")
            elif session.query(Processo).filter_by(numero_sei=sei).first():
                st.error("SEI já existe.")
            else:
                try:
                    fase_ini = session.query(FaseTemplate)\
                        .filter_by(modalidade_id=mod_sel.id)\
                        .order_by(FaseTemplate.ordem).first()
                    
                    novo = Processo(
                        numero_sei=sei,
                        valor_previsto=valor,
                        objeto=objeto,
                        modalidade_id=mod_sel.id,
                        fase_atual=fase_ini.nome if fase_ini else "Início",
                        
                        # VINCULAÇÃO AUTOMÁTICA AQUI:
                        setor_origem_id=user_setor_id 
                    )
                    session.add(novo)
                    session.commit()
                    st.success("Processo salvo!")
                    st.rerun()
                except Exception as e:
                    session.rollback()
                    st.error(f"Erro: {e}")

# --- INTERFACE PRINCIPAL ---
st.sidebar.title(f"👤 {st.session_state.usuario_nome}")
st.sidebar.caption(f"Núcleo: **{st.session_state.get('setor_nome')}**") # Mostra o núcleo no menu

if st.sidebar.button("Sair"):
    logout()

st.sidebar.divider()
menu = st.sidebar.selectbox("Navegação", ["Gestão de Processos", "Configurar Modalidades (Admin)"])

if menu == "Gestão de Processos":
    st.title("🗂️ Gestão de Processos")
    
    col_btn, col_busca, col_filtro = st.columns([0.2, 0.4, 0.4])
    
    with col_btn:
        st.write("") 
        st.write("") 
        if st.button("➕ Novo", type="primary", use_container_width=True):
            modal_novo_processo()
            
    with col_busca:
        busca = st.text_input("🔍 Buscar", placeholder="SEI ou Objeto...")
        
    with col_filtro:
        # Filtro visual para ver processos de outros núcleos
        setores = session.query(Setor).all()
        nomes_setores = [s.nome for s in setores]
        filtro_setor = st.multiselect("Filtrar Núcleo:", options=nomes_setores)

    st.divider()

    # Query trazendo o nome do setor do banco
    query = session.query(
        Processo.id, Processo.numero_sei, Processo.objeto, 
        Processo.valor_previsto, Processo.fase_atual, Processo.data_autorizacao,
        Setor.nome.label("setor"), Modalidade.nome.label("modalidade")
    ).outerjoin(Setor, Processo.setor_origem_id == Setor.id)\
     .outerjoin(Modalidade, Processo.modalidade_id == Modalidade.id) # [6]
    
    df = pd.read_sql(query.statement, session.bind) # [7]
    
    if not df.empty:
        if busca:
            mask = df['numero_sei'].str.contains(busca, case=False, na=False) | \
                   df['objeto'].str.contains(busca, case=False, na=False)
            df = df[mask]
        
        if filtro_setor:
            df = df[df['setor'].isin(filtro_setor)]

        st.dataframe(
            df,
            column_config={
                "numero_sei": "SEI",
                "objeto": "Objeto",
                "setor": "Núcleo Origem",
                "valor_previsto": st.column_config.NumberColumn("Valor", format="R$ %.2f"),
                "data_autorizacao": st.column_config.DatetimeColumn("Data", format="DD/MM/YYYY"),
            },
            hide_index=True,
            use_container_width=True
        )
    else:
        st.info("Nenhum processo encontrado.")

elif menu == "Configurar Modalidades (Admin)":
    if not st.session_state.is_admin:
        st.error("Acesso restrito.")
        st.stop()
    
    # ... (Código de configuração de modalidades permanece igual ao anterior) ...
    st.title("⚙️ Configurar Modalidades")
    # (Copie o código da resposta anterior para esta seção se necessário, 
    # pois ele não muda com a lógica de setores)
