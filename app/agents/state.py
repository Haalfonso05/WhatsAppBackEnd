import operator
from typing import Annotated, Optional, TypedDict


class ConversationState(TypedDict, total=False):
    telefono: str                      
    entrada: str                       
    mensajes: Annotated[list, operator.add]
    cliente: Optional[dict]            
    carrito: list                     
    intencion: Optional[str]           
    respuesta: Optional[str]           
    error: bool                        
