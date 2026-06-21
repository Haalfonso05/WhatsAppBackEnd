# Construccion del grafo de estados con LangGraph
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from app.agents.state import ConversationState
from app.agents import nodes

# decide a que agente enviar segun la intencion
def router_intencion(state) -> str:
    if state.get("error"):
        return "error"
    return {
        "consulta_producto": "inventario",
        "crear_pedido": "pedidos",
        "estado_pedido": "pedidos",
        "registro": "atencion",
        "saludo": "atencion",
        "fuera_de_tema": "fuera_de_tema",
        "ambigua": "aclarar",
    }.get(state.get("intencion"), "fuera_de_tema")


# enruta al manejo de error si algo fallo
def enrutar_si_error(state) -> str:
    return "error" if state.get("error") else "ok"

# construye el grafo de estados con LangGraph
def construir_grafo():
    g = StateGraph(ConversationState)
    g.add_node("recepcion", nodes.recepcion)
    g.add_node("clasificar", nodes.clasificar)
    g.add_node("inventario", nodes.agente_inventario)
    g.add_node("pedidos", nodes.agente_pedidos)
    g.add_node("atencion", nodes.agente_atencion)
    g.add_node("fuera_de_tema", nodes.fuera_de_tema)
    g.add_node("aclarar", nodes.aclarar)
    g.add_node("responder", nodes.responder)
    g.add_node("manejar_error", nodes.manejar_error)
    g.add_edge(START, "recepcion")

    g.add_conditional_edges(
        "recepcion", enrutar_si_error,
        {"ok": "clasificar", "error": "manejar_error"},
    )

    g.add_conditional_edges(
        "clasificar", router_intencion,
        {
            "inventario": "inventario",
            "pedidos": "pedidos",
            "atencion": "atencion",
            "fuera_de_tema": "fuera_de_tema",
            "aclarar": "aclarar",
            "error": "manejar_error",
        },
    )

    for agente in ("inventario", "pedidos", "atencion"):
        g.add_conditional_edges(
            agente, enrutar_si_error,
            {"ok": "responder", "error": "manejar_error"},
        )

    g.add_edge("fuera_de_tema", "responder")
    g.add_edge("aclarar", "responder")
    g.add_edge("responder", END)
    g.add_edge("manejar_error", END)
    return g.compile(checkpointer=MemorySaver())


grafo = construir_grafo()


# procesa un mensaje del cliente a traves del grafo multiagente
def procesar_mensaje(telefono: str, texto: str) -> str:
    config = {"configurable": {"thread_id": telefono}}
    resultado = grafo.invoke(
        {"telefono": telefono, "entrada": texto},
        config=config,
    )
    return resultado.get("respuesta") or nodes.MENSAJE_ERROR