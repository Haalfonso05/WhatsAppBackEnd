import os
import httpx
import anthropic
from fastapi import APIRouter, Request, Response
from app.database import DB_SCHEMA
from sqlalchemy import text

router = APIRouter(prefix="/webhook", tags=["Webhook"])



WHATSAPP_TOKEN    = os.getenv("WHATSAPP_TOKEN", "")
PHONE_NUMBER_ID   = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
VERIFY_TOKEN      = os.getenv("WEBHOOK_VERIFY_TOKEN", "mi_token_secreto_123")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "").strip()

claude = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


_conversations: dict[str, list] = {}



def _get_db():
    from app.database import SessionLocal
    return SessionLocal()



def buscar_cliente(telefono: str) -> str:
    
    db = _get_db()
    try:
        phone_clean = telefono.replace("+", "").replace(" ", "")
        row = db.execute(text(f"""
            SELECT document, name_1, name_2, last_name_1, last_name_2, address, phone_number
            FROM {DB_SCHEMA}.customer
            WHERE phone_number = :phone OR document = :phone
            LIMIT 1
        """), {"phone": phone_clean}).mappings().fetchone()

        if not row:
            return "CLIENTE_NO_ENCONTRADO"

        nombre = f"{row['name_1']} {row['name_2'] or ''}".strip()
        apellido = f"{row['last_name_1']} {row['last_name_2'] or ''}".strip()
        direccion = row['address'] or "sin dirección registrada"
        return f"CLIENTE_ENCONTRADO|documento:{row['document']}|nombre:{nombre}|apellido:{apellido}|direccion:{direccion}"
    finally:
        db.close()

def registrar_cliente(telefono: str, nombre: str, apellido: str,
                      documento: str, direccion: str = "") -> str:
    
    db = _get_db()
    try:
        phone_clean = telefono.replace("+", "").replace(" ", "")
        partes_nombre = nombre.strip().split()
        name_1 = partes_nombre[0][:15]
        name_2 = partes_nombre[1][:15] if len(partes_nombre) > 1 else None

        partes_apellido = apellido.strip().split()
        last_name_1 = partes_apellido[0][:15]
        last_name_2 = partes_apellido[1][:15] if len(partes_apellido) > 1 else None

        doc = documento.strip()[:10] if documento and documento.lower() != "invitado" else phone_clean[:10]

        db.execute(text(f"""
            INSERT INTO {DB_SCHEMA}.customer
                (document, name_1, name_2, last_name_1, last_name_2, address, phone_number)
            VALUES (:doc, :n1, :n2, :l1, :l2, :addr, :phone)
            ON CONFLICT (document) DO UPDATE
                SET address = EXCLUDED.address,
                    phone_number = EXCLUDED.phone_number
        """), {
            "doc": doc, "n1": name_1, "n2": name_2,
            "l1": last_name_1, "l2": last_name_2,
            "addr": direccion or None, "phone": phone_clean
        })
        db.commit()
        return f"Cliente registrado exitosamente. Documento: {doc}, Nombre: {nombre} {apellido}."
    except Exception as e:
        db.rollback()
        return f"Error al registrar cliente: {str(e)}"
    finally:
        db.close()

def consultar_pedidos(telefono: str) -> str:
    
    db = _get_db()
    try:
        phone_clean = telefono.replace("+", "").replace(" ", "")
        rows = db.execute(text(f"""
            SELECT o.id_order, o.application_date, o.total,
                   COALESCE(MAX(d.delivery_status), 'P') AS estado,
                   COALESCE(STRING_AGG(DISTINCT p.name, ', '), '') AS productos
            FROM {DB_SCHEMA}."order" o
            JOIN {DB_SCHEMA}.customer c ON c.document = o.customer_document
            LEFT JOIN {DB_SCHEMA}.order_detail od ON od.order_id = o.id_order
            LEFT JOIN {DB_SCHEMA}.product p ON p.id_product = od.product_id
            LEFT JOIN {DB_SCHEMA}.delivery d ON d.order_id = o.id_order
            WHERE c.phone_number = :phone OR c.document = :phone
            GROUP BY o.id_order, o.application_date, o.total
            ORDER BY o.application_date DESC
            LIMIT 5
        """), {"phone": phone_clean}).mappings().all()

        if not rows:
            return "No encontré pedidos registrados para este cliente."

        _estados = {'P': 'En espera', 'E': 'Enviado', 'D': 'Listo/Entregado'}
        resultado = "Tus pedidos recientes:\n"
        for r in rows:
            estado = _estados.get(r['estado'], r['estado'])
            resultado += (f"- Pedido #{r['id_order']} | {r['application_date']} | "
                         f"{float(r['total']):,.0f} pesos | Estado: {estado}\n"
                         f"  Productos: {r['productos']}\n")
        return resultado
    finally:
        db.close()

def buscar_productos(nombre: str) -> str:
    
    db = _get_db()
    try:
        def normalizar(p):
            p = p.lower().strip()
            if p.endswith('es') and len(p) > 4:
                p = p[:-2]
            elif p.endswith('s') and len(p) > 3:
                p = p[:-1]
            return p

        palabras = [normalizar(p) for p in nombre.split() if len(p.strip()) > 2]
        if not palabras:
            palabras = [nombre]

        condiciones = " OR ".join([f"unaccent(name) ILIKE unaccent(:p{i})" for i in range(len(palabras))])
        params = {f"p{i}": f"%{p}%" for i, p in enumerate(palabras)}

        rows = db.execute(text(f"""
            SELECT name, reference_price, current_stock
            FROM {DB_SCHEMA}.product
            WHERE ({condiciones}) AND current_stock > 0
            ORDER BY name LIMIT 10
        """), params).mappings().all()

        if not rows:
            return f"No encontré productos relacionados con '{nombre}'."

        resultado = f"Productos encontrados para '{nombre}':\n"
        for r in rows:
            stock = float(r["current_stock"])
            precio = float(r["reference_price"])
            resultado += f"- {r['name']}: {precio:,.0f} pesos | {stock:.0f} unidades\n"
        return resultado
    finally:
        db.close()

def verificar_stock(nombre_producto: str, cantidad: int) -> str:
    
    db = _get_db()
    try:
        row = db.execute(text(f"""
            SELECT name, current_stock, reference_price
            FROM {DB_SCHEMA}.product
            WHERE unaccent(name) ILIKE unaccent(:q) AND current_stock > 0
            ORDER BY name LIMIT 1
        """), {"q": f"%{nombre_producto}%"}).mappings().fetchone()

        if not row:
            return f"No encontré el producto '{nombre_producto}'."

        stock = float(row["current_stock"])
        precio = float(row["reference_price"])
        if stock >= cantidad:
            return f"Sí hay stock de '{row['name']}': {stock:.0f} unidades. Precio unitario: {precio:,.0f} pesos."
        else:
            return f"Stock insuficiente para '{row['name']}': solo hay {stock:.0f} unidades, el cliente pide {cantidad}."
    finally:
        db.close()

def crear_pedido(telefono_cliente: str, productos: list,
                 direccion_entrega: str = "", notas: str = "") -> str:
    
    db = _get_db()
    try:
        phone_clean = telefono_cliente.replace("+", "").replace(" ", "")

        # Buscar cliente
        cliente = db.execute(text(f"""
            SELECT document, name_1, last_name_1, address
            FROM {DB_SCHEMA}.customer
            WHERE phone_number = :phone OR document = :phone
            LIMIT 1
        """), {"phone": phone_clean}).mappings().fetchone()

        if not cliente:
            return "Error: el cliente no está registrado. Usa registrar_cliente primero."

        customer_document = cliente["document"]
        client_name = f"{cliente['name_1']} {cliente['last_name_1']}"
        direccion = direccion_entrega or cliente["address"] or "Sin dirección"

        
        payment = db.execute(text(f"""
            SELECT id_payment_method FROM {DB_SCHEMA}.payment_method LIMIT 1
        """)).fetchone()
        payment_id = payment[0] if payment else 1

        
        total = 0.0
        lineas = []
        for item in productos:
            row = db.execute(text(f"""
                SELECT id_product, name, reference_price
                FROM {DB_SCHEMA}.product
                WHERE unaccent(name) ILIKE unaccent(:q)
                ORDER BY name LIMIT 1
            """), {"q": f"%{item['nombre_producto']}%"}).mappings().fetchone()

            if not row:
                return f"No encontré el producto '{item['nombre_producto']}'."

            precio = float(row["reference_price"])
            cantidad = item["cantidad"]
            subtotal = precio * cantidad
            total += subtotal
            lineas.append({
                "id_product": row["id_product"],
                "name": row["name"],
                "cantidad": cantidad,
                "precio": precio,
                "subtotal": subtotal,
            })

        
        result = db.execute(text(f"""
            INSERT INTO {DB_SCHEMA}."order"
                (customer_document, application_date, shipment_date,
                 discount, total, payment_method_id)
            VALUES (:doc, CURRENT_DATE, CURRENT_DATE + 1,
                    0, :total, :pm)
            RETURNING id_order
        """), {"doc": customer_document, "total": total, "pm": payment_id})
        db.commit()
        id_order = result.fetchone()[0]

        
        for linea in lineas:
            db.execute(text(f"""
                INSERT INTO {DB_SCHEMA}.order_detail
                    (order_id, customer_document, product_id, amount, sale_price, subtotal)
                VALUES (:oid, :doc, :pid, :amt, :sp, :sub)
            """), {
                "oid": id_order, "doc": customer_document,
                "pid": linea["id_product"], "amt": linea["cantidad"],
                "sp": linea["precio"], "sub": linea["subtotal"]
            })

        
        db.execute(text(f"""
            INSERT INTO {DB_SCHEMA}.delivery
                (delivery_address, delivery_date, customer_document,
                 hour_start, delivery_status, order_id, value)
            VALUES (:addr, CURRENT_DATE + 1, :doc, NOW(), 'P', :oid, 0)
        """), {"addr": direccion, "doc": customer_document, "oid": id_order})

        db.commit()

        resumen = "\n".join([
            f"- {l['name']} x{l['cantidad']}: {l['subtotal']:,.0f} pesos"
            for l in lineas
        ])
        return (f"Pedido #{id_order} creado para {client_name}.\n"
                f"{resumen}\n"
                f"Total: {total:,.0f} pesos.\n"
                f"Dirección de entrega: {direccion}")

    except Exception as e:
        db.rollback()
        return f"Error al crear el pedido: {str(e)}"
    finally:
        db.close()



_tools = [
    {
        "name": "buscar_cliente",
        "description": "Busca si un cliente ya está registrado por su número de teléfono. Úsala SIEMPRE al inicio de la conversación para saber si el cliente es nuevo o ya existe.",
        "input_schema": {
            "type": "object",
            "properties": {
                "telefono": {"type": "string", "description": "Número de teléfono del cliente"}
            },
            "required": ["telefono"]
        }
    },
    {
        "name": "registrar_cliente",
        "description": "Registra un cliente nuevo. Úsala cuando el cliente proporcione sus datos o cuando quiera continuar como invitado.",
        "input_schema": {
            "type": "object",
            "properties": {
                "telefono":   {"type": "string", "description": "Número de teléfono"},
                "nombre":     {"type": "string", "description": "Nombre(s) del cliente"},
                "apellido":   {"type": "string", "description": "Apellido(s) del cliente"},
                "documento":  {"type": "string", "description": "Número de cédula. Si es invitado usa 'invitado'"},
                "direccion":  {"type": "string", "description": "Dirección de entrega (opcional)"}
            },
            "required": ["telefono", "nombre", "apellido", "documento"]
        }
    },
    {
        "name": "consultar_pedidos",
        "description": "Consulta los pedidos recientes de un cliente. Úsala cuando el cliente pregunte por el estado de su pedido, 'cómo va mi pedido', 'mis pedidos', etc.",
        "input_schema": {
            "type": "object",
            "properties": {
                "telefono": {"type": "string", "description": "Teléfono del cliente"}
            },
            "required": ["telefono"]
        }
    },
    {
        "name": "buscar_productos",
        "description": "Busca productos disponibles en el inventario por nombre.",
        "input_schema": {
            "type": "object",
            "properties": {
                "nombre": {"type": "string", "description": "Nombre o parte del nombre del producto"}
            },
            "required": ["nombre"]
        }
    },
    {
        "name": "verificar_stock",
        "description": "Verifica si hay suficiente stock de un producto para una cantidad específica.",
        "input_schema": {
            "type": "object",
            "properties": {
                "nombre_producto": {"type": "string", "description": "Nombre del producto"},
                "cantidad":        {"type": "integer", "description": "Cantidad que el cliente quiere"}
            },
            "required": ["nombre_producto", "cantidad"]
        }
    },
    {
        "name": "crear_pedido",
        "description": "Crea el pedido en la base de datos cuando el cliente confirma. Úsala SOLO cuando el cliente confirme explícitamente (diga 'sí', 'listo', 'confirmo', etc.).",
        "input_schema": {
            "type": "object",
            "properties": {
                "telefono_cliente":  {"type": "string", "description": "Teléfono del cliente"},
                "productos": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "nombre_producto": {"type": "string"},
                            "cantidad":        {"type": "integer"}
                        },
                        "required": ["nombre_producto", "cantidad"]
                    }
                },
                "direccion_entrega": {"type": "string", "description": "Dirección de entrega"},
                "notas":             {"type": "string", "description": "Notas adicionales"}
            },
            "required": ["telefono_cliente", "productos"]
        }
    }
]

_SYSTEM_PROMPT = """Eres un asistente de ventas amable de Palmita Expres.

Al inicio de cada conversación nueva:
1. Usa buscar_cliente con el teléfono del cliente (viene en el mensaje como [phone:NUMERO]).
2. Si CLIENTE_NO_ENCONTRADO: salúdalo y pregúntale su nombre, apellido, cédula y dirección.
   - Si no quiere dar datos dile que puede continuar como invitado (en ese caso usa nombre="Invitado", apellido="Cliente", documento="invitado").
   - Registra al cliente con registrar_cliente antes de continuar.
3. Si CLIENTE_ENCONTRADO: salúdalo por su nombre y continúa normalmente.

Para los pedidos:
- Usa buscar_productos cuando el cliente mencione un producto.
- Usa verificar_stock cuando el cliente pida una cantidad específica.
- Si buscar_productos no encuentra el producto, dile al cliente: "Lo sentimos, no tenemos [producto] disponible en este momento." Luego usa buscar_productos con términos similares para ofrecer alternativas: "Pero tenemos: [lista de alternativas]."
- Si verificar_stock indica stock insuficiente, dile: "Solo tenemos [cantidad disponible] unidades de [producto]. ¿Deseas pedir esa cantidad?"
- NUNCA uses crear_pedido si algún producto tiene stock 0.
- Antes de crear el pedido, muestra el resumen y confirma con el cliente.
- Si el cliente es registrado y tiene dirección guardada, pregúntale si la usa o si tiene otra.
- Si es invitado, pídele la dirección de entrega.
- Cuando el cliente confirme, usa crear_pedido.
- Si el cliente pregunta por el estado de su pedido, usa consultar_pedidos con su teléfono.
- Si el cliente pide descuento, dile que consultas con el encargado. NO apruebes descuentos.

Habla siempre en español, de forma amigable y concisa.
El teléfono del cliente siempre viene al inicio del mensaje entre corchetes: [phone:NUMERO].
IMPORTANTE: Solo puedes ayudar con temas relacionados con la tienda — productos, pedidos, precios y entregas. Si el cliente pregunta algo que no tiene que ver con la tienda (consejos de vida, chistes, temas personales, etc.), responde amablemente que solo puedes ayudar con pedidos y productos de Palmita Expres. No te inventes un nombre propio.
"""



def _call_claude(phone: str, user_message: str) -> str:
    history = _conversations.get(phone, [])
    history.append({"role": "user", "content": f"[phone:{phone}] {user_message}"})

    while True:
        response = claude.messages.create(
            model="claude-haiku-4-5",
            max_tokens=1024,
            system=_SYSTEM_PROMPT,
            tools=_tools,
            messages=history,
        )

        history.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "tool_use":
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    fn = block.name
                    args = block.input
                    if fn == "consultar_pedidos":
                        result = consultar_pedidos(**args)
                    elif fn == "buscar_cliente":
                        result = buscar_cliente(**args)
                    elif fn == "registrar_cliente":
                        result = registrar_cliente(**args)
                    elif fn == "buscar_productos":
                        result = buscar_productos(**args)
                    elif fn == "verificar_stock":
                        result = verificar_stock(**args)
                    elif fn == "crear_pedido":
                        result = crear_pedido(**args)
                    else:
                        result = "Herramienta no encontrada."

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })

            history.append({"role": "user", "content": tool_results})
        else:
            break

    _conversations[phone] = history

    for block in response.content:
        if hasattr(block, "text"):
            return block.text
    return "Lo siento, no pude procesar tu mensaje."



def _send_whatsapp(to: str, message: str):
    url = f"https://graph.facebook.com/v21.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": message},
    }
    with httpx.Client() as c:
        c.post(url, json=payload, headers=headers)



@router.get("/")
def verify_webhook(request: Request):
    params = dict(request.query_params)
    mode      = params.get("hub.mode")
    token     = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")
    if mode == "subscribe" and token == VERIFY_TOKEN:
        return Response(content=challenge, media_type="text/plain")
    return Response(content="Forbidden", status_code=403)

@router.post("/")
async def receive_message(request: Request):
    body = await request.json()
    try:
        entry   = body["entry"][0]
        changes = entry["changes"][0]
        value   = changes["value"]

        if "messages" not in value:
            return {"status": "no_message"}

        msg      = value["messages"][0]
        phone    = msg["from"]
        msg_type = msg.get("type", "")

        if msg_type != "text":
            _send_whatsapp(phone, "Por ahora solo puedo atender mensajes de texto.")
            return {"status": "ignored"}

        user_text = msg["text"]["body"]
        try:
            from app.agents.graph import procesar_mensaje
            reply = procesar_mensaje(phone, user_text)
        except Exception as e:
            print("[multiagente] no disponible, uso agente simple:", e)
            reply = _call_claude(phone, user_text)
        _send_whatsapp(phone, reply)

    except Exception as e:
        print(f"Error procesando mensaje: {e}")

    return {"status": "ok"}
