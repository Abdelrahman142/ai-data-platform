from pydantic import BaseModel

class Settings(BaseModel):
    PROJECT_NAME: str = "Data Preparation Platform"
    SECRET_KEY: str = "supersecretkey"  # TODO: Use environment variables
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    DATABASE_URL: str = "postgresql://dbuser:dbpassword@localhost/db"

settings = Settings()
