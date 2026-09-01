
from __future__ import annotations
from sqlalchemy import UniqueConstraint, ForeignKey
from datetime import datetime
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import Integer, String, DateTime, Text, Table, Column
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.db import Base

if TYPE_CHECKING:
    from .author import AuthorORM
    from .tag import TagORM

post_tags = Table(
    "post_tags",# nombre de la tabla
    Base.metadata,
    Column("post_id", ForeignKey("posts.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True)
)

class PostORM(Base):
    __tablename__ = "posts"# Este es el nombre de la tabla en la base de datos
    __table_args__ = (UniqueConstraint("title", name="unique_post_title"),) # esto hace que el título del post sea único, es decir, que no se puedan crear dos posts con el mismo título
    
    #Los siguientes son los atributos de la tabla
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    create_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    #informamos a los post la relación con la clase Author
    author_id: Mapped[Optional[int]] = mapped_column(ForeignKey("authors.id"))#esta relacionando la llave primaria con la foranea como en sql
    author: Mapped[Optional["AuthorORM"]] = relationship(back_populates="posts") #esta es la relacion de 1 a muchos, 1 author tiene muchos posts
    
    tags: Mapped[List["TagORM"]] = relationship(
        secondary=post_tags,# aqui le decimos que queremos que tags sea relacionado con la tabla intermedia que es post_tags
        back_populates="posts",# aqui se ele dice cómo va a acceder los tags a los posts
        lazy="selectin", # la búsqueda se va a hacer con selectin
        passive_deletes=True# esto es para respetar el ON DELETE CASCADE
    )