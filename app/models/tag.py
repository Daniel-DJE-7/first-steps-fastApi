from __future__ import annotations
from typing import List, TYPE_CHECKING
from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.db import Base

if TYPE_CHECKING:
    from .post import PostORM


class TagORM(Base):
    __tablename__="tags"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    
    posts: Mapped[List["PostORM"]] = relationship(
        secondary="post_tags", #cual es la tabla con la cual se va a enlazar o la referencia
        back_populates="tags",#como se va a acceder a las tags
        lazy="selectin"
    )