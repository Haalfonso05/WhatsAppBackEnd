"""Agentes especializados con CrewAI (HU-050) + carrito compartido (HU-051)."""

from crewai import Agent, Task, Crew, LLM
from crewai.tools import BaseTool

from app.agents import memoria
from app.routers.webhook import (
    buscar_cliente as _buscar_cliente,
    registrar_cliente as _registrar_cliente,
    buscar_productos as _buscar_productos,
    verificar_stock as _verificar_stock,
    crear_pedido as _crear_pedido,
    consultar_pedidos as _consultar_pedidos,
)

# Modelo subyacente de los agentes: Claude Haiku (via la capa LLM de CrewAI).
_llm = LLM(model="anthropic/claude-haiku-4-5", temperature=0.3)


# --------------------------------------------------------------------------- #
# Herramientas: la descripcion es un atributo (no depende de docstring).
# --------------------------------------------------------------------------- #
class BuscarClienteTool(BaseTool):
    name: str = "buscar_cliente"
    description: str = "Busca si un cliente ya esta registrado por su numero de telefono."

    def _run(self, telefono: str) -> str:
        return _buscar_cliente(telefono)


class RegistrarClienteTool(BaseTool):
    name: str = "registrar_cliente"
    description: str = ("Registra un cliente nuevo con nombre, apellido, documento y "
                        "direccion. Usa documento='invitado' si no quiere dar datos.")

    def _run(self, telefono: str, nombre: str, apellido: str,
             documento: str, direccion: str = "") -> str:
        return _registrar_cliente(telefono, nombre, apellido, documento, direccion)


class BuscarProductosTool(BaseTool):
    name: str = "buscar_productos"
    description: str = ("Busca productos por nombre; tolera mayusculas, tildes, plurales y nombres "
                        "parciales, y puede devolver varias coincidencias con precio y stock.")

    def _run(self, nombre: str) -> str:
        return _buscar_productos(nombre)


class VerificarStockTool(BaseTool):
    name: str = "verificar_stock"
    description: str = "Verifica si hay suficiente stock de un producto para una cantidad dada."

    def _run(self, nombre_producto: str, cantidad: int) -> str:
        return _verificar_stock(nombre_producto, cantidad)


class CrearPedidoTool(BaseTool):
    name: str = "crear_pedido"
    description: str = ("Crea un pedido en la base de datos. 'productos' es una lista de "
                        "objetos con 'nombre_producto' y 'cantidad'.")

    def _run(self, telefono_cliente: str, productos: list,
             direccion_entrega: str = "", notas: str = "") -> str:
        return _crear_pedido(telefono_cliente, productos, direccion_entrega, notas)


class ConsultarPedidosTool(BaseTool):
    name: str = "consultar_pedidos"
    description: str = "Consulta los pedidos recientes de un cliente y su estado."

    def _run(self, telefono: str) -> str:
        return _consultar_pedidos(telefono)



class AgregarAlCarritoTool(BaseTool):
    name: str = "agregar_al_carrito"
    description: str = ("Agrega un producto y cantidad al carrito compartido del cliente. "
                        "Usala SIEMPRE que el cliente pida un producto. El carrito queda "
                        "disponible para los demas agentes.")

    def _run(self, telefono: str, nombre_producto: str, cantidad: int) -> str:
        return memoria.agregar_item(telefono, nombre_producto, cantidad)


class VerCarritoTool(BaseTool):
    name: str = "ver_carrito"
    description: str = "Muestra el carrito actual del cliente (compartido entre agentes)."

    def _run(self, telefono: str) -> str:
        return memoria.ver_carrito(telefono)


t_buscar_cliente = BuscarClienteTool()
t_registrar_cliente = RegistrarClienteTool()
t_buscar_productos = BuscarProductosTool()
t_verificar_stock = VerificarStockTool()
t_crear_pedido = CrearPedidoTool()
t_consultar_pedidos = ConsultarPedidosTool()
t_agregar_carrito = AgregarAlCarritoTool()
t_ver_carrito = VerCarritoTool()





agente_atencion = Agent(
    role="Agente de atencion al cliente de Palmita Express",
    goal="Saludar, verificar si el cliente existe y registrar a los nuevos pidiendo todos sus datos, o atenderlos como invitado.",
    backstory="Reconoces al cliente con buscar_cliente. Si NO existe, pidele uno a uno nombre, apellido, cedula y direccion, y luego registralo con registrar_cliente. Si no quiere dar sus datos, ofrecele continuar como invitado (registrar_cliente con documento='invitado'). Si ya existe, saludalo por su nombre.",
    tools=[t_buscar_cliente, t_registrar_cliente],
    llm=_llm,
    allow_delegation=True,
    verbose=False,
)

agente_inventario = Agent(
    role="Agente de inventario de Palmita Express",
    goal="Informar disponibilidad y SIEMPRE agregar al carrito los productos que el cliente pida.",
    backstory="Conoces el catalogo al detalle. No exijas el nombre exacto: la busqueda ignora mayusculas, tildes y plurales. Si hay varias coincidencias (por ejemplo 'chorizos'), muestralas TODAS como opciones con su precio. Cuando el cliente elige un producto con cantidad, verificas stock y lo agregas al carrito con agregar_al_carrito. Si no hay ninguna coincidencia, ofreces alternativas similares.",
    tools=[t_buscar_productos, t_verificar_stock, t_agregar_carrito],
    llm=_llm,
    allow_delegation=True,
    verbose=False,
)

agente_pedidos = Agent(
    role="Agente de pedidos de Palmita Express",
    goal="Llenar el carrito con lo que pida el cliente y crear el pedido tras confirmar.",
    backstory="Gestionas la venta. Si el cliente menciona productos con cantidades, OBLIGATORIAMENTE los agregas al carrito con agregar_al_carrito. Luego revisas el carrito con ver_carrito, muestras un resumen y, cuando el cliente confirma, creas el pedido con crear_pedido.",
    tools=[t_agregar_carrito, t_ver_carrito, t_verificar_stock, t_crear_pedido, t_consultar_pedidos],
    llm=_llm,
    allow_delegation=True,
    verbose=False,
)


# --------------------------------------------------------------------------- #
# Ejecucion: cada funcion corre un agente sobre el mensaje del cliente.
# --------------------------------------------------------------------------- #
def _ejecutar(agente, mensaje, telefono, contexto=""):
    descripcion = (
        'El cliente (telefono ' + str(telefono) + ') escribio: "' + str(mensaje) + '".\n'
        + (("Contexto reciente de la conversacion:\n" + contexto + "\n") if contexto else "")
        + "Reglas: si el cliente menciona uno o mas productos con cantidad, usa "
        + "agregar_al_carrito por cada uno (telefono=" + str(telefono) + "). "
        + "Para confirmar un pedido, primero usa ver_carrito. "
        + "Atiende usando tus herramientas. Habla en espanol, amable y breve."
    )
    tarea = Task(
        description=descripcion,
        expected_output="La respuesta final para enviar al cliente por WhatsApp.",
        agent=agente,
    )
    crew = Crew(agents=[agente], tasks=[tarea], verbose=False)
    return str(crew.kickoff()).strip()


def responder_atencion(mensaje, telefono, contexto=""):
    return _ejecutar(agente_atencion, mensaje, telefono, contexto)


def responder_inventario(mensaje, telefono, contexto=""):
    return _ejecutar(agente_inventario, mensaje, telefono, contexto)


def responder_pedidos(mensaje, telefono, contexto=""):
    return _ejecutar(agente_pedidos, mensaje, telefono, contexto)
