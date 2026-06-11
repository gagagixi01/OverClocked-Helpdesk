from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "sqlite:///./helpdesk.db"

    # App
    APP_BASE_URL: str = "http://127.0.0.1:8000"

    # Slack
    SLACK_BOT_TOKEN: str | None = None
    SLACK_WEBHOOK_URL: str | None = None

    # Email
    SMTP_SERVER: str = "smtp.gmail.com"
    SMTP_PORT: int = 465
    SMTP_USER: str | None = None
    SMTP_PASSWORD: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )


settings = Settings()
