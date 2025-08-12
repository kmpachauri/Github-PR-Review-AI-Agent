import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://redis:6379/0")
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    MODEL_NAME: str = os.getenv("MODEL_NAME", "gpt-3.5-turbo")  
    GITHUB_API_BASE: str = "https://api.github.com"

settings = Settings()
