from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "ML Service"
    app_debug: bool = False

    fallback_enabled: bool = True

    host: str = "0.0.0.0"
    port: int = 8100

    ollama_url: str = "http://ollama:11434"
    ollama_model: str = "qwen2.5:7b-instruct"
    ollama_timeout_seconds: float = 90.0


settings = Settings()
