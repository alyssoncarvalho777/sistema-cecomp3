from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

# Importações internas do nosso projeto
# O 'backend.' é necessário porque estamos rodando da raiz
from backend.database import engine, Base, get_db
from backend import models, schemas

app = FastAPI(
    title="Sistema CECOMP API",
    description="API assíncrona para gestão de processos de compras",
    version="1.0.0"
)

# --- EVENTOS DE CICLO DE VIDA ---

@app.on_event("startup")
async def startup():
    """
    Ao iniciar a API, conecta ao banco e cria as tabelas se não existirem.
    Em produção, o ideal é usar Alembic para migrações.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Banco de dados conectado e tabelas verificadas.")

# --- ROTAS DE PROCESSOS ---

@app.post("/processos/", response_model=schemas.ProcessoResponse, status_code=status.HTTP_201_CREATED)
async def criar_processo(processo: schemas.ProcessoCreate, db: AsyncSession = Depends(get_db)):
    """Cadastra um novo processo no banco de dados."""
    
    # 1. Verifica duplicidade do SEI
    stmt = select(models.Processo).filter_by(numero_sei=processo.numero_sei)
    result = await db.execute(stmt)
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="Número SEI já cadastrado.")

    # 2. Cria o objeto do modelo
    # 'Início' é a fase padrão hardcoded por enquanto
    novo_processo = models.Processo(
        **processo.dict(),
        fase_atual="Início" 
    )
    
    # 3. Salva no banco
    db.add(novo_processo)
    try:
        await db.commit()
        await db.refresh(novo_processo) # Recarrega para pegar o ID gerado e a Data
        return novo_processo
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao salvar: {str(e)}")

@app.get("/processos/", response_model=List[schemas.ProcessoResponse])
async def listar_processos(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    """Lista todos os processos com paginação simples."""
    stmt = select(models.Processo).offset(skip).limit(limit)
    result = await db.execute(stmt)
    # .scalars().all() converte o resultado bruto do SQL em objetos Python
    return result.scalars().all()

# --- ROTAS DE MODALIDADES ---

@app.post("/modalidades/", response_model=schemas.ModalidadeResponse)
async def criar_modalidade(modalidade: schemas.ModalidadeCreate, db: AsyncSession = Depends(get_db)):
    nova_mod = models.Modalidade(**modalidade.dict())
    db.add(nova_mod)
    await db.commit()
    await db.refresh(nova_mod)
    return nova_mod

@app.get("/modalidades/", response_model=List[schemas.ModalidadeResponse])
async def listar_modalidades(db: AsyncSession = Depends(get_db)):
    stmt = select(models.Modalidade)
    result = await db.execute(stmt)
    return result.scalars().all()

# --- ROTA DE SAÚDE (HEALTH CHECK) ---
@app.get("/")
async def root():
    return {"status": "online", "message": "API CECOMP operando com SQLAlchemy Async"}
