from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class BaseConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore",
    )


class AppSettings(BaseConfig):
    openai_api_key: str = Field(alias="OPENAI_API_KEY")
    api_url: str = Field(default="http://127.0.0.1:8000", alias="API_URL")
    admin_api_key: str | None = Field(default=None, alias="ADMIN_API_KEY")


class PostgresSettings(BaseConfig):
    user: str = Field(default="postgres", alias="DB_USER")
    password: str = Field(default="postgres", alias="DB_PASSWORD")
    name: str = Field(default="candidates", alias="DB_NAME")
    host: str = Field(default="localhost", alias="DB_HOST")
    port: int = Field(default=5433, alias="DB_PORT")


class RedisSettings(BaseConfig):
    url: str | None = Field(default="redis://localhost:6379", alias="REDIS_URL")
    cache_ttl: int = Field(default=86400, alias="CACHE_TTL")


class RateLimitSettings(BaseConfig):
    search: str = Field(default="20/hour", alias="RATE_LIMIT_SEARCH")
    onboarding: str = Field(default="20/hour", alias="RATE_LIMIT_ONBOARDING")
    extract: str = Field(default="20/hour", alias="RATE_LIMIT_EXTRACT")
    default: str = Field(default="20/hour", alias="RATE_LIMIT_DEFAULT")


class Settings:
    def __init__(self) -> None:
        self.app = AppSettings()
        self.postgres = PostgresSettings()
        self.redis = RedisSettings()
        self.rate_limit = RateLimitSettings()


settings = Settings()
