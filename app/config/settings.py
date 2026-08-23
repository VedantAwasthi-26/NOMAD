from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    mireye_api_key: str
    mireye_base_url: str

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        # .env now also carries GROQ_API_KEY and (optionally) NOMAD_ENGINE_MODEL
        # / LangSmith vars for app/engine -- none of those belong to this
        # Settings class, so tell pydantic-settings to ignore keys it
        # doesn't declare a field for, instead of the default (raise).
        extra="ignore",
    )


settings = Settings()