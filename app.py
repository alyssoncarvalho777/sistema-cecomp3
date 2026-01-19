import streamlit as st
import pandas as pd
from sqlalchemy import text
from sqlalchemy.exc import OperationalError # Importação necessária para tratar o erro
from auth import verificar_login, logout
from database import get_connection, get_session
from models import Base, Setor, Modalidade, FaseTemplate, Processo, Usuario

# 1. Configuração da Página
st.set_page_config(page_title="CECOMP - SESAU/RO", layout="wide")

# 2. Inicialização e Correção Automática do Banco
conn = get_connection()
session = get_session()

try:
    # Tenta verificar se a tabela existe e está atualizada
    # Se a coluna 'is_admin' faltar, isso vai gerar o OperationalError
    session.query(Usuario).first()
except OperationalError:
    # SE O ERRO ACONTECER:
    st.warning("⚠️ Detectada alteração de estrutura no banco de dados. Atualizando sistema...")
    
    # Força a exclusão das tabelas antigas e cria as novas com a coluna is_admin
    Base.metadata.drop_all(conn.engine)
    Base.metadata.create_all(conn.engine)
    
    st.success("✅ Sistema atualizado! Por favor, recarregue a página (F5).")
    st.stop() # Para a execução para o usuário recarregar
except Exception:
    # Caso as tabelas não existam ainda (primeira execução absoluta)
    Base.metadata.create_all(conn.engine)

# Garante que as tabelas existem se não caiu no erro acima
Base.metadata.create_all(conn.engine)

# 3. Verificação de Segurança
if not verificar_login():
    st.stop()

# 3. Verificação de Segurança e Login [4]
# Se não logado, o script para aqui. Se logado, continua.
if not verificar_login():
    st.stop()

# --- INÍCIO DA ÁREA RESTRITA (LOGADA) ---
session = get_session()

# Barra Lateral: Informações do Usuário [5]
st.sidebar.title(f"👤 {st.session_state.get('usuario_nome', 'Usuário')}")

# Indicador visual de privilégio
if st.session_state.get('is_admin'):
    st.sidebar.markdown("**:crown: Perfil: Administrador**")
else:
    st.sidebar.markdown("**:paperclip: Perfil: Operador**")

if st.sidebar.button("Sair"):
    logout() # [4]

st.sidebar.divider()

# Menu de Navegação [6]
menu = st.sidebar.selectbox(
    "Navegação", 
    ["Dashboard", "Novo Processo", "Configurar Modalidades (Admin)"]
)

# --- MÓDULO 1: DASHBOARD ---
if menu == "Dashboard":
    st.title("📋 Visão Geral")
    
    # Consulta otimizada lendo direto para Pandas [7]
    df = pd.read_sql(session.query(Processo).statement, session.bind)
    
    if not df.empty:
        # Métricas no topo [8]
        col1, col2 = st.columns(2)
        col1.metric("Total de Processos", len(df))
        col2.metric("Valor Total (R$)", f"{df['valor_previsto'].sum():,.2f}")
        
        st.divider()
        
        # Gráficos e Tabelas [7, 9]
        st.subheader("Processos por Fase Atual")
        st.bar_chart(df['fase_atual'].value_counts())
        
        st.subheader("Detalhamento")
        st.dataframe(
            df[['numero_sei', 'objeto', 'valor_previsto', 'fase_atual', 'data_autorizacao']], 
            use_container_width=True
        )
    else:
        st.info("Nenhum processo cadastrado no sistema ainda.")

# --- MÓDULO 2: NOVO PROCESSO ---
elif menu == "Novo Processo":
    st.title("📝 Cadastro de Processo")
    
    mods = session.query(Modalidade).all()
    
    if not mods:
        st.warning("⚠️ O sistema está vazio. Solicite ao Administrador para cadastrar Modalidades.")
    else:
        # Formulário para garantir submissão única [10]
        with st.form("form_processo"):
            c1, c2 = st.columns(2) [11]
            with c1:
                sei = st.text_input("Número SEI (Único)") [12]
                valor = st.number_input("Valor de Referência (R$)", min_value=0.0, format="%.2f") [13]
            with c2:
                # Selectbox exibindo nomes, mas trabalhando com objetos [6]
                mod_selecionada = st.selectbox(
                    "Modalidade", 
                    mods, 
                    format_func=lambda x: x.nome
                )
                objeto = st.text_area("Objeto da Compra") [12]
                
            submitted = st.form_submit_button("Cadastrar Processo") [14]
            
            if submitted:
                # Validações de Regra de Negócio
                if not sei or not objeto:
                    st.error("Preencha os campos obrigatórios (SEI e Objeto).") [15]
                elif session.query(Processo).filter_by(numero_sei=sei).first():
                    st.error("Erro: Este número SEI já está cadastrado.")
                else:
                    # Lógica para definir fase inicial automaticamente
                    fase_inicial = session.query(FaseTemplate)\
                        .filter_by(modalidade_id=mod_selecionada.id)\
                        .order_by(FaseTemplate.ordem)\
                        .first()
                    
                    novo_processo = Processo(
                        numero_sei=sei,
                        valor_previsto=valor,
                        objeto=objeto,
                        modalidade_id=mod_selecionada.id,
                        fase_atual=fase_inicial.nome if fase_inicial else "Início"
                    )
                    session.add(novo_processo)
                    session.commit()
                    st.success(f"Processo {sei} cadastrado com sucesso!") [15]

# --- MÓDULO 3: CONFIGURAR MODALIDADES (ADMIN) ---
elif menu == "Configurar Modalidades (Admin)":
    
    # 🔒 BLOQUEIO DE SEGURANÇA [16]
    # Se a variável de sessão 'is_admin' não for True, impede o acesso.
    if not st.session_state.get("is_admin", False):
        st.error("⛔ ACESSO NEGADO")
        st.info("Você não tem permissão para acessar esta área.")
        st.stop() # Interrompe a renderização do restante da página [17]

    st.title("⚙️ Gestão de Modalidades")
    st.markdown("Crie modalidades e defina seu fluxo de fases (Padrão + Personalizadas).")
    
    with st.form("admin_modalidades"):
        nome_mod = st.text_input("Nome da Modalidade (ex: Pregão Eletrônico)")
        
        st.divider()
        st.caption("Montagem do Fluxo de Fases")
        
        # 1. Fases Padrão (Multiselect) [18]
        lista_padrao = [
            "Planejamento", "Pesquisa de Preço", "Parecer Jurídico", "Edital", 
            "Sessão Pública", "Adjudicação", "Homologação", "Empenho", 
            "Liquidação", "Pagamento"
        ]
        selecao_padrao = st.multiselect("Selecione fases padrão (na ordem):", lista_padrao)
        
        # 2. Fases Manuais (Text Area) [12]
        st.caption("Se precisar de fases extras, digite abaixo (uma por linha). Elas entrarão APÓS as selecionadas acima.")
        extras_txt = st.text_area("Fases Personalizadas", height=100)
        
        if st.form_submit_button("Salvar Estrutura"):
            # Processa o texto manual: remove vazios e espaços
            fases_extras = [f.strip() for f in extras_txt.split('\n') if f.strip()]
            
            # Combina as listas
            todas_fases = selecao_padrao + fases_extras
            
            if not nome_mod:
                st.warning("O nome da modalidade é obrigatório.")
            elif not todas_fases:
                st.warning("Defina pelo menos uma fase.")
            else:
                try:
                    # Transação Atômica no Banco
                    nova_m = Modalidade(nome=nome_mod)
                    session.add(nova_m)
                    session.flush() # Garante o ID da modalidade
                    
                    for i, nome_f in enumerate(todas_fases):
                        session.add(FaseTemplate(
                            nome=nome_f,
                            ordem=i+1,
                            modalidade_id=nova_m.id
                        ))
                    
                    session.commit()
                    st.success(f"Modalidade '{nome_mod}' criada com {len(todas_fases)} fases!")
                except Exception as e:
                    session.rollback()
                    st.error(f"Erro ao salvar: {e}")

    # Visualização do que já existe (Expander) [19]
    st.divider()
    st.subheader("Modalidades Ativas")
    mods_db = session.query(Modalidade).all()
    
    if mods_db:
        for m in mods_db:
            with st.expander(f"📂 {m.nome}"):
                fases = session.query(FaseTemplate)\
                    .filter_by(modalidade_id=m.id)\
                    .order_by(FaseTemplate.ordem)\
                    .all()
                st.write("Fluxo: " + " ➡️ ".join([f.nome for f in fases]))
    else:
        st.caption("Nenhuma modalidade cadastrada.")
