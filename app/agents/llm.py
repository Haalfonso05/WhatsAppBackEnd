# Cliente de Claude: clasificador y agente de respaldo
import os
import anthropic

from app.routers.webhook import (
    _tools,
    buscar_cliente,
    registrar_cliente,
    buscar_productos,
    verificar_stock,
    crear_pedido,
    consultar_pedidos,
)

MODELO = "claude-haiku-4-5"
_claude = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY", "").strip())

_DISPATCH = {
    "buscar_cliente": buscar_cliente,
    "registrar_cliente": registrar_cliente,
    "buscar_productos": buscar_productos,
    "verificar_stock": verificar_stock,
    "crear_pedido": crear_pedido,
    "consultar_pedidos": consultar_pedidos,
}


# filtra las herramientas por su nombre
def _tools_por_nombre(nombres: list[str]) -> list:
    return [t for t in _tools if t["name"] in nombres]

# clasifica la intencion del mensaje del cliente
def clasificar_texto(entrada: str, contexto: str = "") -> str:
    system = (
        "Eres un clasificador de intención para el chatbot de una tienda. "
        "Usa el contexto previo si ayuda a desambiguar. Responde EXACTAMENTE una "
        "etiqueta, sin explicaciones ni puntuación:\n"
        "consulta_producto, crear_pedido, estado_pedido, registro, saludo, fuera_de_tema, ambigua\n"
        "Usa 'saludo' para saludos o cortesia (hola, buenos dias, gracias). "
        "Usa 'ambigua' solo si el mensaje es demasiado vago para decidir."
    )
    user = entrada if not contexto else "Contexto previo:\n" + contexto + "\n\nMensaje actual: " + entrada
    resp = _claude.messages.create(
        model=MODELO,
        max_tokens=10,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    etiqueta = ""
    for bloque in resp.content:
        if hasattr(bloque, "text"):
            etiqueta = bloque.text.strip().lower()
            break
    validas = {"consulta_producto", "crear_pedido", "estado_pedido", "registro", "saludo", "fuera_de_tema", "ambigua"}
    return etiqueta if etiqueta in validas else "fuera_de_tema"


# ejecuta el agente de IA con sus herramientas (respaldo directo)
def correr_agente(system: str, historial: list, nombres_herramientas: list[str]) -> str:
    herramientas = _tools_por_nombre(nombres_herramientas)
    mensajes = [{"role": m["role"], "content": m["content"]} for m in historial]

    while True:
        resp = _claude.messages.create(
            model=MODELO,
            max_tokens=1024,
            system=system,
            tools=herramientas,
            messages=mensajes,
        )
        mensajes.append({"role": "assistant", "content": resp.content})

        if resp.stop_reason != "tool_use":
            break

        resultados = []
        for bloque in resp.content:
            if bloque.type == "tool_use":
                fn = _DISPATCH.get(bloque.name)
                salida = fn(**bloque.input) if fn else "Herramienta no disponible."
                resultados.append({
                    "type": "tool_result",
                    "tool_use_id": bloque.id,
                    "content": salida,
                })
        mensajes.append({"role": "user", "content": resultados})

    for bloque in resp.content:
        if hasattr(bloque, "text"):
            return bloque.text
    return "Lo siento, no pude procesar tu mensaje."