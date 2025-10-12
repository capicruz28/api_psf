# app/schemas/auth.py
from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field

# Datos base del usuario
class UserDataBase(BaseModel):
    usuario_id: int
    nombre_usuario: str
    correo: EmailStr
    nombre: Optional[str] = None
    apellido: Optional[str] = None
    es_activo: bool

# Usuario con roles
class UserDataWithRoles(UserDataBase):
    roles: List[str] = Field(default_factory=list)

# Entrada de login (si la usas fuera de OAuth2PasswordRequestForm)
class LoginData(BaseModel):
    username: str
    password: str

# Respuesta del login/refresh
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_data: Optional[UserDataWithRoles] = None  # en /refresh puede ser None

# Payload del JWT
class TokenPayload(BaseModel):
    sub: Optional[str] = None  # estándar: subject (username)
    exp: Optional[int] = None
    iat: Optional[int] = None
    type: Optional[str] = None  # 'access' o 'refresh'