import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session, DeclarativeBase


DATABASE_URL = os.getenv("DATABASE_URL","sqlite:///./blog.db")

engine_kwargs = {}
if DATABASE_URL.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}

#conectar a la base de datos
engine = create_engine(DATABASE_URL, echo=True, future=True, **engine_kwargs)
#crear una sesion

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, class_=Session)

class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal() # inicializa la sesion a la base de datos
    try:
        yield db # yield devuelve la sesion a la base de datos, pero no cierra la sesion, por eso se usa el finally para cerrarla
    finally:
        db.close() # cierra la sesion a la base de datos