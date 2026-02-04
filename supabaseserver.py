import os
from typing import Optional
from supabase import create_client, Client
from langchain_core.tools import tool
from pydantic import BaseModel, Field


# Initialize Supabase client
def get_supabase_client() -> Client:
    """Create and return a Supabase client."""
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")

    if not url or not key:
        raise ValueError(
            "SUPABASE_URL and SUPABASE_KEY environment variables must be set"
        )

    return create_client(url, key)


class ClientePoliciesInput(BaseModel):
    """Input schema for fetching client policies."""
    nombre_cliente: str = Field(
        description="The name of the client (nombre) to search for in the database. "
                    "Can be a partial name for fuzzy matching."
    )


@tool(args_schema=ClientePoliciesInput)
def get_cliente_polizas(nombre_cliente: str) -> str:
    """
    Fetches all insurance policies (polizas) for a given client from the database.

    This tool searches for a client by name in the Clientes table, then retrieves
    all their associated policies from the polizas table with complete details.

    Use this tool when you need to:
    - Look up a client's insurance policies
    - Check policy details like coverage, premiums, validity dates
    - Get an overview of all policies a client has

    Returns all relevant policy information including:
    - Policy number (Numero_de_poliza)
    - Validity period (vigencia_inicio, vigencia_fin)
    - Insurance type (tipoSeguro)
    - Insured sum (sumaAsegurada)
    - Annual premium (prima_anual)
    - Net premium (primaNeta)
    - Description (descripcion)
    - Status (estado)
    """
    try:
        supabase = get_supabase_client()

        # First, find the client(s) matching the name (case-insensitive search)
        clientes_response = supabase.table("Clientes").select("id, nombre").ilike(
            "nombre", f"%{nombre_cliente}%"
        ).execute()

        if not clientes_response.data:
            return f"No se encontró ningún cliente con el nombre '{nombre_cliente}'."

        # Collect all matching client IDs
        clientes = clientes_response.data
        client_ids = [cliente["id"] for cliente in clientes]

        # Build result string with client info and their policies
        result_parts = []

        for cliente in clientes:
            cliente_id = cliente["id"]
            cliente_nombre = cliente["nombre"]

            # Fetch all policies for this client with the specified columns
            polizas_response = supabase.table("polizas").select(
                "Numero_de_poliza, vigencia_inicio, vigencia_fin, tipoSeguro, "
                "sumaAsegurada, prima_anual, primaNeta, descripcion, estado"
            ).eq("id_cliente", cliente_id).execute()

            polizas = polizas_response.data

            # Format client section
            client_section = f"\n{'='*60}\n"
            client_section += f"CLIENTE: {cliente_nombre} (ID: {cliente_id})\n"
            client_section += f"{'='*60}\n"

            if not polizas:
                client_section += "  No tiene pólizas registradas.\n"
            else:
                client_section += f"  Total de pólizas: {len(polizas)}\n\n"

                for i, poliza in enumerate(polizas, 1):
                    client_section += f"  --- Póliza {i} ---\n"
                    client_section += f"  Número de Póliza: {poliza.get('Numero_de_poliza', 'N/A')}\n"
                    client_section += f"  Tipo de Seguro: {poliza.get('tipoSeguro', 'N/A')}\n"
                    client_section += f"  Estado: {poliza.get('estado', 'N/A')}\n"
                    client_section += f"  Vigencia: {poliza.get('vigencia_inicio', 'N/A')} a {poliza.get('vigencia_fin', 'N/A')}\n"
                    client_section += f"  Suma Asegurada: ${poliza.get('sumaAsegurada', 'N/A'):,}\n" if poliza.get('sumaAsegurada') else f"  Suma Asegurada: N/A\n"
                    client_section += f"  Prima Anual: ${poliza.get('prima_anual', 'N/A'):,}\n" if poliza.get('prima_anual') else f"  Prima Anual: N/A\n"
                    client_section += f"  Prima Neta: ${poliza.get('primaNeta', 'N/A'):,}\n" if poliza.get('primaNeta') else f"  Prima Neta: N/A\n"
                    client_section += f"  Descripción: {poliza.get('descripcion', 'N/A')}\n\n"

            result_parts.append(client_section)

        return "".join(result_parts)

    except Exception as e:
        return f"Error al consultar la base de datos: {str(e)}"


# List of tools to export for use with LangChain agent
supabase_tools = [get_cliente_polizas]


# Optional: Function to get all clients (useful for listing)
@tool
def list_all_clientes() -> str:
    """
    Lists all clients in the database.

    Use this tool when you need to:
    - See all available clients
    - Help the user find the correct client name
    - Get an overview of the client database
    """
    try:
        supabase = get_supabase_client()

        response = supabase.table("Clientes").select("id, nombre").execute()

        if not response.data:
            return "No hay clientes registrados en la base de datos."

        result = "LISTA DE CLIENTES:\n"
        result += "-" * 40 + "\n"

        for cliente in response.data:
            result += f"  • {cliente['nombre']} (ID: {cliente['id']})\n"

        result += f"\nTotal: {len(response.data)} clientes"

        return result

    except Exception as e:
        return f"Error al consultar la base de datos: {str(e)}"


# Extended tools list including the optional list function
supabase_tools_extended = [get_cliente_polizas, list_all_clientes]


# ============================================================================
# Chat Memory Functions
# ============================================================================

CHAT_HISTORY_TABLE = "chat_memory"
MAX_HISTORY_MESSAGES = 40  # 20 exchanges (human + AI)


async def get_chat_history(phone_number: str) -> list:
    """
    Get chat history for a phone number from Supabase.

    Args:
        phone_number: The user's phone number

    Returns:
        list: List of message dicts with 'role' and 'content' keys
    """
    try:
        client = get_supabase_client()

        response = client.table(CHAT_HISTORY_TABLE).select("history_json").eq("phone_number", phone_number).execute()

        if response.data and len(response.data) > 0:
            history = response.data[0].get("history_json", [])
            return history
        else:
            return []

    except Exception as e:
        print(f"Error loading chat history: {e}")
        return []


async def save_chat_history(phone_number: str, history: list) -> bool:
    """
    Save chat history for a phone number to Supabase (upsert).
    Creates a new record if phone_number doesn't exist.

    Args:
        phone_number: The user's phone number
        history: List of message dicts with 'role' and 'content' keys

    Returns:
        bool: True if saved successfully, False otherwise
    """
    try:
        client = get_supabase_client()

        # Trim history to max messages
        if len(history) > MAX_HISTORY_MESSAGES:
            history = history[-MAX_HISTORY_MESSAGES:]

        # Prepare the data for upsert
        upsert_data = {
            "phone_number": phone_number,
            "history_json": history,
            "updated_at": "now()"
        }

        # Upsert the history (insert or update)
        response = client.table(CHAT_HISTORY_TABLE).upsert(
            upsert_data,
            on_conflict="phone_number"
        ).execute()

        if response.data:
            return True
        else:
            return False

    except Exception as e:
        print(f"Error saving chat history for {phone_number}: {e}")
        return False
