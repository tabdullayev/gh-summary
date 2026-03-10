from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    NEBIUS_API_KEY: str
    NEBIUS_BASE_URL: str = "https://api.studio.nebius.com/v1/"
    LLM_MODEL: str = "Qwen/Qwen3-Coder-30B-A3B-Instruct"
    TOKEN_BUDGET: int = 12000
    GITHUB_TOKEN: str | None = None

    model_config = {"env_file": ".env"}


settings = Settings()
