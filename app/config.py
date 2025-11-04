from pydantic_settings import BaseSettings, SettingsConfigDict

_base_config = SettingsConfigDict(
    env_file=".env",             
    env_file_encoding="utf-8",
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

    model_config = _base_config

    @property
    def POSTGRES_URL(self):
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )


class SecuritySettings(BaseSettings):
    JWT_SECRET: str
    JWT_ALGORITHM: str
    JWT_EXPIRATION_Days: int = 7
    JWT_EXPIRATION_MINUTES: int = 30

    model_config = _base_config


# These will now be filled by env vars or Docker Compose .env
db_settings = DatabaseSettings() # type: ignore
security_settings = SecuritySettings() # type: ignore
