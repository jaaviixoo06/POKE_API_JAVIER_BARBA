# app/config.py

from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    secret_key: str = "CHANGE_ME"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24
    refresh_token_expire_minutes: int = 60 * 24

    class Config:
        env_file = ".env"

settings = Settings()