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


def _nuevo():
    return {"cliente": None, "carrito": [], "historial": [], "ultima_actividad": time.time()}


def obtener(telefono):
    est = _memoria.get(telefono)
    if est is None:
        est = _nuevo()
        _memoria[telefono] = est
    return est


def expirada(telefono):
    est = _memoria.get(telefono)
    if not est:
        return False
    return (time.time() - est["ultima_actividad"]) > TIMEOUT_SEG


def tocar(telefono):
    obtener(telefono)["ultima_actividad"] = time.time()


def limpiar(telefono):
    
    _memoria.pop(telefono, None)


def set_cliente(telefono, cliente):
    obtener(telefono)["cliente"] = cliente


def get_cliente(telefono):
    return obtener(telefono)["cliente"]


def agregar_item(telefono, nombre_producto, cantidad):
    obtener(telefono)["carrito"].append(
        {"nombre_producto": nombre_producto, "cantidad": cantidad}
    )
    return ver_carrito(telefono)


def get_carrito(telefono):
    return list(obtener(telefono)["carrito"])


def ver_carrito(telefono):
    c = obtener(telefono)["carrito"]
    if not c:
        return "El carrito esta vacio."
    lineas = "\n".join("- " + str(i["cantidad"]) + " x " + str(i["nombre_producto"]) for i in c)
    return "Carrito actual:\n" + lineas


def vaciar_carrito(telefono):
    obtener(telefono)["carrito"] = []


def agregar_historial(telefono, role, content):
    h = obtener(telefono)["historial"]
    h.append({"role": role, "content": content})
    
    if len(h) > MAX_HISTORIAL:
        del h[:-MAX_HISTORIAL]
    return h


def get_historial(telefono):
    return list(obtener(telefono)["historial"])
