import os

from dotenv import load_dotenv

# Подгружаем .env в os.environ при импорте модуля. Если файла нет, ничего
# не происходит — переменные ожидаются из окружения (как в Docker).
load_dotenv()


class Settings:
    """Конфигурация приложения, считанная из переменных окружения."""

    def __init__(self) -> None:
        self.postgres_host: str = os.getenv("POSTGRES_HOST", "localhost")
        self.postgres_port: int = int(os.getenv("POSTGRES_PORT", "5432"))
        self.postgres_user: str = os.getenv("POSTGRES_USER", "enricher")
        self.postgres_password: str = os.getenv("POSTGRES_PASSWORD", "enricher")
        self.postgres_db: str = os.getenv("POSTGRES_DB", "enricher")

        self.api_base_url: str = os.getenv("API_BASE_URL", "https://dummyjson.com")
        # Шаблон пути к эндпоинту обогащения. Доступные плейсхолдеры:
        #   {user_id} — детерминированно полученный из `key` числовой id
        #   {key}     — исходное значение из БД (наш номер телефона)
        # Меняется без правки кода — например: /api/v1/customers/{key}
        self.api_path: str = os.getenv("API_PATH", "/users/{user_id}")
        self.api_timeout: float = float(os.getenv("API_TIMEOUT", "10.0"))

        self.batch_size: int = int(os.getenv("BATCH_SIZE", "50"))
        self.log_level: str = os.getenv("LOG_LEVEL", "INFO")

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


settings = Settings()
