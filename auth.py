import streamlit as st
import pandas as pd
from sqlalchemy.exc import OperationalError
from auth import verificar_login, logout
from database import get_connection, get_session
from models import Base, Setor, Modalidade, FaseTemplate, Processo, Usuario

# 1. Configuração Inicial
st.set_page_config(page_title="CECOMP - SESAU/RO", layout="wide", page_icon="🏛️")

# 2. Inicialização Segura do Banco de Dados
conn = get_connection()
session = get_session()

try:
    # Teste de integridade: Tenta ler um usuário. 
    # Se a coluna 'is_admin' não existir (banco antigo), vai gerar erro.
    session.query(Usuario).first()
except OperationalError:
    # Se der erro, recria o banco automaticamente
    Base.metadata.drop_all(conn.engine)
    Base.metadata.create_all(conn.engine)
    st.toast("Banco de dados atualizado para nova versão!", icon="🔄")
except Exception:
    # Criação padrão se o arquivo não existir
    Base.metadata.create_all(conn.engine)

# Garante que tabelas existam
Base.metadata.create_all(conn.engine)

# 3. Verificação de Login
if not verificar_login():
    st.stop()

# --- FUNÇÃO DO MODAL (POPUP) ---
@st.dialog("Novo Processo")
def modal_novo_processo():
    """Formulário de cadastro dentro de um modal."""
    session = get_session()
    mods = session.query(Modalidade).all()
    setores = session.query(Setor).all()
    
    # Se não houver dados básicos, avisa e para
    if not mods:
        st.warning("⚠️ Nenhuma modalidade cadastrada. Contate o Administrador.")
        if st.button("Fechar"):
            st.rerun()
        return

    # Se não houver setores, cria padrões automaticamente
    if not setores:
        padroes = ["NPA", "NAP", "NMP", "NSC", "NSM", "NDJPL", "NOSE", "NMCHE", "NMSG", "NMN", "NLAB"]
        for s in padroes:
            session.add(Setor(nome=s))
        session.commit()
        setores = session.query(Setor).all()

    st.caption("Preencha os dados do processo.")
    
    with st.form("form_novo_processo_modal"):
        c1, c2 = st.columns(2)
        with c1:
            sei = st.text_input("Número SEI")
            valor = st.number_input("Valor (R$)", min_value=0.0, format="%.2f")
            setor_sel = st.selectbox("Setor Origem", setores, format_func=lambda x: x.nome)
        with c2:
            mod_sel = st.selectbox("Modalidade", mods, format_func=lambda x: x.nome)
            objeto = st.text_area("Objeto")

        if st.form_submit_button("Salvar Processo"):
            if not sei or not objeto:
                st.error("Preencha SEI e Objeto.")
            elif session.query(Processo).filter_by(numero_sei=sei).first():
                st.error("Erro: SEI já existe.")
            else:
                try:
                    # Define fase inicial automaticamente
                    fase_ini = session.query(FaseTemplate)\
                        .filter_by(modalidade_id=mod_sel.id)\
                        .order_by(FaseTemplate.ordem).first()
                    
                    novo = Processo(
                        numero_sei=sei,
                        valor_previsto=valor,
                        objeto=objeto,
                        modalidade_id=mod_sel.id,
                        setor_origem_id=setor_sel.id,
                        fase_atual=fase_ini.nome if fase_ini else "Início"
                    )
                    session.add(novo)
                    session.commit()
                    st.success("Processo salvo!")
                    st.rerun()
                except Exception as e:
                    session.rollback()
                    st.error(f"Erro: {e}")

# --- MENU LATERAL ---
st.sidebar.title(f"👤 {st.session_state.usuario_nome}")
perfil = "Administrador" if st.session_state.is_admin else "Operador"
st.sidebar.caption(f"Perfil: **{perfil}**")

if st.sidebar.button("Sair"):
    logout()

st.sidebar.divider()
menu = st.sidebar.selectbox(
    "Navegação", 
    ["Gestão de Processos", "Configurar Modalidades (Admin)"]
)

# --- TELA 1: GESTÃO DE PROCESSOS (DASHBOARD + LISTAGEM) ---
if menu == "Gestão de Processos":
    st.title("🗂️ Gestão de Processos")
    
    # Área de Ação e Filtros
    col_btn, col_busca, col_filtro = st.columns([0.2, 0.4, 0.4])
    
    with col_btn:
        st.write("") 
        st.write("") 
        # Botão que abre o Modal
        if st.button("➕ Novo", type="primary", use_container_width=True):
            modal_novo_processo()
            
    with col_busca:
        busca = st.text_input("🔍 Buscar", placeholder="SEI ou Objeto...")
        
    with col_filtro:
        lista_setores = session.query(Setor).all()
        opcoes_setores = [s.nome for s in lista_setores]
        filtro_setor = st.multiselect("Filtrar por Setor:", options=opcoes_setores)

    st.divider()

    # Query com Joins para trazer nomes em vez de IDs
    query = session.query(
        Processo.id, Processo.numero_sei, Processo.objeto, 
        Processo.valor_previsto, Processo.fase_atual, Processo.data_autorizacao,
        Setor.nome.label("setor"), Modalidade.nome.label("modalidade")
    ).outerjoin(Setor).outerjoin(Modalidade)
    
    df = pd.read_sql(query.statement, session.bind)
    
    if not df.empty:
        # Aplicação de Filtros no DataFrame
        if busca:
            mask = df['numero_sei'].str.contains(busca, case=False, na=False) | \
                   df['objeto'].str.contains(busca, case=False, na=False)
            df = df[mask]
            
        if filtro_setor:
            df = df[df['setor'].isin(filtro_setor)]

        # Métricas
        m1, m2 = st.columns(2)
        m1.metric("Quantidade", len(df))
        m1.metric("Total Financeiro", f"R$ {df['valor_previsto'].sum():,.2f}")
        
        # Tabela Formatada
        st.dataframe(
            df,
            column_config={
                "numero_sei": "SEI",
                "objeto": "Objeto",
                "setor": "Setor",
                "modalidade": "Modalidade",
                "fase_atual": "Fase Atual",
                "valor_previsto": st.column_config.NumberColumn("Valor", format="R$ %.2f"),
                "data_autorizacao": st.column_config.DatetimeColumn("Data", format="DD/MM/YYYY"),
            },
            hide_index=True,
            use_container_width=True,
            height=450
        )
    else:
        st.info("Nenhum processo encontrado.")

# --- TELA 2: ADMINISTRAÇÃO (MODALIDADES E FASES) ---
elif menu == "Configurar Modalidades (Admin)":
    
    # Bloqueio de Segurança
    if not st.session_state.is_admin:
        st.error("⛔ Acesso restrito a administradores.")
        st.stop()

    st.title("⚙️ Gestão de Modalidades")
    st.markdown("Crie modalidades e edite o fluxo de fases livremente abaixo.")
    
    with st.form("admin_modalidades"):
        nome_mod = st.text_input("Nome da Modalidade (ex: Pregão Eletrônico)")
        
        st.write("---")
        st.caption("Edite as fases abaixo (uma por linha). Você pode inserir fases intermediárias onde quiser.")
        
        # Lista padrão sugerida carregada no Text Area
        padrao = [
            "Recepção na CECOMP", "Primeira Análise do Núcleo", "Pesquisa de Preços / ETP / Risco",
            "Elaboração de TR", "Primeira Análise da SUPEL", "Correção/Ajuste do TR",
            "Elaboração de Edital", "Análise Jurídica", "Correção/Ajuste do Edital",
            "Publicação do Pregão", "Recepção de Propostas", "Análise Técnica",
            "Recurso/Reanálise (Técnico)", "Habilitação", "Recurso/Reanálise (Habilitação)",
            "Análise para Homologação", "Homologação", "Elaboração da Ata",
            "Comunicação Publicação da Ata", "Finalizado"
        ]
        
        texto_fases = st.text_area("Fluxo de Fases", value="\n".join(padrao), height=400)
        
        if st.form_submit_button("Salvar Modalidade"):
            # Converte texto em lista, removendo vazios
            lista_fases = [f.strip() for f in texto_fases.split('\n') if f.strip()]
            
            if not nome_mod or not lista_fases:
                st.warning("Nome e fases são obrigatórios.")
            else:
                try:
                    nova_m = Modalidade(nome=nome_mod)
                    session.add(nova_m)
                    session.flush() # Gera ID
                    
                    for i, nome_f in enumerate(lista_fases):
                        session.add(FaseTemplate(
                            nome=nome_f,
                            ordem=i+1,
                            modalidade_id=nova_m.id
                        ))
                    
                    session.commit()
                    st.success(f"Modalidade '{nome_mod}' cadastrada com {len(lista_fases)} fases.")
                except Exception as e:
                    session.rollback()
                    st.error(f"Erro: {e}")

    # Lista Modalidades Existentes
    st.divider()
    st.subheader("Modalidades Ativas")
    mods_db = session.query(Modalidade).all()
    for m in mods_db:
        with st.expander(f"📂 {m.nome}"):
            fases = session.query(FaseTemplate).filter_by(modalidade_id=m.id).order_by(FaseTemplate.ordem).all()
            for f in fases:
                st.text(f"{f.ordem}. {f.nome}")
