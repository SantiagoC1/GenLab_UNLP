import os
from pathlib import Path

from dotenv import load_dotenv
from supabase import Client, create_client

# El .env está en la raíz del repo (en Docker las variables llegan por docker-compose)
BASE_DIR = Path(__file__).resolve().parent.parent.parent

load_dotenv(BASE_DIR / ".env")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")


supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
supabase_admin: Client | None = (
    create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY) if SUPABASE_SERVICE_ROLE_KEY else None
)


def new_auth_client() -> Client:
    """Devuelve un cliente nuevo (anon key) para verificar contraseñas y códigos.

    Iniciar sesión guarda el token en el cliente: si fuera el `supabase` compartido,
    las consultas siguientes de todos los usuarios saldrían con ese token.
    """
    return create_client(SUPABASE_URL, SUPABASE_KEY)
