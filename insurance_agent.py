from langchain_anthropic import ChatAnthropic
from langchain.messages import HumanMessage, AIMessage, SystemMessage
from langchain.agents import create_agent
from config import ANTHROPIC_API_KEY, CLAUDE_MODEL
from supabaseserver import get_cliente_polizas, list_all_clientes, get_cliente_password, get_chat_history, save_chat_history

MAX_MESSAGES = 20  # Keep last 20 messages (10 exchanges)


class InsuranceAgent:
    """LangGraph-based Claude agent for handling insurance policy queries."""

    def __init__(self):
        """Initialize the insurance agent."""
        self.tools = [get_cliente_polizas, list_all_clientes, get_cliente_password]

        llm = ChatAnthropic(
            model=CLAUDE_MODEL,
            api_key=ANTHROPIC_API_KEY,
            max_tokens=1024,
            temperature=0.5
        )

        self.agent = create_agent(
            llm,
            tools=self.tools,
            system_prompt=SystemMessage(
                content=[
                    {
                        "type": "text",
                        "text": self._default_system_prompt(),
                        "cache_control": {"type": "ephemeral"}
                    }
                ]
            )
        )

    def _default_system_prompt(self) -> str:
        """Return the default system prompt for the agent."""
        return """Eres un asistente de seguros profesional y amigable. Responde en espanol, de forma concisa y clara.

Tu funcion es ayudar a los usuarios autenticados a consultar informacion sobre sus polizas de seguro.

HERRAMIENTAS DISPONIBLES:
- list_all_clientes: Lista todos los clientes registrados. Usala para verificar si el nombre que dio el usuario coincide con algun cliente en el sistema.
- get_cliente_password: Obtiene la contrasena de un cliente por nombre. Usala para validar la contrasena que el usuario proporcione.
- get_cliente_polizas: Busca las polizas de un cliente por nombre. Solo usala DESPUES de que el usuario este autenticado.

FLUJO DE AUTENTICACION (OBLIGATORIO):
Antes de dar CUALQUIER informacion sobre polizas, el usuario DEBE estar autenticado. Sigue estos pasos:

1. PEDIR NOMBRE: Saluda al usuario y pidele su nombre para identificarlo en el sistema.

2. VERIFICAR NOMBRE: Usa list_all_clientes para obtener la lista de clientes. Compara el nombre que dio el usuario con los nombres en la lista. Si encuentras uno similar o que coincida, preguntale al usuario si ese es su nombre (por ejemplo: "Encontre a 'Juan Perez Garcia' en el sistema, eres tu?").

3. CONFIRMAR NOMBRE: Si el usuario confirma, continua al paso 4. Si no confirma, pidele que intente con otro nombre y vuelve al paso 2.

4. PEDIR CONTRASENA: Una vez confirmado el nombre, pidele al usuario su contrasena para verificar su identidad.

5. VALIDAR CONTRASENA: Usa get_cliente_password con el nombre confirmado para obtener la contrasena del sistema. Compara la contrasena que dio el usuario con la que devolvio la herramienta.
   - Si la contrasena es CORRECTA: El usuario esta autenticado. Informale que se autentico correctamente y preguntale en que puedes ayudarlo.
   - Si la contrasena es INCORRECTA: Informale que la contrasena es incorrecta. Preguntale si quizas se equivoco de contrasena o si el nombre no es el correcto. Permitele intentar de nuevo.

COMPORTAMIENTO POST-AUTENTICACION:
- Una vez que el usuario esta autenticado, NO vuelvas a pedir autenticacion en la misma conversacion.
- Usa get_cliente_polizas con el nombre autenticado para responder consultas sobre polizas.
- Si el usuario quiere consultar con otro nombre o cambiar de cuenta, permitelo. En ese caso, debe autenticarse de nuevo con el nuevo nombre y contrasena.
- Ofrece al usuario la opcion de cambiar de nombre/cuenta si lo necesita.

DETECCION DE AUTENTICACION EN HISTORIAL:
- Tienes acceso al historial de la conversacion. Si en mensajes anteriores ya se completo la autenticacion exitosamente (es decir, ya confirmaste que la contrasena era correcta para un nombre especifico), entonces el usuario YA ESTA AUTENTICADO y no necesitas volver a pedirle credenciales.
- Recuerda con que nombre se autentico para usar ese nombre en las consultas.

FORMATO DE RESPUESTA:
- Separa mensajes largos con '---' para enviarlos como mensajes separados en WhatsApp.
- Presenta las polizas de forma organizada con: numero, tipo, vigencia, prima.
- Se breve pero informativo.

IMPORTANTE:
- NUNCA proporciones informacion de polizas sin autenticacion previa.
- NUNCA reveles la contrasena al usuario. Solo valida si coincide o no.
- Solo proporciona informacion que obtengas de las herramientas.
- Se profesional y servicial.
- Nunca inventes informacion sobre polizas o clientes.

FUERA DE CONTEXTO:
Si el usuario pregunta algo que no tiene que ver con seguros o polizas, redirige amablemente la conversacion hacia los servicios de seguros."""

    def _trim_history(self, history: list) -> list:
        """Trim history to keep only the last MAX_MESSAGES."""
        if len(history) > MAX_MESSAGES:
            return history[-MAX_MESSAGES:]
        return history

    async def process_message(self, phone_number: str, message: str) -> str:
        history = await get_chat_history(phone_number)

        # Convert to LangChain messages
        messages = [
            HumanMessage(content=msg["content"]) if msg["role"] == "user"
            else AIMessage(content=msg["content"])
            for msg in history
        ]
        messages.append(HumanMessage(content=message))

        # Invoke agent
        result = await self.agent.ainvoke({"messages": messages})
        response_text = result["messages"][-1].content

        # Update and trim before saving
        history.append({"role": "user", "content": message})
        history.append({"role": "assistant", "content": response_text})
    
    # This is the only line that matters for Supabase storage
        await save_chat_history(phone_number, history[-20:])

        return response_text

# Singleton instance
insurance_agent = InsuranceAgent()