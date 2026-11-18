import os
from pathlib import Path
from dotenv import load_dotenv

# Explicitly load .env from the backend directory
env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

class Settings:
    PROJECT_NAME: str = "MARKET PILOT AI"
    DATABASE_URL: str = os.getenv("DATABASE_URL", "mysql+pymysql://root:root@localhost:3306/marketing_agent")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "market-pilot-ai-secret-key-super-secure-production-ready")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", str(60 * 24))) # 24 hours
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:5173,http://127.0.0.1:5173")
    
    # LLM Settings
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "groq/llama-3.3-70b-versatile")
    OPENROUTER_MODEL: str = os.getenv("OPENROUTER_MODEL", "openrouter/meta-llama/llama-3.1-8b-instruct")

settings = Settings()