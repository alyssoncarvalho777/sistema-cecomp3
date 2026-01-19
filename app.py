import streamlit as st
import pandas as pd
from sqlalchemy import text
from auth import verificar_login, logout
from database import get_session, get_connection
from models import Base, Setor, Modalidade, FaseTemplate, Processo, Usuario

# 1. Configuração da Página (Deve ser a primeira linha)
st.set_page_config(page_title="CECOMP - SESAU/RO", layout="wide")

# 2. Inicialização do Banco de Dados
conn = get_connection()
Base.metadata.create_all(conn.engine)

# 3. Verificação de Segurança
# Se verificar_login() retornar False, o script para aqui e mostra a tela de login.
if not verificar_login():
    st.stop()

# --- DAQUI PARA BAIXO, O CÓDIGO SÓ RODA SE O USUÁRIO ESTIVER LOGADO ---

# 4. Barra Lateral (Menu)
st.sidebar.title(f"👤 {st.session_state.get('usuario_nome', 'Usuário')}")

# Menu Dropdown com as opções solicitadas
menu = st.sidebar.selectbox(
    "Navegação", 
    [
        "Dashboard", 
        "Novo Processo (Preços)", # Equivalente ao cadastro de preços/processo
        "Configurar Modalidades e Fases" # Agrupa Modalidades e Fases
    ]
)

if st.sidebar.button("Sair"):
    logout()

# 5. Lógica das Telas
session = get_session()

# --- TELA: DASHBOARD ---
if menu == "Dashboard":
    st.title("📋 Visão Geral")
    
    # Busca dados usando pandas e a conexão
    df_proc = pd.read_sql(session.query(Processo).statement, session.bind)
    
    if not df_proc.empty:
        col1, col2 = st.columns(2)
        col1.metric("Total de Processos", len(df_proc))
        valor_total = df_proc['valor_previsto'].sum()
        col2.metric("Volume Financeiro", f"R$ {valor_total:,.2f}")
        
        st.subheader("Processos Recentes")
        st.dataframe(df_proc, use_container_width=True)
    else:
        st.info("Nenhum processo encontrado.")

# --- TELA: NOVO PROCESSO (Preços) ---
elif menu == "Novo Processo (Preços)":
    st.title("📝 Cadastro de Processo e Preços")
    
    # Carrega modalidades para o selectbox
    mods = session.query(Modalidade).all()
    
    if not mods:
        st.warning("⚠️ Nenhuma modalidade cadastrada. Vá para 'Configurar Modalidades' primeiro.")
    else:
        with st.form("form_processo"):
            c1, c2 = st.columns(2)
            with c1:
                sei = st.text_input("Número SEI")
                # Aqui entra o "Cadastro de Preço" (Valor Previsto)
                valor = st.number_input("Valor de Referência (Preço)", min_value=0.0, format="%.2f")
            with c2:
                # Selectbox que mostra o nome mas salva o ID
                mod_selecionada = st.selectbox(
                    "Modalidade", 
                    mods, 
                    format_func=lambda m: m.nome
                )
                objeto = st.text_area("Objeto")

            submitted = st.form_submit_button("Salvar Processo")
            
            if submitted:
                # Validação simples
                if not sei or not objeto:
                    st.error("Preencha SEI e Objeto.")
                else:
                    # Tenta buscar a primeira fase dessa modalidade
                    fase_inicial = session.query(FaseTemplate)\
                        .filter_by(modalidade_id=mod_selecionada.id)\
                        .order_by(FaseTemplate.ordem)\
                        .first()
                    
                    nome_fase = fase_inicial.nome if fase_inicial else "Inicial"
                    
                    novo_processo = Processo(
                        numero_sei=sei,
                        valor_previsto=valor,
                        objeto=objeto,
                        modalidade_id=mod_selecionada.id,
                        fase_atual=nome_fase
                    )
                    session.add(novo_processo)
                    session.commit()
                    st.success(f"Processo {sei} cadastrado com sucesso!")

# --- TELA: CONFIGURAR MODALIDADES E FASES (COM FASES PERSONALIZADAS) ---
elif menu == "Configurar Modalidades e Fases":
    st.title("⚙️ Gestão de Modalidades")
    
    st.info("Cadastre a modalidade e defina a ordem das fases (padrão + personalizadas).")
    
    with st.form("form_config_modalidade"):
        nome_mod = st.text_input("Nome da Nova Modalidade (ex: Credenciamento)")
        
        st.write("---")
        st.write("### Definição de Fases")
        
        # 1. Lista de fases padrão para seleção rápida [1]
        fases_padrao = [
            "Planejamento", "Pesquisa de Preço", "Parecer Jurídico", 
            "Edital", "Disputa", "Adjudicação", "Homologação", "Empenho",
            "Liquidação", "Pagamento"
        ]
        
        # O usuário seleciona as fases comuns
        selecao_padrao = st.multiselect(
            "1. Selecione fases padrão (na ordem desejada):", 
            fases_padrao
        )
        
        # 2. Área de texto para fases manuais [2]
        st.write("2. Adicione fases personalizadas (se houver):")
        st.caption("Digite uma fase por linha. Elas serão adicionadas APÓS as fases padrão selecionadas acima.")
        texto_fases_extras = st.text_area("Fases Manuais", height=100, placeholder="Exemplo:\nRecurso Administrativo\nAnálise Técnica")
        
        # Botão de Submissão [3]
        submit_mod = st.form_submit_button("Criar Modalidade e Fases")
        
        if submit_mod:
            # Processamento: Limpa espaços e quebra o texto por linha
            fases_extras = [f.strip() for f in texto_fases_extras.split('\n') if f.strip()]
            
            # Une as duas listas: Fases Padrão + Fases Extras
            todas_fases = selecao_padrao + fases_extras
            
            # Validações Lógicas
            if not nome_mod:
                st.error("O nome da modalidade é obrigatório.")
            elif not todas_fases:
                st.error("Você precisa definir pelo menos uma fase (selecionada ou manual).")
            else:
                try:
                    # Inserção no Banco de Dados (SQLAlchemy)
                    nova_m = Modalidade(nome=nome_mod)
                    session.add(nova_m)
                    session.flush() # Gera o ID da modalidade antes do commit [4]
                    
                    # Itera sobre a lista combinada para criar as fases na ordem
                    for i, nome_fase in enumerate(todas_fases):
                        nova_f = FaseTemplate(
                            nome=nome_fase, 
                            ordem=i + 1,  # Começa da ordem 1
                            modalidade_id=nova_m.id
                        )
                        session.add(nova_f)
                    
                    session.commit()
                    st.success(f"Modalidade '{nome_mod}' criada com sucesso!")
                    
                    # Exibe resumo do que foi criado
                    st.write(f"**Fases cadastradas:** {', '.join(todas_fases)}")
                    
                except Exception as e:
                    session.rollback()
                    st.error(f"Erro ao salvar: {e}")

    # Visualização das Modalidades Existentes
    st.divider()
    st.subheader("Modalidades Cadastradas")
    
    # Consulta atualizada para mostrar as modalidades criadas
    modalidades_db = session.query(Modalidade).all()
    
    if not modalidades_db:
        st.info("Nenhuma modalidade cadastrada ainda.")
    else:
        for m in modalidades_db:
            with st.expander(f"📂 {m.nome}"):
                # Busca fases ordenadas
                fases = session.query(FaseTemplate)\
                    .filter_by(modalidade_id=m.id)\
                    .order_by(FaseTemplate.ordem)\
                    .all()
                
                if fases:
                    # Exibe fluxo visual
                    st.write("fluxo: " + " ➡️ ".join([f.nome for f in fases]))
                else:
                    st.warning("Sem fases cadastradas.")
