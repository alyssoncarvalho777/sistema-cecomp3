import asyncio
import streamlit as st
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

# 1. Tenta pegar a URL dos segredos (Source [2])
try:
    DATABASE_URL = st.secrets["database"]["url"]
    print("✅ Segredo encontrado: URL carregada.")
except Exception as e:
    print(f"❌ Erro: Não foi possível ler .streamlit/secrets.toml. Detalhes: {e}")
    exit()

async def verificar():
    print("🔄 Tentando conectar ao PostgreSQL...")
    
    # 2. Configura o motor assíncrono (Source [3])
    try:
        engine = create_async_engine(DATABASE_URL, echo=False)
        
        async with engine.connect() as conn:
            # Executa um comando simples de teste
            result = await conn.execute(text("SELECT version();"))
            versao = result.scalar()
            print(f"🎉 SUCESSO! Conectado ao: {versao}")
            
        await engine.dispose()
        return True
    except Exception as e:
        print(f"❌ FALHA NA CONEXÃO. Verifique sua URL e senha.\nErro técnico: {e}")
        return False

if __name__ == "__main__":
    # Executa o loop assíncrono (Source [4])
    asyncio.run(verificar())
