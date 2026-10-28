from fastapi import APIRouter, Depends
 
from app.core.enums import Rol
from app.core.errors import BusinessRuleError
from app.core.security import get_session_user, require_role
from app.modules.acceso import service
from app.modules.acceso.catalogs import ADMIN_CREATABLE_ROLES, SELF_SIGNUP_ROLES
from app.modules.acceso.schemas import (
    ChangePasswordData,
    CreateUserData,
    LoginData,
    RegisterData,
    VerifyCodeData,
)
from app.modules.acceso.validate import validate_password_change, validate_user_data
 
router = APIRouter(prefix="/auth", tags=["auth"])
 
ADMIN_ONLY = require_role(Rol.ADMINISTRADOR_GENERAL)
 
 
def _raise_if_invalid(errors: list[str]) -> None:
    """
    Si hay errores de validación, responde 422 con todos los mensajes juntos.
    """
    if errors:
        raise BusinessRuleError(" ".join(errors), status_code=422)
 
 
def _session_response(token: str, user: dict) -> dict:
    return {
        "access_token": token,
        "token_type": "bearer",
        "role": user["role"],
        "must_change_password": user["must_change_password"],
    }
 
 
@router.get("/catalogs")
def get_catalogs():
    """Especialidades y provincias, para los formularios."""
    return service.get_catalogs()
 
 
@router.post("/register", status_code=201)
def register(data: RegisterData):
    """Escenario 1: autoalta."""
    data = data.model_dump()
    _raise_if_invalid(validate_user_data(data, SELF_SIGNUP_ROLES, with_password=True))
    token, user = service.register_user(data)
    return _session_response(token, user)
 
 
@router.post("/login")
def login(data: LoginData):
    """Escenario 4, paso 1: contraseña. Envía el código por mail."""
    if not data.email or not data.password:
        raise BusinessRuleError("Completá el mail y la contraseña.", status_code=422)
    service.login_user(data.email, data.password)
    return {"state": "code_sent", "session": None}
 
 
@router.post("/verify-code")
def verify_code(data: VerifyCodeData):
    """Escenario 4, paso 2: código recibido por mail."""
    if not data.email or not data.code:
        raise BusinessRuleError("Completá el mail y el código.", status_code=422)
    token, user = service.verify_login_code(data.email, data.code)
    return _session_response(token, user)
 
 
@router.post("/change-password")
def change_password(data: ChangePasswordData, user: dict = Depends(get_session_user)):
    """Escenario 3: cambio de la contraseña. Funciona aunque falte cambiar la inicial."""
    data = data.model_dump()
    _raise_if_invalid(validate_password_change(data))
    service.change_password(user, data["current_password"], data["new_password"])
    return {"state": "password_changed"}
 
 
@router.get("/users")
def list_users(admin_user: dict = Depends(ADMIN_ONLY)):
    """Escenario 2: listado de usuarios (solo el administrador general)."""
    return service.list_users()
 
 
@router.post("/users", status_code=201)
def create_user(data: CreateUserData, admin_user: dict = Depends(ADMIN_ONLY)):
    """Escenario 2: alta de un usuario por el administrador general."""
    data = data.model_dump()
    _raise_if_invalid(validate_user_data(data, ADMIN_CREATABLE_ROLES, with_password=False))
    return service.create_user_as_admin(data, admin_user)