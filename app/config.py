from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./docvault.db"
    DES3_MASTER_KEY: str
    STORAGE_PATH: str = "./storage"
    JWT_SECRET: str = "default-secret"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
