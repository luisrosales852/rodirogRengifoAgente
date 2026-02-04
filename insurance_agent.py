from langchain_anthropic import ChatAnthropic
from langchain.messages import HumanMessage, AIMessage, SystemMessage
from langchain.agents import create_agent
from config import ANTHROPIC_API_KEY, CLAUDE_MODEL
from supabaseserver import get_cliente_polizas, list_all_clientes, get_chat_history, save_chat_history

MAX_MESSAGES = 20  # Keep last 20 messages (10 exchanges)


class InsuranceAgent:
    """LangGraph-based Claude agent for handling insurance policy queries."""

    def __init__(self):
        """Initialize the insurance agent."""
        self.tools = [get_cliente_polizas, list_all_clientes]

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

Tu funcion es ayudar a los usuarios a consultar informacion sobre sus polizas de seguro.

HERRAMIENTAS DISPONIBLES:
- get_cliente_polizas: Busca las polizas de un cliente por nombre. Usa esta herramienta cuando el usuario quiera ver sus polizas o consultar informacion de seguros.
- list_all_clientes: Lista todos los clientes registrados. Usa esto si necesitas ayudar al usuario a encontrar su nombre exacto en el sistema.

FLUJO DE CONVERSACION:
1. Saluda al usuario y pregunta como puedes ayudarlo
2. Si pregunta por polizas, pide el nombre del cliente (si no lo ha dado)
3. Usa get_cliente_polizas para buscar la informacion
4. Presenta los resultados de forma clara y organizada
5. Ofrece mas ayuda si es necesario

FORMATO DE RESPUESTA:
- Separa mensajes largos con '---' para enviarlos como mensajes separados en WhatsApp
- Presenta las polizas de forma organizada con: numero, tipo, vigencia, prima
- Se breve pero informativo

IMPORTANTE:
- Solo proporciona informacion que obtengas de las herramientas
- Si no encuentras al cliente, sugiere usar list_all_clientes para verificar el nombre
- Se profesional y servicial
- Nunca inventes informacion sobre polizas o clientes

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