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
    page_title="Central CECOMP", 
    layout="wide",
    page_icon="🏛️"
)

# 2. Backup Automático
def realizar_backup_automatico():
    pasta_backup = "backups"
    if not os.path.exists(pasta_backup): os.makedirs(pasta_backup)
    data_hoje = datetime.now().strftime("%Y-%m-%d")
    caminho = os.path.join(pasta_backup, f"backup_{data_hoje}.db")
    if not os.path.exists(caminho) and os.path.exists("central_compras.db"):
        try: shutil.copy2("central_compras.db", caminho)
        except: pass

realizar_backup_automatico()

# 3. Conexão e Verificação de Banco
conn = get_connection()
session = get_session()

# Cria tabelas se não existirem
try:
    Base.metadata.create_all(conn.engine)
except Exception:
    pass

# 4. Autenticação (Bloqueio)
if not verificar_login():
    st.stop()

# --- FUNÇÕES DE MODAL (POP-UPS) ---

@st.dialog("Novo Processo")
def modal_novo_processo():
    """Formulário de cadastro vinculado ao Núcleo do usuário."""
    session = get_session()
    mods = session.query(Modalidade).all()
    
    # Recupera o setor do usuário logado
    meu_setor_id = st.session_state.get("setor_id")
    meu_setor_nome = st.session_state.get("setor_nome", "Indefinido")

    if not mods:
        st.error("Não há modalidades cadastradas no sistema.")
        return

    st.markdown(f"**Núcleo Responsável:** {meu_setor_nome}")
    
    with st.form("form_novo_processo"):
        c1, c2 = st.columns(2)
        with c1:
            sei = st.text_input("Número SEI (Único)")
            valor = st.number_input("Valor Estimado (R$)", min_value=0.0, format="%.2f")
        with c2:
            mod_sel = st.selectbox("Modalidade", mods, format_func=lambda x: x.nome)
            objeto = st.text_area("Objeto / Descrição")

        if st.form_submit_button("💾 Salvar Processo", type="primary"):
            if not sei or not objeto:
                st.warning("Preencha o SEI e o Objeto.")
                return
            
            # Verifica duplicidade
            existe = session.query(Processo).filter_by(numero_sei=sei).first()
            if existe:
                st.error("Este número SEI já está cadastrado.")
                return

            try:
                # Pega a primeira fase da modalidade escolhida
                fase_ini = session.query(FaseTemplate)\
                    .filter_by(modalidade_id=mod_sel.id)\
                    .order_by(FaseTemplate.ordem).first()
                
                novo = Processo(
                    numero_sei=sei,
                    valor_previsto=valor,
                    objeto=objeto,
                    modalidade_id=mod_sel.id,
                    fase_atual=fase_ini.nome if fase_ini else "Início",
                    setor_origem_id=meu_setor_id # Vínculo automático
                )
                session.add(novo)
                session.commit()
                st.success("Processo cadastrado!")
                time.sleep(1)
                st.rerun()
            except Exception as e:
                session.rollback()
                st.error(f"Erro ao salvar: {e}")

@st.dialog("Gerenciar Processo")
def modal_movimentar_processo(processo_id):
    """Edição de Fase e Dados Cadastrais"""
    session = get_session()
    proc = session.query(Processo).filter_by(id=processo_id).first()
    
    if not proc:
        st.error("Processo não encontrado.")
        return

    st.subheader(f"SEI: {proc.numero_sei}")
    
    # Busca fases disponíveis
    fases = session.query(FaseTemplate)\
        .filter_by(modalidade_id=proc.modalidade_id)\
        .order_by(FaseTemplate.ordem).all()
    lista_fases = [f.nome for f in fases]
    
    idx_fase = 0
    if proc.fase_atual in lista_fases:
        idx_fase = lista_fases.index(proc.fase_atual)

    with st.form("form_editar"):
        # Campo de Fase (Destaque)
        st.markdown("### 🔄 Atualização de Status")
        nova_fase = st.selectbox("Fase Atual", lista_fases, index=idx_fase)
        
        st.divider()
        st.markdown("### ✏️ Dados do Processo")
        
        # Campos editáveis
        novo_objeto = st.text_area("Objeto", value=proc.objeto)
        novo_valor = st.number_input("Valor (R$)", value=proc.valor_previsto, format="%.2f")
        
        c_btn1, c_btn2 = st.columns(2)
        with c_btn1:
            salvar = st.form_submit_button("✅ Salvar Alterações", type="primary")
        
    if salvar:
        try:
            proc.fase_atual = nova_fase
            proc.objeto = novo_objeto
            proc.valor_previsto = novo_valor
            session.commit()
            st.success("Processo atualizado com sucesso!")
            time.sleep(1)
            st.rerun()
        except Exception as e:
            session.rollback()
            st.error(f"Erro: {e}")

# --- BARRA LATERAL ---
meu_setor_nome = st.session_state.get('setor_nome', 'Geral')
usuario_nome = st.session_state.get('usuario_nome', 'Usuário')

st.sidebar.title(f"👤 {usuario_nome}")
st.sidebar.caption(f"Núcleo: **{meu_setor_nome}**")

if st.session_state.get('is_admin'):
    st.sidebar.info("Perfil: Administrador")
else:
    st.sidebar.text("Perfil: Operador")

if st.sidebar.button("Sair"):
    logout()

st.sidebar.divider()

# Menu Principal
opcoes_menu = ["Central do Núcleo"]
if st.session_state.get('is_admin'):
    opcoes_menu.append("Configurar Modalidades (Admin)")

menu = st.sidebar.radio("Navegação", opcoes_menu)

# --- TELA 1: CENTRAL DO NÚCLEO (Gestão de Processos) ---
if menu == "Central do Núcleo":
    st.title(f"🏢 Central do {meu_setor_nome}")
    
    # 1. Recupera SÓ os processos deste núcleo
    meu_setor_id = st.session_state.get("setor_id")
    
    # Query filtrada pelo setor_id da sessão
    query = session.query(
        Processo.id, Processo.numero_sei, Processo.objeto, 
        Processo.valor_previsto, Processo.fase_atual, Processo.data_autorizacao,
        Modalidade.nome.label("modalidade")
    ).outerjoin(Modalidade, Processo.modalidade_id == Modalidade.id)\
     .filter(Processo.setor_origem_id == meu_setor_id) # <--- FILTRO PRINCIPAL
    
    df = pd.read_sql(query.statement, session.bind)
    
    # Abas para separar Visão Geral (Dashboard) da Operação
    tab_dashboard, tab_operacional = st.tabs(["📊 Visão Geral", "⚙️ Operacional (Processos)"])

    # --- ABA 1: DASHBOARD ---
    with tab_dashboard:
        if not df.empty:
            m1, m2, m3 = st.columns(3)
            m1.metric("Total de Processos", len(df))
            m2.metric("Valor Acumulado", f"R$ {df['valor_previsto'].sum():,.2f}")
            m3.metric("Fase Mais Comum", df['fase_atual'].mode() if not df.empty else "-")
            
            st.divider()
            st.subheader("Processos por Fase")
            contagem_fases = df['fase_atual'].value_counts()
            st.bar_chart(contagem_fases, color="#4A90E2")
        else:
            st.info("Ainda não há indicadores para exibir. Cadastre processos na aba Operacional.")

    # --- ABA 2: OPERACIONAL (A Central do Gerente) ---
    with tab_operacional:
        # Barra de Ferramentas
        col_btn, col_busca = st.columns([0.25, 0.75])
        
        with col_btn:
            # Botão grande para cadastrar
            if st.button("➕ Novo Processo", type="primary", use_container_width=True):
                modal_novo_processo()
        
        with col_busca:
            termo_busca = st.text_input("🔍 Buscar Processo (SEI ou Objeto)", label_visibility="collapsed", placeholder="Digite para filtrar...")

        if not df.empty:
            # Aplica filtro de busca Python
            if termo_busca:
                mask = df['numero_sei'].str.contains(termo_busca, case=False, na=False) | \
                       df['objeto'].str.contains(termo_busca, case=False, na=False)
                df_exibicao = df[mask]
            else:
                df_exibicao = df

            # Área de Ação (Editar/Movimentar)
            with st.container(border=True):
                st.markdown("#### ✏️ Gerenciar Processo Existente")
                c_sel, c_do = st.columns([0.8, 0.2])
                with c_sel:
                    proc_id = st.selectbox(
                        "Selecione o processo para editar ou mudar de fase:", 
                        df_exibicao['id'].tolist(),
                        format_func=lambda x: f"{df_exibicao[df_exibicao['id']==x]['numero_sei'].values} - {df_exibicao[df_exibicao['id']==x]['objeto'].values[:50]}..."
                    )
                with c_do:
                    st.write("")
                    st.write("") 
                    if st.button("Abrir Gestão", use_container_width=True):
                        modal_movimentar_processo(proc_id)

            # Tabela de Visualização
            st.dataframe(
                df_exibicao,
                column_config={
                    "numero_sei": "SEI",
                    "objeto": "Objeto do Processo",
                    "modalidade": "Modalidade",
                    "fase_atual": st.column_config.TextColumn("Fase Atual", help="Status atual"),
                    "valor_previsto": st.column_config.NumberColumn("Valor", format="R$ %.2f"),
                    "data_autorizacao": st.column_config.DatetimeColumn("Criado em", format="DD/MM/YYYY"),
                },
                hide_index=True,
                use_container_width=True,
                height=400
            )
        else:
            st.warning("Seu núcleo ainda não possui processos cadastrados.")

# --- TELA 2: CONFIGURAÇÃO (Apenas Admin) ---
elif menu == "Configurar Modalidades (Admin)":
    if not st.session_state.get('is_admin'):
        st.error("Acesso restrito.")
        st.stop()
    
    st.title("⚙️ Configurar Modalidades")
    
    # Aba simples de configuração
    with st.form("form_add_mod"):
        nome_mod = st.text_input("Nome da Nova Modalidade")
        fases_txt = st.text_area("Fases (uma por linha)", height=200, placeholder="Ex:\nRecepção\nAnálise\nPublicação")
        
        if st.form_submit_button("Criar Modalidade"):
            fases_lista = [f.strip() for f in fases_txt.split('\n') if f.strip()]
            if nome_mod and fases_lista:
                try:
                    nm = Modalidade(nome=nome_mod)
                    session.add(nm)
                    session.flush()
                    for i, f_nome in enumerate(fases_lista):
                        session.add(FaseTemplate(nome=f_nome, ordem=i+1, modalidade_id=nm.id))
                    session.commit()
                    st.success(f"Modalidade '{nome_mod}' criada!")
                except Exception as e:
                    session.rollback()
                    st.error(f"Erro: {e}")
    
    # Lista modalidades existentes
    st.divider()
    st.subheader("Modalidades Ativas")
    mods = session.query(Modalidade).all()
    for m in mods:
        with st.expander(m.nome):
            fs = session.query(FaseTemplate).filter_by(modalidade_id=m.id).order_by(FaseTemplate.ordem).all()
            for f in fs:
                st.text(f"{f.ordem} - {f.nome}")
