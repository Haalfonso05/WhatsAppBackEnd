# Nodos del grafo multiagente
"""Nodos del grafo multiagente (HU-049 + HU-050 + HU-051)."""

from app.agents.llm import clasificar_texto, correr_agente
from app.agents import memoria

MENSAJE_ERROR = (
    "Uy, tuve un problema procesando tu mensaje. "
    "Puedes intentarlo de nuevo en un momento, por favor?"
)

FUERA_DE_TEMA = (
    "Solo puedo ayudarte con productos, pedidos, precios y entregas de "
    "Palmita Express. Que te gustaria pedir hoy?"
)

ACLARAR = (
    "No estoy segura de lo que necesitas. Quieres consultar un producto, "
    "hacer un pedido, ver el estado de tu pedido o registrarte?"
)


# decorador que captura errores dentro de un nodo
def nodo_seguro(fn):
    # funcion envuelto
    def envuelto(state):
        try:
            return fn(state)
        except Exception as e:
            print("[multiagente] Error en nodo " + fn.__name__ + ": " + str(e))
            return {"error": True, "respuesta": MENSAJE_ERROR}
    return envuelto



@nodo_seguro
# nodo de recepcion: carga memoria e identifica al cliente
def recepcion(state):
    telefono = state["telefono"]
    entrada = state["entrada"]

    
    if memoria.expirada(telefono):
        memoria.limpiar(telefono)

    cliente = memoria.get_cliente(telefono)
    if not cliente:
        from app.routers.webhook import buscar_cliente
        raw = buscar_cliente(telefono)
        cliente = {"raw": raw, "encontrado": raw != "CLIENTE_NO_ENCONTRADO"}
        memoria.set_cliente(telefono, cliente)

    memoria.agregar_historial(telefono, "user", entrada)
    memoria.tocar(telefono)

    return {
        "mensajes": [{"role": "user", "content": entrada}],
        "cliente": cliente,
        "carrito": memoria.get_carrito(telefono),
        "error": False,
    }



@nodo_seguro
# nodo que clasifica la intencion del mensaje
def clasificar(state):
    return {"intencion": clasificar_texto(state["entrada"], _contexto(state["telefono"]))}



_SYS_INVENTARIO = (
    "Eres el agente de inventario de Palmita Express. Usa buscar_productos sin exigir "
    "el nombre exacto: ignora mayusculas, tildes y plurales. Si hay varias "
    "coincidencias, muestralas todas como opciones con su precio; si no hay ninguna, "
    "ofrece alternativas. Usa verificar_stock y agrega al carrito lo que el cliente "
    "elija. Responde en espanol, amable y breve. El telefono del cliente es: {telefono}."
)
_SYS_PEDIDOS = (
    "Eres el agente de pedidos de Palmita Express. Revisa el carrito, verifica stock "
    "y muestra un resumen pidiendo confirmacion antes de crear el pedido. "
    "Responde en espanol, amable y breve. El telefono del cliente es: {telefono}."
)
_SYS_ATENCION = (
    "Eres el agente de atencion de Palmita Express. Primero usa buscar_cliente. "
    "Si el cliente NO existe, pidele nombre, apellido, cedula y direccion, y "
    "registralo con registrar_cliente. Si no quiere dar datos, ofrece continuar "
    "como invitado (documento='invitado'). Si ya existe, saludalo por su nombre. "
    "Responde en espanol, amable y breve. El telefono del cliente es: {telefono}."
)


# arma el contexto de la conversacion desde la memoria
def _contexto(telefono):
    
    msgs = memoria.get_historial(telefono)
    return "\n".join(m["role"] + ": " + m["content"] for m in msgs)


# ejecuta un agente (CrewAI) con respaldo a Claude directo
def _agente(state, fn_crew, system_tpl, nombres_herramientas):
    telefono = state["telefono"]
    try:
        from app.agents import crew
        texto = getattr(crew, fn_crew)(state["entrada"], telefono, _contexto(telefono))
    except Exception as e:
        print("[crewai] Fallback a Haiku directo en " + fn_crew + ": " + str(e))
        system = system_tpl.format(telefono=telefono)
        texto = correr_agente(system, memoria.get_historial(telefono), nombres_herramientas)

    memoria.agregar_historial(telefono, "assistant", texto)
    memoria.tocar(telefono)

    return {
        "mensajes": [{"role": "assistant", "content": texto}],
        "carrito": memoria.get_carrito(telefono),
        "respuesta": texto,
        "error": False,
    }


@nodo_seguro
# nodo del agente de inventario
def agente_inventario(state):
    return _agente(state, "responder_inventario", _SYS_INVENTARIO,
                   ["buscar_productos", "verificar_stock"])


@nodo_seguro
# nodo del agente de pedidos
def agente_pedidos(state):
    return _agente(state, "responder_pedidos", _SYS_PEDIDOS,
                   ["crear_pedido", "consultar_pedidos", "verificar_stock"])


@nodo_seguro
# nodo del agente de atencion al cliente
def agente_atencion(state):
    return _agente(state, "responder_atencion", _SYS_ATENCION,
                   ["buscar_cliente", "registrar_cliente"])


# 4. Nodos terminales.
def fuera_de_tema(state):
    memoria.agregar_historial(state["telefono"], "assistant", FUERA_DE_TEMA)
    return {
        "mensajes": [{"role": "assistant", "content": FUERA_DE_TEMA}],
        "respuesta": FUERA_DE_TEMA,
    }


# nodo que pide aclaracion cuando el mensaje es ambiguo
def aclarar(state):
    memoria.agregar_historial(state["telefono"], "assistant", ACLARAR)
    return {
        "mensajes": [{"role": "assistant", "content": ACLARAR}],
        "respuesta": ACLARAR,
    }


# nodo final que entrega la respuesta
def responder(state):
    if not state.get("respuesta"):
        return {"respuesta": MENSAJE_ERROR}
    return {}


# nodo que maneja los errores del grafo
def manejar_error(state):
    return {"respuesta": state.get("respuesta") or MENSAJE_ERROR}