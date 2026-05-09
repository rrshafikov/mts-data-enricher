from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings

# pool_pre_ping=True — перед каждым использованием соединения SQLAlchemy
# делает быстрый ping. В Docker-сценарии это спасает от ошибок «server closed
# the connection unexpectedly», когда контейнер с PG перезапустился, а пул
# соединений ещё держит «мёртвые» дескрипторы.
engine = create_engine(
    settings.database_url,
    echo=False,
    pool_pre_ping=True,
    future=True,
)

# expire_on_commit=False — после commit() атрибуты ORM-объектов не сбрасываются
# и доступны для чтения без дополнительного SELECT'а. Удобно в тестах и при
# логировании уже закоммиченной строки.
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)
