from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    APP_NAME: str = "My_Portfolio"
    APP_DOMAIN: str = "localhost:8000"

    model_config = SettingsConfigDict(
        env_ignore_empty=True,
        extra="ignore"
    )


class DatabaseSettings(BaseSettings):
    POSTGRES_SERVER: str
    POSTGRES_PORT: int
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str

    
    MONGO_URI: str 
    MONGO_DB_NAME: str

    model_config = SettingsConfigDict(
        env_file=".env",
        env_ignore_empty=True,
        extra="ignore"
    )

    @property
    def POSTGRES_URL(self):
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )


class SecuritySettings(BaseSettings):
    JWT_SECRET: str
    JWT_ALGORITHM: str

    model_config = SettingsConfigDict(
        env_file=".env",
        env_ignore_empty=True,
        extra="ignore"
    )


# These will now be filled by env vars or Docker Compose .env
app_settings = AppSettings()
db_settings = DatabaseSettings() # type: ignore
security_settings = SecuritySettings() # type: ignore
