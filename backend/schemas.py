from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional, List

# --- SCHEMAS DE MODALIDADE ---
# Necessário para listar no dropdown do frontend

class ModalidadeBase(BaseModel):
    nome: str

class ModalidadeCreate(ModalidadeBase):
    pass

class ModalidadeResponse(ModalidadeBase):
    id: int
    
    # Configuração para Pydantic v2 ler objetos do SQLAlchemy
    model_config = ConfigDict(from_attributes=True)


# --- SCHEMAS DE PROCESSO ---

class ProcessoBase(BaseModel):
    numero_sei: str
    objeto: str
    valor_previsto: float
    modalidade_id: int
    setor_origem_id: Optional[int] = 1  # Valor padrão caso não seja enviado

# O que precisamos receber para CRIAR (Input)
class ProcessoCreate(ProcessoBase):
    pass

# O que a API DEVOLVE para quem chamou (Output)
class ProcessoResponse(ProcessoBase):
    id: int
    fase_atual: str
    data_autorizacao: datetime
    
    # Permite que o Pydantic converta o objeto do banco (SQLAlchemy) para JSON
    model_config = ConfigDict(from_attributes=True)
