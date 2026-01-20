import os
import tomllib  # Para Python 3.11+ (Se der erro, use 'import toml' e instale pip install toml)
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base

# 1. Função para ler o secrets.toml manualmente (já que o FastAPI não é o Streamlit)
def get_database_url():
    try:
        with open(".streamlit/secrets.toml", "rb") as f:
            secrets = tomllib.load(f)
            return secrets["database"]["url"]
    except FileNotFoundError:
        # Fallback para variável de ambiente (boa prática para produção)
        return os.getenv("DATABASE_URL", "sqlite:///./test.db")

DATABASE_URL = get_database_url()

# 2. Criação do Motor Assíncrono
engine = create_async_engine(DATABASE_URL, echo=True)

# 3. Fábrica de Sessões
AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

Base = declarative_base()

# 4. Dependência para injetar o banco nas rotas
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
