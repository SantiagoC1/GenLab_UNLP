from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.enums import Rol
from app.core.errors import Forbidden, InvalidSession, MustChangePassword
from app.database import supabase_admin
from app.models import user as user_model

_bearer = HTTPBearer(auto_error=False)


def get_session_user(credentials: HTTPAuthorizationCredentials | None = Depends(_bearer)):
    
    """Devuelve el usuario de la sesión, aunque todavía tenga que cambiar la contraseña inicial.

    Solo lo usa el endpoint de cambio de contraseña. Para todo lo demás, `get_current_user`.
    """
    
    if credentials is None:
        raise InvalidSession("Sesión inválida o vencida.")
    try:
        response = supabase_admin.auth.get_user(credentials.credentials)
        
    except Exception:
        raise InvalidSession("Sesión inválida o vencida.") from None
    
    user = user_model.find_by_id(response.user.id) if response and response.user else None
    
    if user is None or user["blocked"]:
        
        raise InvalidSession("Sesión inválida o vencida.")
    
    return user


def get_current_user(user: dict = Depends(get_session_user)):
    
    """Devuelve el usuario de la sesión. Si tiene la contraseña inicial, no lo deja seguir."""
    
    if user["must_change_password"]:
        raise MustChangePassword("Tenés que cambiar la contraseña antes de continuar.")
    return user


def require_role(*roles: Rol):
    
    """
    Devuelve una dependencia que solo deja pasar a los usuarios con alguno de esos roles.

    Uso: usuario = Depends(require_role(Rol.MEDICO_TRATANTE))
    """
    
    allowed = [rol.value for rol in roles]

    def check(user: dict = Depends(get_current_user)):
        
        if user["role"] not in allowed:
            raise Forbidden("No tenés permiso para esta acción.")
        return user

    return check