from typing import Optional, List, Union, Literal
from pydantic import BaseModel, Field, field_validator, EmailStr, ConfigDict


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