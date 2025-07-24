# app/core/config.py

from pydantic_settings import BaseSettings  # ← nuevo import en Pydantic v2

class Settings(BaseSettings):
    ENV: str = "development"
    DEBUG: bool = True

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
