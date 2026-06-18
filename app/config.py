import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    LLM_PROVIDER: str = Field(default="ollama", description="ollama, huggingface, or mock")
    OLLAMA_MODEL: str = Field(default="llama3.1:8b")
    EMBEDDING_MODEL: str = Field(default="all-MiniLM-L6-v2")
    TOP_K: int = Field(default=4)
    DATABASE_URL: str = Field(default="sqlite:///rag_logs.db")
    HF_API_TOKEN: str = Field(default="")
    HF_MODEL: str = Field(default="google/gemma-2-9b-it")
    PDF_PATH: str = Field(default="data/pdfs/aws_customer_agreement.pdf")
    VECTOR_DB_DIR: str = Field(default="data/faiss_index")
    
    # Load from .env file
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
