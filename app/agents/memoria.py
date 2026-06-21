# Memoria en RAM por telefono (sesion, carrito, historial)
"""Memoria compartida del sistema multiagente (HU-051).

Un almacen en memoria, indexado por telefono del cliente, que conservan todos
los agentes durante la conversacion: cliente identificado, carrito en
construccion e historial de mensajes. Incluye limite de historial (control de
tokens) y limpieza por inactividad o cambio de tema.
"""

import time

MAX_HISTORIAL = 12          
TIMEOUT_SEG = 30 * 60       

_memoria = {}               


# funcion nuevo
def _nuevo():
    return {"cliente": None, "carrito": [], "historial": [], "ultima_actividad": time.time()}


# obtiene la sesion en memoria de un telefono
def obtener(telefono):
    est = _memoria.get(telefono)
    if est is None:
        est = _nuevo()
        _memoria[telefono] = est
    return est


# indica si la sesion del telefono expiro
def expirada(telefono):
    est = _memoria.get(telefono)
    if not est:
        return False
    return (time.time() - est["ultima_actividad"]) > TIMEOUT_SEG


# actualiza la marca de tiempo de la sesion
def tocar(telefono):
    obtener(telefono)["ultima_actividad"] = time.time()


# limpia la memoria de un telefono
def limpiar(telefono):
    
    _memoria.pop(telefono, None)


# guarda el cliente en memoria
def set_cliente(telefono, cliente):
    obtener(telefono)["cliente"] = cliente


# obtiene el cliente desde memoria
def get_cliente(telefono):
    return obtener(telefono)["cliente"]


# agrega un producto al carrito
def agregar_item(telefono, nombre_producto, cantidad):
    obtener(telefono)["carrito"].append(
        {"nombre_producto": nombre_producto, "cantidad": cantidad}
    )
    return ver_carrito(telefono)


# obtiene el carrito del cliente
def get_carrito(telefono):
    return list(obtener(telefono)["carrito"])


# devuelve el carrito en texto
def ver_carrito(telefono):
    c = obtener(telefono)["carrito"]
    if not c:
        return "El carrito esta vacio."
    lineas = "\n".join("- " + str(i["cantidad"]) + " x " + str(i["nombre_producto"]) for i in c)
    return "Carrito actual:\n" + lineas


# vacia el carrito
def vaciar_carrito(telefono):
    obtener(telefono)["carrito"] = []


# agrega un mensaje al historial
def agregar_historial(telefono, role, content):
    h = obtener(telefono)["historial"]
    h.append({"role": role, "content": content})
    
    if len(h) > MAX_HISTORIAL:
        del h[:-MAX_HISTORIAL]
    return h


# obtiene el historial de la conversacion
def get_historial(telefono):
    return list(obtener(telefono)["historial"])