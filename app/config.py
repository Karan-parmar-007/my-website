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
    
    # Token expiry (configurable)
    ACCESS_TOKEN_EXPIRY_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRY_DAYS: int = 30
    
    ENVIRONMENT: str = "production"
    
    # CSRF exempt paths (GET requests are always exempt)
    CSRF_EXEMPT_PATHS: list[str] = [
        "/api/v1/auth/login",
        "/api/v1/auth/signup",
        "/api/v1/auth/refresh",
        "/api/v1/auth/forgot-password",
        "/api/v1/auth/reset-password",
        # Swagger/OpenAPI documentation
        "/docs",
        "/redoc",
        "/openapi.json",
    ]
    
    # System admin bypass - these roles skip all permission checks
    SYSTEM_ADMIN_BYPASS_ROLES: list[str] = ["system_admin", "admin"]
    
    # Cron job - hour of day to run cleanup (0-23, 0 = midnight)
    REFRESH_TOKEN_CLEANUP_HOUR: int = 0
    
    # OTP Rate Limiting
    OTP_RESEND_DELAY_SECONDS: int = 30
    OTP_MAX_RESENDS: int = 2  # Total 3 sends (1 initial + 2 resends)
    
    # Password Change Limits
    MAX_PASSWORD_RESETS_PER_DAY: int = 2
    MAX_PASSWORD_CHANGES_PER_DAY: int = 2

    model_config = _base_config


class EmailSettings(BaseSettings):
    SMTP_HOST: str
    SMTP_PORT: int
    SMTP_USERNAME: str
    SMTP_PASSWORD: str
    SMTP_FROM_EMAIL: str
    SMTP_FROM_NAME: str = "My Website"
    
    model_config = _base_config


# These will now be filled by env vars or Docker Compose .env
db_settings = DatabaseSettings() # type: ignore
security_settings = SecuritySettings() # type: ignore
email_settings = EmailSettings() # type: ignore
