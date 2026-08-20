import os
from datetime import datetime
from string import capwords
from fastapi import FastAPI, Query, Body, HTTPException, Path, status, Depends
from pydantic import BaseModel, Field, field_validator, EmailStr, ConfigDict
from typing import Optional, List, Union, Literal
from math import ceil
from sqlalchemy import create_engine, Integer, String, DateTime, Text, select, func
from sqlalchemy.orm import sessionmaker, Session, DeclarativeBase, Mapped, mapped_column
from sqlalchemy.exc import SQLAlchemyError

DATABASE_URL = os.getenv("DATABASE_URL","sqlite:///./blog.db")
print("conectado a: ", DATABASE_URL)

engine_kwargs = {}
if DATABASE_URL.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}

#conectar a la base de datos
engine = create_engine(DATABASE_URL, echo=True, future=True, **engine_kwargs)
#crear una sesion

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, class_=Session)


class Base(DeclarativeBase):
    pass

class PostORM(Base):
    __tablename__ = "posts"# Este es el nombre de la tabla en la base de datos
    #Los siguientes son los atributos de la tabla
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    create_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
Base.metadata.create_all(bind=engine) # crea la tabla en la base de datos si no existe, esto es para etapa de desarrollo porque para producción se van a crear migraciones

def get_db():
    db = SessionLocal() # inicializa la sesion a la base de datos
    try:
        yield db # yield devuelve la sesion a la base de datos, pero no cierra la sesion, por eso se usa el finally para cerrarla
    finally:
        db.close() # cierra la sesion a la base de datos


app = FastAPI(title="Mini Blog")

#POST

BLOG_POST = [
    {"id": 1, "title": "Hola desde FastAPI", "content": "Mi primer post con FastAPI"},
    {"id": 2, "title": "Mi segundo POST CON FastAPI", "content": "Mi segundo post con FastAPI"},
    {"id": 3, "title": "Django vs FastAPI", "content": "FastAPI es más rápido por x razón"},
    {"id": 4, "title": "Hola desde FastAPI", 
     "content": "Mi primer post con FastAPI"},
    {"id": 5, "title": "Mi segundo POST CON FastAPI", 
     "content": "Mi segundo post con FastAPI",
     "tag": [
        {"name": "python"},
        {"name": "fastapi"},
        {"name": "cluster"}
        ]
     },
    {"id": 6, "title": "Django vs FastAPI", "content": "FastAPI es más rápido por x razón"},
    {"id": 7, "title": "Hola desde FastAPI", "content": "Mi primer post con FastAPI"},
    {"id": 8, "title": "Mi segundo POST CON FastAPI", "content": "Mi segundo post con FastAPI"},
    {"id": 9, "title": "Django vs FastAPI", 
     "content": "FastAPI es más rápido por x razón", 
     "tag": [
            {"name": "Python"},
            {"name": "fastapi"},
            {"name": "Cluster"}
            ]
     },
    {"id": 10, "title": "Hola desde FastAPI", "content": "Mi primer post con FastAPI"},
    {"id": 11, "title": "Mi segundo POST CON FastAPI", "content": "Mi segundo post con FastAPI"},
    {"id": 12, "title": "Django vs FastAPI", 
     "content": "FastAPI es más rápido por x razón", 
     "tag": [
            {"name": "python"},
            {"name": "fastapi"},
            {"name": "cluster"}
            ]
     },
]

class Tag(BaseModel):
    name: str = Field(..., 
                      min_length=3,
                      max_length=30,
                      description="Nombre de la etiqueta"
                      )

class Author(BaseModel):
    name: str
    email: EmailStr

#CAMPOS OPCIONALES POR DEFECTO
class PostBase(BaseModel):
    title: Optional[str] = "Título no disponible"
    content: str
    tag: Optional[List[Tag]] = Field(default_factory=list) # esto crea un array [] vacía por cada objeto en el programa
    author: Optional[Author] = None
  
  
##VALIDACIONES FIELD Y AVANZADAS   
class PostCreate(BaseModel):
    title: str = Field(
        ...,
        min_length=3,
        max_length=100,
        description="Título del post (mínimo 3 caracteres, max 100)",
        examples= ["Mi primer post con Fast API"]
    )
    content: Optional[str] = Field(
        default="Contenido no disponible",
        min_length=10,
        description="Contenido mínimo de 10 carácteres",
        examples= ["Este es un contenido valido porque tiene 10 o más caracteres"]
    )
    tag: List[Tag] = Field(default_factory=list)
    author: Optional[Author] = None
    
    ##VALIDACIONES PERSONALIZADAS
    @field_validator("title")
    @classmethod
    def not_allowrd_title(cls, value:str) -> str:
        banned_words: list[str] = [
            "marica",
            "porno",
            "idiota",
            "petro"
        ] 
        for words in banned_words:
            if words in value.lower():
                raise ValueError(f"El título no puede contener la palabra '{words}'")
        return value
        

class PostUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=100)
    content: Optional[str] = None
    
#RESPUESTAS PERSONALIZADAS
class PostPublic(PostBase):
    id: int
    #model config sirve para que se pueda enviar los datos de la clase a la ORM, es decir, que los datos que se envien se conviertan a objetos JSON
    model_config = ConfigDict(from_attributes=True) # esto hace que se pueda usar el modelo con objetos de la base de datos, es decir, que se pueda usar con SQLAlchemy

class PostSummary(BaseModel):
    id: int
    title: str
    
    model_config = ConfigDict(from_attributes=True) # esto hace que se pueda usar el modelo con objetos de la base de datos, es decir, que se pueda usar con SQLAlchemy

class PaginatedPost(BaseModel):
    page: int
    post_per_page: int
    total: int
    total_pages: int
    has_prev: bool
    has_next: bool
    sort_by: Literal["id", "title"]
    direction: Literal["asc", "desc"]
    search: Optional[str] = None #si es por default, va un none
    items: List[PostPublic]
    


@app.get("/")
def home():
    return {'message': 'Bienvenido al mini Blog por Daniel Figueredo h'}


# QUERY PARAMS
@app.get("/posts", response_model=PaginatedPost)
def list_posts(text: Optional[str] = Query(
                        default=None, # None significa que no es obligatorio, si no se pasa el query, devuelve todos los post 
                        deprecated=True, #deprecated significa que el query param está obsoleto y no se debería usar o se dejara de usar en el futuro
                        description="Texto para busar por título"
                    ),
               query: Optional[str] = Query(
                        default=None, # None significa que no es obligatorio, si no se pasa el query, devuelve todos los post 
                        description="Texto para busar por título",
                        alias="search", #alias para cambiar el nombre del query param
                        min_length=3,
                        max_length=50,
                        pattern="^[a-zA-Z1-9]+$"
                    ),  
               post_per_page: int = Query(
                   10,#10 es el valor por defecto si no se pasa el query param
                   ge=1,
                   le=50,
                   description="Número máximo de resultados mostrar (1-50)"
               ),
                page: int = Query(
                     1,
                     ge=1,
                     description="Número de página (>=1)"
                ),
                sort_by: Literal["id", "title"] = Query(
                  "id",
                  description="Campo por el cual ordenar los resultados (id o title)"  
                ),
                direction: Literal["asc", "desc"] = Query(
                    "asc",
                    description="Dirección de ordenamiento (asc o desc)"
                ),
                db: Session = Depends(get_db) # esto hace que se inyecte la sesión de la base de datos en la función, es decir, que se pueda usar la sesión de la base de datos para hacer consultas a la base de datos
               
):
    results = select(PostORM)# select hace referencia al Select de SQL, es decir, que selecciona todos los registros de la tabla PostORM en la Base de datos
    
    query = query or text # esto era para poner una opcion alternativa en caso de que el query param "query" este deprecado, se use el query param "text" en su lugar, pero ahora ya no es necesario porque se usa el alias "search" para el query param "query"
    
    if query:
        results = results.where(PostORM.title.ilike(f"%{query}%"))
    
    total = db.scalar(select(func.count()).select_from(results.subquery())) or 0 # esto hace que se cuenten los resultados de la consulta, es decir, que se cuenten los registros de la tabla PostORM en la Base de datos, y si no hay resultados, devuelve 0
    total_pages = ceil(total / post_per_page) if total > 0 else 0 # ceil redondea los decimales hacia arriba
    
    if total_pages == 0:
        current_page = 1
    else:
        current_page = min(page, total_pages)
    
    if sort_by == "id":
        order_column = PostORM.id
    else:
        order_column = func.lower(PostORM.title) # esto hace que se ordene por el título en minúsculas, es decir, que se ignore si es mayúscula o minúscula
    
    results = results.order_by(order_column.asc() if direction == "asc" else order_column.desc())
    # results = sorted(results, 
    #                  key=lambda post: post[sort_by], 
    #                  reverse=(direction == "desc")
    #                 )
    
    if total_pages == 0:
        items: List[PostORM] = [] 
    else:
        start = (current_page - 1) * post_per_page
        # items = results[start:start + post_per_page] # esto hace que se devuelvan los resultados desde el offset hasta el offset + limit, es decir, si offset=0 y limit=10, devuelve los primeros 10 resultados, si offset=10 y limit=10, devuelve los siguientes 10 resultados, etc.
        items = db.execute(results.limit(
            post_per_page).offset(start)).scalars().all()# offset va a sacar los registros de las páginas anteriores para no repetir valroes, y scalars.all() va extraer los valores del PostORM
       
    has_prev = current_page > 1
    has_next = current_page < total_pages if total_pages > 0 else False
   
    return PaginatedPost(
                        page=current_page,
                        post_per_page=post_per_page,
                        total=total,
                        total_pages=total_pages,
                        has_prev=has_prev,
                        has_next=has_next,
                        sort_by=sort_by,
                        direction=direction,
                        search=query,
                        items=items
                        )

@app.get("/posts/by-tags", response_model=List[PostPublic])
def filter_by_tags(
    tags: List[str] = Query(
                            ..., min_length=2, 
                            description="Una o más etiquetas. Ejemplo: ?tags=python&tags=fastapi"
                            )
    ):
    
    # tags_lower = []
    # for tag in tags:        tags_lower.append(tag.lower())
    
    # filtered_posts = []
    # for post in BLOG_POST:
    #     post_tags = post.get("tag", [])
    #     for tag in post_tags:
    #         if tag["name"].lower() in tags_lower:
    #             filtered_posts.append(post)
    #             break
    
    #     return filtered_posts
    
    tags_lower = [tag.lower() for tag in tags]
    
    return [
        post for post in BLOG_POST 
        if any(tag["name"].lower() in tags_lower for tag in post.get("tag", []))
    ]


# PATH PARAMETERS, SIRVE PARA FILTRAR LOS ELEMENTOS QUE QUIERO VER
@app.get("/posts/{post_id}", 
         response_model=Union[PostPublic, PostSummary],
         response_description="Post no encontrado")
def get_post_id(post_id: int = Path(
                    ...,
                    ge=1,#esto hace que no se acepten id como "0, -1,-2, etc"
                    title="ID del post",
                    description="ID del post a mostrar",
                    example=1
                ), 
                query_include_content: bool = Query(
                    default=False, #
                    description="¿Incluir contenido?"),
                db: Session = Depends(get_db)
                ):
    
    post_find = select(PostORM).where(PostORM.id == post_id) 
    post = db.excecute(post_find).scalar_one_or_none()
    
    #post = db.get(PostORM, post_id) # esto hace que se busque el post en la base de datos por su id
    
    if not post:
        raise HTTPException(status_code=404, detail="Post no encontrado")
    
    if query_include_content:
        return PostPublic.model_validate(post, from_attributes=True) # esto hace que se devuelvan todos los campos del post, incluyendo el contenido)
    
    return PostSummary.model_validate(post, from_attributes=True) # esto hace que se devuelvan solo los campos id y title del post, sin el contenido

#POST -> Crear post
@app.post("/posts", response_model=PostPublic, 
          response_description="Post creado GREAT",
          status_code=status.HTTP_201_CREATED
          )
def create_post(post: PostCreate, db: Session = Depends(get_db)):
   
   new_post = PostORM(title=post.title, content=post.content)#llamamos el model ORM creado y le pasa el titulo y contenido del post que se recibe en el body de la petición, esto es para crear un nuevo post en la base de datos
   try:
       # 1. se debe marcar la inserción
       db.add(new_post)
       # 2. se debe hacer commit "confirmar" para que se ejecute la inserción
       db.commit()
       #3. se deben traer los valores generados por la base de datos, como el id y la fecha de creación
       db.refresh(new_post)
       return new_post
   except SQLAlchemyError:
       db.rollback() # en caso de error, se debe hacer rollback para deshacer la inserción u operación que se estaba haciendo
       raise HTTPException(status_code=500, detail="Error al crear el post")

#PUT
@app.put(
        "/posts/{post_id}", 
         response_model = PostPublic, 
         response_description="Post actualizado", 
         response_model_exclude_none= True#excluye los valores NONE
         )
def update_post(post_id: int, data: PostUpdate):
    for post in BLOG_POST:
        if post["id"] == post_id:
            playload = data.model_dump(exclude_unset=True)
            if "title" in playload: post["title"] = playload["title"]
            if "content" in playload: post["content"] = playload["content"]
            return post
    raise HTTPException(status_code=404, detail="Post no encontrado")


#DELETE
@app.delete("/posts/{post_id}", status_code=204)
def delete_post(post_id: int):
    for index, post in enumerate(BLOG_POST):
        if post["id"] == post_id:
            BLOG_POST.pop(index)
            return 
    raise HTTPException(status_code=404, detail= "Post no encontrado")