import os
from datetime import datetime
from string import capwords
from fastapi import FastAPI, Query, Body, HTTPException, Path, status, Depends
from pydantic import BaseModel, Field, field_validator, EmailStr, ConfigDict
from typing import Optional, List, Union, Literal
from math import ceil
from sqlalchemy import create_engine, Integer, String, DateTime, Text, select, func, UniqueConstraint, ForeignKey, Table, Column
from sqlalchemy.orm import sessionmaker, Session, DeclarativeBase, Mapped, mapped_column, relationship, selectinload, joinedload
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
#from dotenv import load_dotenv#poner esto en caso de que no encuentre la BD

#load_dotenv()

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

post_tags = Table(
    "post_tags",# nombre de la tabla
    Base.metadata,
    Column("post_id", ForeignKey("posts.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True)
)

class AuthorORM(Base):
    __tablename__ = "authors"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(100), unique=True, index=True)

    #creamos la relación de uno a muchos
    posts: Mapped[List["PostORM"]] = relationship(back_populates="author")# este es el nombre con el cual se relaciona con los Post

class TagORM(Base):
    __tablename__="tags"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    
    posts: Mapped[List["PostORM"]] = relationship(
        secondary=post_tags, #cual es la tabla con la cual se va a enlazar o la referencia
        back_populates="tags",#como se va a acceder a las tags
        lazy="selectin"
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
    
Base.metadata.create_all(bind=engine) # crea la tabla en la base de datos si no existe, esto es para etapa de desarrollo porque para producción se van a crear migraciones

def get_db():
    db = SessionLocal() # inicializa la sesion a la base de datos
    try:
        yield db # yield devuelve la sesion a la base de datos, pero no cierra la sesion, por eso se usa el finally para cerrarla
    finally:
        db.close() # cierra la sesion a la base de datos


app = FastAPI(title="Mini Blog")

class Tag(BaseModel):
    name: str = Field(..., 
                      min_length=3,
                      max_length=30,
                      description="Nombre de la etiqueta"
                      )
    
    model_config = ConfigDict(from_attributes=True)# esto significa que esta clase tambien a¡va a aceptar objetos ORM porque si no, solo recibiria dictionarios y si no hay dictionarios, no sabe que hacer

class Author(BaseModel):
    name: str
    email: EmailStr
    
    model_config = ConfigDict(from_attributes=True)

#CAMPOS OPCIONALES POR DEFECTO
class PostBase(BaseModel):
    title: Optional[str] = "Título no disponible"
    content: str
    tags: Optional[List[Tag]] = Field(default_factory=list) # esto crea un array [] vacía por cada objeto en el programa
    author: Optional[Author] = None
    
    model_config = ConfigDict(from_attributes=True)
  
  
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
def filter_by_tags(tags: List[str] = Query(
                            ..., min_length=1, 
                            description="Una o más etiquetas. Ejemplo: ?tags=python&tags=fastapi"
                            ),
                   db: Session = Depends(get_db)
    ):
    normailized_tag_names = [tag.strip().lower() for tag in tags if tag.strip()]#strip remueve los espacios en blanco del texto
    
    if not normailized_tag_names:
        return []
    
    # esto crea una query para los post y luego para todas las demás etiquetas
    post_list = (select(PostORM)
                 .options(
                     selectinload(PostORM.tags),
                     joinedload(PostORM.author)
                     ).where(PostORM.tags.any(func.lower(TagORM.name).in_(normailized_tag_names)))# si el nombre de la etiqueta del post está dentro de la lista normalizada, significa que está incluida y luego se ordena
                 .order_by(PostORM.id.asc())
                )
    
    post = db.execute(post_list).scalars().all()
    
    return post


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
    post = db.execute(post_find).scalar_one_or_none()
    
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
   author_obj = None
   #obtenemos el author en caso de que exista
   if post.author:
        author_obj = db.execute(
            select(AuthorORM).where(AuthorORM.email == post.author.email)
        ).scalar_one_or_none()
        
        if not author_obj:
            author_obj = AuthorORM(name=post.author.name, email=post.author.email)
            
            db.add(author_obj)
            db.flush()# le creamos un id a author_obj
    
        
   new_post = PostORM(title=post.title, content=post.content, author=author_obj)#llamamos el model ORM creado y le pasa el titulo y contenido del post que se recibe en el body de la petición, esto es para crear un nuevo post en la base de datos
   for tag in post.tag:
        tag_obj = db.execute(
           select(TagORM).where(TagORM.name.ilike(tag.name))
        ).scalar_one_or_none()
        if not tag_obj:
            tag_obj = TagORM(name=tag.name)
            db.add(tag_obj)
            db.flush()     
        new_post.tags.append(tag_obj)
        
   try:
       # 1. se debe marcar la inserción
       db.add(new_post)
       # 2. se debe hacer commit "confirmar" para que se ejecute la inserción
       db.commit()
       #3. se deben traer los valores generados por la base de datos, como el id y la fecha de creación
       db.refresh(new_post)
       return new_post
   except IntegrityError:
       db.rollback() # en caso de error, se debe hacer rollback para deshacer la inserción u operación que se estaba haciendo
       raise HTTPException(status_code=409, detail="El título del post ya existe, prueba con otro")
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
def update_post(post_id: int, data: PostUpdate, db: Session = Depends(get_db)):
    #obtenemos el valor del post a través del post_id
    post_update = db.get(PostORM, post_id)
    #validar que el post no exista
    if not post_update:
        raise HTTPException(status_code=404, detail="Post no encontrado")
    
   #Exraer los datos de los campos que envia el usuario
    updates = data.model_dump(exclude_unset=True)# esto evita que la respuesta aparezca en null en campos que no se envian
   
   #extraer el valor
    for key, value in updates.items():
        setattr(post_update, key, value) # esto hace que se actualicen los valores del post en la base de datos
   
   #agregar guardar en la base de datos
    db.add(post_update)
    db.commit()
    db.refresh(post_update)#aqui se actualiza en la BD
    
    return post_update


#DELETE
@app.delete("/posts/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_post(post_id: int, db: Session = Depends(get_db)):
    post_deleted = db.get(PostORM, post_id)
    if not post_deleted:
        raise HTTPException(status_code=404, detail = "Post no encontrado")
    
    db.delete(post_deleted)
    db.commit()
    
    return 