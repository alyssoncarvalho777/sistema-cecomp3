from sqlalchemy import Column, Integer, String, ForeignKey, Text, Float, DateTime, Boolean
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime

Base = declarative_base()

class Setor(Base):
    __tablename__ = 'setores'
    id = Column(Integer, primary_key=True)
    nome = Column(String(100), nullable=False)
    # Relacionamentos
    usuarios = relationship("Usuario", back_populates="setor")
    processos = relationship("Processo", back_populates="setor_origem")

class Usuario(Base):
    __tablename__ = 'usuarios'
    id = Column(Integer, primary_key=True)
    nome = Column(String(100), nullable=False)
    login = Column(String(50), unique=True, nullable=False)
    senha = Column(String(50), nullable=False)
    is_admin = Column(Boolean, default=False)
    
    # Vínculo Obrigatório com Setor
    setor_id = Column(Integer, ForeignKey('setores.id'))
    setor = relationship("Setor", back_populates="usuarios")

class Modalidade(Base):
    __tablename__ = 'modalidades'
    id = Column(Integer, primary_key=True)
    nome = Column(String(100), nullable=False)
    fases = relationship("FaseTemplate", back_populates="modalidade", cascade="all, delete-orphan")

class FaseTemplate(Base):
    __tablename__ = 'fases_template'
    id = Column(Integer, primary_key=True)
    nome = Column(String(100))
    ordem = Column(Integer)
    modalidade_id = Column(Integer, ForeignKey('modalidades.id'))
    modalidade = relationship("Modalidade", back_populates="fases")

class Processo(Base):
    __tablename__ = 'processos'
    id = Column(Integer, primary_key=True)
    numero_sei = Column(String(50), unique=True)
    objeto = Column(Text)
    data_autorizacao = Column(DateTime, default=datetime.now)
    valor_previsto = Column(Float, default=0.0)
    
    modalidade_id = Column(Integer, ForeignKey('modalidades.id'))
    fase_atual = Column(String(100))
    setor_origem_id = Column(Integer, ForeignKey('setores.id'))
    setor_origem = relationship("Setor", back_populates="processos")
