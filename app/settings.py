from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    llm_api_key: str = ""
    llm_model: str = "claude-haiku-4-5-20251001"


settings = Settings()
