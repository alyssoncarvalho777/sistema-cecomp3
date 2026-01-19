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
        # Formulário para garantir submissão única 
        with st.form("form_processo"):
            c1, c2 = st.columns(2)
            with c1:
                sei = st.text_input("Número SEI (Único)") 
                valor = st.number_input("Valor de Referência (R$)", min_value=0.0, format="%.2f") 
            with c2:
                # Selectbox exibindo nomes, mas trabalhando com objetos [6]
                mod_selecionada = st.selectbox(
                    "Modalidade", 
                    mods, 
                    format_func=lambda x: x.nome
                )
                objeto = st.text_area("Objeto da Compra") 
                
            submitted = st.form_submit_button("Cadastrar Processo") 
            
            if submitted:
                # Validações de Regra de Negócio
                if not sei or not objeto:
                    st.error("Preencha os campos obrigatórios (SEI e Objeto).") 
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
                    st.success(f"Processo {sei} cadastrado com sucesso!") 

# --- MÓDULO 3: CONFIGURAR MODALIDADES (ADMIN) ---
elif menu == "Configurar Modalidades (Admin)":
    
    # 🔒 BLOQUEIO DE SEGURANÇA
    if not st.session_state.get("is_admin", False):
        st.error("⛔ ACESSO NEGADO")
        st.info("Você não tem permissão para acessar esta área.")
        st.stop() 

    st.title("⚙️ Gestão de Modalidades e Fluxos")
    st.markdown("""
    **Instruções:**
    1. Defina o nome da modalidade.
    2. A lista de fases abaixo já vem preenchida com o padrão sugerido.
    3. **Para inserir fases intermediárias:** Basta clicar no texto, criar uma nova linha e digitar.
    4. **Para remover:** Apague a linha desejada.
    5. A ordem das linhas será a ordem oficial do processo.
    """)
    
    with st.form("admin_modalidades"):
        nome_mod = st.text_input("Nome da Modalidade (ex: Pregão Eletrônico)")
        
        st.write("---")
        st.subheader("Definição do Fluxo de Fases")
        
        # LISTA PADRÃO SOLICITADA (20 Itens)
        fases_sugeridas = [
            "Recepção na CECOMP",
            "Primeira Análise do Núcleo",
            "Pesquisa de Preços / ETP / Risco",
            "Elaboração de TR",
            "Primeira Análise da SUPEL",
            "Correção/Ajuste do TR",
            "Elaboração de Edital",
            "Análise Jurídica",
            "Correção/Ajuste do Edital",
            "Publicação do Pregão",
            "Recepção de Propostas",
            "Análise Técnica",
            "Recurso/Reanálise (Técnico)",
            "Habilitação",
            "Recurso/Reanálise (Habilitação)",
            "Análise para Homologação",
            "Homologação",
            "Elaboração da Ata",
            "Comunicação Publicação da Ata",
            "Finalizado"
        ]
        
        # Convertemos a lista para uma única string separada por quebras de linha
        texto_padrao = "\n".join(fases_sugeridas)
        
        # O text_area permite edição livre (inserir no meio, apagar, renomear)
        fases_editaveis = st.text_area(
            "Edite as fases aqui (uma por linha):", 
            value=texto_padrao, 
            height=500  # Altura aumentada para caber todas as fases confortavelmente
        )
        
        if st.form_submit_button("Salvar Estrutura"):
            # Processamento:
            # 1. Separa o texto por linhas
            # 2. Remove espaços extras (.strip())
            # 3. Ignora linhas vazias (if f.strip())
            lista_final_fases = [f.strip() for f in fases_editaveis.split('\n') if f.strip()]
            
            if not nome_mod:
                st.warning("O nome da modalidade é obrigatório.")
            elif not lista_final_fases:
                st.warning("A lista de fases não pode estar vazia.")
            else:
                try:
                    # Transação no Banco de Dados
                    nova_m = Modalidade(nome=nome_mod)
                    session.add(nova_m)
                    session.flush() # Gera o ID da modalidade
                    
                    # Salva cada fase com sua ordem baseada na linha em que estava
                    for i, nome_f in enumerate(lista_final_fases):
                        session.add(FaseTemplate(
                            nome=nome_f,
                            ordem=i+1, # A ordem é o índice + 1
                            modalidade_id=nova_m.id
                        ))
                    
                    session.commit()
                    st.success(f"Modalidade '{nome_mod}' criada com {len(lista_final_fases)} fases!")
                    st.toast("Fluxo salvo com sucesso!", icon="✅")
                    
                except Exception as e:
                    session.rollback()
                    st.error(f"Erro ao salvar: {e}")

    # Visualização das Modalidades Existentes
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
                
                # Mostra lista numerada para facilitar conferência da ordem
                for f in fases:
                    st.text(f"{f.ordem}. {f.nome}")
    else:
        st.caption("Nenhuma modalidade cadastrada.")
