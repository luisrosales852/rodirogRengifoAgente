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

        # Use only the first matching client
        cliente = clientes_response.data[0]
        cliente_id = cliente["id"]
        cliente_nombre = cliente["nombre"]

        # Fetch all policies for this client with the specified columns
        polizas_response = supabase.table("polizas").select(
            "Numero_de_poliza, vigencia_inicio, vigencia_fin, tipoSeguro, "
            "sumaAsegurada, prima_anual, primaNeta, descripcion, estado"
        ).eq("id_cliente", cliente_id).execute()

        polizas = polizas_response.data

        # Format client section
        result = f"\n{'='*60}\n"
        result += f"CLIENTE: {cliente_nombre} (ID: {cliente_id})\n"
        result += f"{'='*60}\n"

        if not polizas:
            result += "  No tiene pólizas registradas.\n"
        else:
            result += f"  Total de pólizas: {len(polizas)}\n\n"

            for i, poliza in enumerate(polizas, 1):
                result += f"  Póliza {i} \n"
                result += f"  Número de Póliza: {poliza.get('Numero_de_poliza', 'N/A')}\n"
                result += f"  Tipo de Seguro: {poliza.get('tipoSeguro', 'N/A')}\n"
                result += f"  Estado: {poliza.get('estado', 'N/A')}\n"
                result += f"  Vigencia: {poliza.get('vigencia_inicio', 'N/A')} a {poliza.get('vigencia_fin', 'N/A')}\n"
                result += f"  Suma Asegurada: ${poliza.get('sumaAsegurada', 'N/A'):,}\n" if poliza.get('sumaAsegurada') else f"  Suma Asegurada: N/A\n"
                result += f"  Prima Anual: ${poliza.get('prima_anual', 'N/A'):,}\n" if poliza.get('prima_anual') else f"  Prima Anual: N/A\n"
                result += f"  Prima Neta: ${poliza.get('primaNeta', 'N/A'):,}\n" if poliza.get('primaNeta') else f"  Prima Neta: N/A\n"
                result += f"  Descripción: {poliza.get('descripcion', 'N/A')}\n\n"

        return result

    except Exception as e:
        return f"Error al consultar la base de datos: {str(e)}"


class ClientePasswordInput(BaseModel):
    """Input schema for checking client password."""
    nombre_cliente: str = Field(
        description="The name of the client (nombre) to search for in the database."
    )


@tool(args_schema=ClientePasswordInput)
def get_cliente_password(nombre_cliente: str) -> str:
    """
    Retrieves the password for a given client from the database.

    This tool searches for a client by name in the Clientes table and returns
    their password from the Contraseña column.

    Use this tool when you need to:
    - Check a client's password
    - Verify client credentials

    Returns the client's password, or 'password' if none is set.
    """
    try:
        supabase = get_supabase_client()

        # Search for the client by name (case-insensitive)
        clientes_response = supabase.table("Clientes").select("nombre, Contraseña").ilike(
            "nombre", f"%{nombre_cliente}%"
        ).execute()

        if not clientes_response.data:
            return f"No se encontró ningún cliente con el nombre '{nombre_cliente}'."

        # Use only the first matching client
        cliente = clientes_response.data[0]
        password = cliente.get("Contraseña")

        # Return password if exists, otherwise return default
        if password is not None:
            return password
        else:
            return "password"

    except Exception as e:
        return f"Error al consultar la base de datos: {str(e)}"


# List of tools to export for use with LangChain agent
supabase_tools = [get_cliente_polizas, get_cliente_password]


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
supabase_tools_extended = [get_cliente_polizas, get_cliente_password, list_all_clientes]


CHAT_HISTORY_TABLE = "chat_memory"
MAX_HISTORY_MESSAGES = 20  


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
