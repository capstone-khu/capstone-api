from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.common.persistence import BaseEntity


class User(BaseEntity):
    __tablename__ = "users"

    name: Mapped[str] = mapped_column(String(50), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
