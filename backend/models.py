from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from backend.database import Base

class Modalidade(Base):
    __tablename__ = "modalidades"
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False)
    
    # Relacionamento inverso (opcional para agora)
    processos = relationship("Processo", back_populates="modalidade")

class Processo(Base):
    __tablename__ = "processos"

    id = Column(Integer, primary_key=True, index=True)
    numero_sei = Column(String, unique=True, index=True)
    objeto = Column(Text)
    valor_previsto = Column(Float, default=0.0)
    data_autorizacao = Column(DateTime, default=datetime.now)
    fase_atual = Column(String, default="Início")
    
    modalidade_id = Column(Integer, ForeignKey("modalidades.id"))
    modalidade = relationship("Modalidade", back_populates="processos")
    
    # Para simplificar este passo, vamos omitir Setor e Usuario por um instante
    # focando em fazer o cadastro de processo funcionar primeiro.
    setor_origem_id = Column(Integer, nullable=True) 
Arquivo 3: backend/schemas.py
O FastAPI usa esses "Esquemas" para validar se os dados que o usuário enviou estão corretos antes de passar para o banco.
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

# O que precisamos receber para criar um Processo
class ProcessoCreate(BaseModel):
    numero_sei: str
    objeto: str
    valor_previsto: float
    modalidade_id: int
    setor_origem_id: Optional[int] = 1

# O que a API devolve para o usuário (inclui ID e Data)
class ProcessoResponse(ProcessoCreate):
    id: int
    fase_atual: str
    data_autorizacao: datetime

    class Config:
        from_attributes = True # Permite ler dados do SQLAlchemy
Arquivo 4: backend/main.py
Este é o arquivo que liga tudo. Ele cria as rotas (URLs) da API.
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List

# Importando nossos módulos
from backend.database import engine, Base, get_db
from backend import models, schemas

app = FastAPI(title="Sistema CECOMP API")

# Evento de inicialização: Cria as tabelas no banco automaticamente
@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        # Cria todas as tabelas definidas em models.py
        await conn.run_sync(Base.metadata.create_all)

# Rota 1: Criar Processo (POST)
@app.post("/processos/", response_model=schemas.ProcessoResponse)
async def criar_processo(processo: schemas.ProcessoCreate, db: AsyncSession = Depends(get_db)):
    # Transforma o Schema (Pydantic) em Model (SQLAlchemy)
    novo_db = models.Processo(**processo.dict()) 
    db.add(novo_db)
    try:
        await db.commit()
        await db.refresh(novo_db)
        return novo_db
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=f"Erro ao salvar: {e}")

# Rota 2: Listar Processos (GET)
@app.get("/processos/", response_model=List[schemas.ProcessoResponse])
async def listar_processos(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.Processo))
    return result.scalars().all()

# Rota de teste simples
@app.get("/")
async def root():
    return {"mensagem": "API CECOMP Online 🚀"}
