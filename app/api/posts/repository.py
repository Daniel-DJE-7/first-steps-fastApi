from typing import Optional, List, Tuple
from app.models import PostORM, TagORM, AuthorORM
from sqlalchemy import select, func, joinedload, selectinload
from sqlalchemy.orm import Session
from math import ceil

class PostRepository:
    def __init__(self, db: Session):
        self.db = db
        
    def get(self, post_id: int) -> Optional[PostORM]:
        post_find = select(PostORM).where(PostORM.id == post_id) 
        return self.db.execute(post_find).scalar_one_or_none()
        
    
    def search(self, 
               query: Optional[str], 
               sort_by: str,
               direction: str, 
               page: int, 
               post_per_page: int) -> Tuple[int, List[PostORM]]:
         
        results = select(PostORM)# select hace referencia al Select de SQL, es decir, que selecciona todos los registros de la tabla PostORM en la Base de datos
                                    
        if query:
            results = results.where(PostORM.title.ilike(f"%{query}%"))
                        
        total = self.db.scalar(select(func.count()).select_from(results.subquery())) or 0 # esto hace que se cuenten los resultados de la consulta, es decir, que se cuenten los registros de la tabla PostORM en la Base de datos, y si no hay resultados, devuelve 0
       
        if total == 0:
            return 0, []
               
        total_pages = ceil(total / post_per_page) # ceil redondea los decimales hacia arriba
        
        current_page = min(page, max(total_pages, 1)) # esto hace que si la página actual es mayor que el total de páginas, se devuelva la última página, y si la página actual es menor que 1, se devuelva la primera página
                                
        if sort_by == "id":
            order_column = PostORM.id
        else:
            order_column = func.lower(PostORM.title) # esto hace que se ordene por el título en minúsculas, es decir, que se ignore si es mayúscula o minúscula
                        
        results = results.order_by(order_column.asc() if direction == "asc" else order_column.desc())
                
        start = (current_page - 1) * post_per_page
        # items = results[start:start + post_per_page] # esto hace que se devuelvan los resultados desde el offset hasta el offset + limit, es decir, si offset=0 y limit=10, devuelve los primeros 10 resultados, si offset=10 y limit=10, devuelve los siguientes 10 resultados, etc.
        items = self.db.execute(results.limit(
            post_per_page).offset(start)).scalars().all()# offset va a sacar los registros de las páginas anteriores para no repetir valroes, y scalars.all() va extraer los valores del PostORM
        
        return total, items
    
    
    def by_tags(self, tag_names: List[str]) -> List[PostORM]:
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
        
        return self.db.execute(post_list).scalars().all()
        
    def ensure_author(self, name:str, email:str) -> AuthorORM:
        
        #obtenemos el author en caso de que exista
        
        author_obj = self.db.execute(
            select(AuthorORM).where(AuthorORM.email == email)# aqui buscamos un autor que tenga el email que se le pasa o solicta
        ).scalar_one_or_none()
        
        if author_obj:
            return author_obj #si encontro el author con el email solicitado, se pide que lo devuelva, si no, se crea uno nuevo con el nombre y email que se le pasa
        
        # if not author_obj:
        #             author_obj = AuthorORM(name=post.author.name, email=post.author.email)
        
        author_obj = AuthorORM(name=name, email=email)# aqui se crea un nuevo author con el nombre y email que se le pasa, si no existe uno con ese email
            
        self.db.add(author_obj)
        self.db.flush()# le creamos un id a author_obj 
        
        return author_obj # aqui se devuelve el author_obj que se acaba de crear cuando no se encuentra el author con el email solicitado
    
    def ensure_tags(self, name:str) -> TagORM:
        pass