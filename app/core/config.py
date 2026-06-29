from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"
    log_level: str = "INFO"
    database_url: str = "sqlite+aiosqlite:///./data/travel_planner.db"
    cors_origins: str = "http://localhost:8081,http://127.0.0.1:8081"
    uploads_dir: str = "./data/uploads"
    ollama_base_url: str = "http://localhost:11434"
    ollama_chat_model: str = "llama3.2"
    ollama_embedding_model: str = "nomic-embed-text"
    use_mock_llm: bool = True
    max_upload_bytes: int = 10 * 1024 * 1024

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    @property
    def is_postgres(self) -> bool:
        return "postgresql" in self.database_url


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
