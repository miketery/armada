from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://armada:armada@localhost:6130/armada"
    session_expire_minutes: int = 1440  # 24 hours

    model_config = {"env_prefix": "ARMADA_"}


settings = Settings()
