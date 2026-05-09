from sqlalchemy import String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Item(Base):
    """Запись в очереди обогащения.

    Ровно те поля, что описаны в ТЗ: id, key, additional_info, status.
    """

    __tablename__ = "items"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Бизнес-идентификатор записи (в нашем сценарии — номер телефона).
    # Длина 255 — компромисс: хватит и для телефонов, и для UUID/email,
    # если в реальной интеграции key окажется чем-то другим.
    key: Mapped[str] = mapped_column(String(255), nullable=False)
    # Куда складываем ответ внешнего API. Тип Text, потому что объём
    # ответа заранее не известен (мы кладём JSON-строку).
    additional_info: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Индекс на status — горячая колонка: каждый запуск воркера делает
    # `WHERE status='pending'`. Без индекса — full scan на больших объёмах.
    # default ставится Python'ом при создании объекта, server_default —
    # дефолт на уровне PG, страхует от вставок мимо ORM.
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="pending", server_default="pending", index=True
    )

    def __repr__(self) -> str:
        return f"Item(id={self.id!r}, key={self.key!r}, status={self.status!r})"
