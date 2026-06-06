# config.py
# Reads all environment variables from .env using pydantic-settings.
# Never hardcode secrets or URLs in your code — always read from env.
# In interviews: mention 12-factor app principles here.

from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str = "sqlite:///./url_shortener.db"
    base_url: str = "http://localhost:8000"
    app_name: str = "URL Shortener"

    class Config:
        env_file = ".env"

# Single instance shared across the app — imported wherever needed
settings = Settings()