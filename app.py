import streamlit as st
import pandas as pd
import time
import os
import shutil
from datetime import datetime
from sqlalchemy.exc import OperationalError
from auth import verificar_login, logout
from database import get_connection, get_session
from models import Base, Setor, Modalidade, FaseTemplate, Processo, Usuario

# 1. Configuração da Página
st.set_page_config(
    page_title="CECOMP - SESAU/RO", 
    layout="wide",
    page_icon="🏛️"
)

# 2. Funções Utilitárias (Backup)
def realizar_backup_automatico():
    """Cria uma cópia diária do banco se ela ainda não existir."""
    pasta_backup = "backups"
    if not os.path.exists(pasta_backup):
        os.makedirs(pasta_backup)
    
    data_hoje = datetime.now().strftime("%Y-%m-%d")
    nome_arquivo = f"backup_central_compras_{data_hoje}.db"
    caminho_completo = os.path.join(pasta_backup, nome_arquivo)
    
    if not os.path.exists(caminho_completo) and os.path.exists("central_compras.db"):
        try:
            shutil.copy2("central_compras.db", caminho_completo)
            # Opcional: print(f"Backup automático criado: {nome_arquivo}")
        except Exception as e:
            print(f"Falha no backup: {e}")

# Executa backup silencioso ao iniciar
realizar_backup_automatico()

# 3. Inicialização do Banco de Dados
conn = get_connection()
session = get_session()

# Verificação de integridade do banco (Schema Mismatch)
try:
    session.query(Usuario).first()
except OperationalError:
    # Se houver erro de coluna faltando (mudança de estrutura), reseta
    Base.metadata.drop_all(conn.engine)
    Base.metadata.create_all(conn.engine)
    st.toast("Banco de dados atualizado para nova versão!", icon="🔄")
except Exception:
    Base.metadata.create_all(conn.engine)

# Garante que as tabelas existem
Base.metadata.create_all(conn.engine)

# 4. Verificação de Login
# Se não estiver logado, para a execução aqui.
if not verificar_login():
    st.stop()

# --- MODAIS (POPUPS) ---

@st.dialog("Novo Processo")
def modal_novo_processo():
    """Formulário de cadastro vinculado ao Núcleo do usuário."""
    session = get_session()
    mods = session.query(Modalidade).all()
    
    if not mods:
        st.warning("⚠️ Nenhuma modalidade cadastrada. Contate o Admin.")
        if st.button("Fechar"): st.rerun()
        return

    # Recupera dados da sessão do usuário
    user_setor_id = st.session_state.get("setor_id")
    user_setor_nome = st.session_state.get("setor_nome", "Indefinido")

    st.caption(f"Vinculado ao Núcleo: **{user_setor_nome}**")
    
    with st.form("form_novo_processo"):
        c1, c2 = st.columns(2)
        with c1:
            sei = st.text_input("Número SEI (Único)")
            valor = st.number_input("Valor Estimado (R$)", min_value=0.0, format="%.2f")
        with c2:
            mod_sel = st.selectbox("Modalidade", mods, format_func=lambda x: x.nome)
            objeto = st.text_area("Objeto")

        if st.form_submit_button("Salvar Processo"):
            if not sei or not objeto:
                st.error("Preencha SEI e Objeto.")
            elif session.query(Processo).filter_by(numero_sei=sei).first():
                st.error("Erro: SEI já cadastrado.")
            else:
                try:
                    # Busca fase inicial automaticamente
                    fase_ini = session.query(FaseTemplate)\
                        .filter_by(modalidade_id=mod_sel.id)\
                        .order_by(FaseTemplate.ordem).first()
                    
                    novo = Processo(
                        numero_sei=sei,
                        valor_previsto=valor,
                        objeto=objeto,
                        modalidade_id=mod_sel.id,
                        fase_atual=fase_ini.nome if fase_ini else "Início",
                        setor_origem_id=user_setor_id # Vínculo automático
                    )
                    session.add(novo)
                    session.commit()
                    st.success("Processo cadastrado com sucesso!")
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    session.rollback()
                    st.error(f"Erro ao salvar: {e}")

@st.dialog("Movimentar Processo")
def modal_movimentar_processo(processo_id):
    """Edição de fase e valores de um processo existente."""
    session = get_session()
    proc = session.query(Processo).filter_by(id=processo_id).first()
    
    if not proc:
        st.error("Processo não encontrado.")
        return

    st.markdown(f"**Processo:** {proc.numero_sei}")
    st.caption(f"Objeto: {proc.objeto}")
    
    # Busca fases disponíveis para a modalidade deste processo
    fases = session.query(FaseTemplate)\
        .filter_by(modalidade_id=proc.modalidade_id)\
        .order_by(FaseTemplate.ordem).all()
    
    lista_nomes = [f.nome for f in fases]
    
    # Define índice atual para o selectbox
    idx_atual = 0
    if proc.fase_atual in lista_nomes:
        idx_atual = lista_nomes.index(proc.fase_atual)

    with st.form("form_movimentar"):
        nova_fase = st.selectbox("Nova Fase", lista_nomes, index=idx_atual)
        novo_valor = st.number_input("Atualizar Valor (R$)", value=proc.valor_previsto, format="%.2f")
        
        if st.form_submit_button("Salvar Alterações"):
            try:
                proc.fase_atual = nova_fase
                proc.valor_previsto = novo_valor
                session.commit()
                st.success("Processo atualizado!")
                time.sleep(0.5)
                st.rerun()
            except Exception as e:
                session.rollback()
                st.error(f"Erro: {e}")

# --- BARRA LATERAL ---
# Exibe o Nome do Usuário (Título)
st.sidebar.title(f"👤 {st.session_state.get('usuario_nome', 'Usuário')}")

# Exibe o Núcleo/Setor (Subtítulo/Caption)
# Se estiver 'Indefinido', algo deu errado no login ou cadastro
nome_nucleo = st.session_state.get('setor_nome', 'Indefinido')
st.sidebar.caption(f"Núcleo: **{nome_nucleo}**")

# Exibe o Perfil (Texto simples)
perfil_usuario = "Administrador" if st.session_state.get('is_admin') else "Operador"
st.sidebar.text(f"Perfil: {perfil_usuario}")

if st.sidebar.button("Sair"):
    logout()

st.sidebar.divider()
menu = st.sidebar.selectbox(
    "Navegação", 
    ["Gestão de Processos", "Configurar Modalidades (Admin)"]
)

# --- TELA 1: GESTÃO DE PROCESSOS ---
if menu == "Gestão de Processos":
    st.title("🗂️ Gestão de Processos")
    
    # Botão Novo e Filtros
    col_btn, col_busca, col_filtro = st.columns([0.2, 0.4, 0.4])
    
    with col_btn:
        st.write("") 
        st.write("") 
        if st.button("➕ Novo", type="primary", use_container_width=True):
            modal_novo_processo()
            
    with col_busca:
        busca = st.text_input("🔍 Buscar", placeholder="Digite SEI ou termo do objeto")
        
    with col_filtro:
        # Carrega setores para filtro
        all_setores = session.query(Setor).all()
        opcoes_setores = [s.nome for s in all_setores]
        filtro_setor = st.multiselect("Filtrar por Núcleo:", opcoes_setores)

    st.divider()

    # Query Principal (Join com Setor e Modalidade)
    query = session.query(
        Processo.id, Processo.numero_sei, Processo.objeto, 
        Processo.valor_previsto, Processo.fase_atual, Processo.data_autorizacao,
        Setor.nome.label("setor"), Modalidade.nome.label("modalidade")
    ).outerjoin(Setor, Processo.setor_origem_id == Setor.id)\
     .outerjoin(Modalidade, Processo.modalidade_id == Modalidade.id)
    
    # Carrega DataFrame
    df = pd.read_sql(query.statement, session.bind)
    
    if not df.empty:
        # Filtros Python (Pandas)
        if busca:
            mask = df['numero_sei'].str.contains(busca, case=False, na=False) | \
                   df['objeto'].str.contains(busca, case=False, na=False)
            df = df[mask]
            
        if filtro_setor:
            df = df[df['setor'].isin(filtro_setor)]

        # Área de Edição (Seleção + Botão)
        with st.container(border=True):
            c_sel, c_abrir = st.columns([0.8, 0.2])
            with c_sel:
                # Selectbox formatado para facilitar identificação
                proc_id_editar = st.selectbox(
                    "✏️ Selecione para Editar/Movimentar:",
                    df['id'].tolist(),
                    format_func=lambda x: f"{df[df['id']==x]['numero_sei'].values} - {df[df['id']==x]['objeto'].values[:60]}..."
                )
            with c_abrir:
                st.write("")
                st.write("")
                if st.button("Abrir Processo", use_container_width=True):
                    modal_movimentar_processo(proc_id_editar)

        # Métricas
        m1, m2 = st.columns(2)
        m1.metric("Quantidade", len(df))
        m1.metric("Volume Total", f"R$ {df['valor_previsto'].sum():,.2f}")

        # Tabela
        st.dataframe(
            df,
            column_config={
                "numero_sei": "SEI",
                "objeto": "Objeto",
                "setor": "Núcleo",
                "modalidade": "Modalidade",
                "fase_atual": "Fase Atual",
                "valor_previsto": st.column_config.NumberColumn("Valor", format="R$ %.2f"),
                "data_autorizacao": st.column_config.DatetimeColumn("Data", format="DD/MM/YYYY"),
            },
            hide_index=True,
            use_container_width=True
        )
    else:
        st.info("Nenhum processo encontrado.")

# --- TELA 2: ADMINISTRAÇÃO ---
elif menu == "Configurar Modalidades (Admin)":
    
    if not st.session_state.get("is_admin"):
        st.error("⛔ Acesso Negado.")
        st.stop()

    tab_mods, tab_bkp = st.tabs(["⚙️ Modalidades", "💾 Backup e Dados"])

    # ABA 1: MODALIDADES
    with tab_mods:
        st.title("Gestão de Fluxos")
        
        with st.form("form_modalidade"):
            nome_mod = st.text_input("Nome da Modalidade")
            st.caption("Defina o fluxo de fases abaixo (uma por linha):")
            
            padrao = [
                "Recepção na CECOMP", "Primeira Análise do Núcleo", "Pesquisa de Preços / ETP / Risco",
                "Elaboração de TR", "Primeira Análise da SUPEL", "Correção/Ajuste do TR",
                "Elaboração de Edital", "Análise Jurídica", "Correção/Ajuste do Edital",
                "Publicação do Pregão", "Recepção de Propostas", "Análise Técnica",
                "Recurso/Reanálise (Técnico)", "Habilitação", "Recurso/Reanálise (Habilitação)",
                "Análise para Homologação", "Homologação", "Elaboração da Ata",
                "Comunicação Publicação da Ata", "Finalizado"
            ]
            
            texto_fases = st.text_area("Fases", value="\n".join(padrao), height=300)
            
            if st.form_submit_button("Salvar Estrutura"):
                lista = [f.strip() for f in texto_fases.split('\n') if f.strip()]
                if nome_mod and lista:
                    try:
                        nm = Modalidade(nome=nome_mod)
                        session.add(nm)
                        session.flush()
                        for i, f in enumerate(lista):
                            session.add(FaseTemplate(nome=f, ordem=i+1, modalidade_id=nm.id))
                        session.commit()
                        st.success(f"Modalidade '{nome_mod}' criada!")
                    except Exception as e:
                        session.rollback()
                        st.error(f"Erro: {e}")
                else:
                    st.warning("Preencha nome e fases.")

        st.divider()
        st.subheader("Modalidades Ativas")
        for m in session.query(Modalidade).all():
            with st.expander(f"📂 {m.nome}"):
                fs = session.query(FaseTemplate).filter_by(modalidade_id=m.id).order_by(FaseTemplate.ordem).all()
                for f in fs:
                    st.text(f"{f.ordem}. {f.nome}")

    # ABA 2: BACKUPS
    with tab_bkp:
        st.title("Segurança de Dados")
        st.info("Backups automáticos são gerados diariamente na pasta /backups.")
        
        # Download Manual
        if os.path.exists("central_compras.db"):
            with open("central_compras.db", "rb") as f:
                st.download_button(
                    label="📥 Baixar Banco de Dados Atual (.db)",
                    data=f,
                    file_name=f"backup_manual_{datetime.now().strftime('%Y%m%d_%H%M')}.db",
                    mime="application/x-sqlite3"
                )
        
        st.divider()
        st.subheader("Histórico Automático")
        pasta = "backups"
        if os.path.exists(pasta):
            arquivos = [f for f in os.listdir(pasta) if f.endswith(".db")]
            arquivos.sort(reverse=True)
            if arquivos:
                st.dataframe(pd.DataFrame(arquivos, columns=["Arquivo"]), use_container_width=True)
            else:
                st.caption("Nenhum backup automático ainda.")
