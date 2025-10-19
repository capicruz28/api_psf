# app/core/auth.py
from datetime import datetime, timedelta
from typing import Optional, Dict
import logging

from fastapi import Depends, HTTPException, status, Cookie
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

from app.core.config import settings
from app.core.security import verify_password
from app.db.queries import execute_auth_query
from app.schemas.auth import TokenPayload

logger = logging.getLogger(__name__)

# Swagger/OpenAPI: flujo password con tokenUrl en /api/v1
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login/")


def create_access_token(data: dict) -> str:
    """
    Crea un token JWT de acceso con iat, exp y type='access'
    """
    to_encode = data.copy()
    now = datetime.utcnow()
    expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({
        "exp": expire,
        "iat": now,
        "type": "access",
    })
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(data: dict) -> str:
    """
    Crea un token JWT de refresh con iat, exp y type='refresh'
    """
    to_encode = data.copy()
    now = datetime.utcnow()
    expire = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({
        "exp": expire,
        "iat": now,
        "type": "refresh",
    })
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_refresh_token(token: str) -> dict:
    """
    Decodifica y valida un refresh token (type='refresh')
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("type") != "refresh":
            raise JWTError("Token type is not refresh")
        return payload
    except JWTError as e:
        logger.error(f"Error decodificando refresh token: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def authenticate_user(username: str, password: str) -> Dict:
    """
    Autentica un usuario y retorna sus datos (sin contraseña) si las credenciales son correctas
    """
    try:
        query = """
            SELECT usuario_id, nombre_usuario, correo, contrasena,
                   nombre, apellido, es_activo
            FROM usuario
            WHERE nombre_usuario = ? AND es_eliminado = 0
        """
        user = execute_auth_query(query, (username,))

        if not user or not verify_password(password, user['contrasena']):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciales incorrectas"
            )

        if not user['es_activo']:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Usuario inactivo"
            )

        # Actualizar fecha último acceso
        update_query = """
            UPDATE usuario
            SET fecha_ultimo_acceso = GETDATE()
            WHERE usuario_id = ?
        """
        execute_auth_query(update_query, (user['usuario_id'],))

        # Eliminar la contraseña del resultado
        user.pop('contrasena', None)
        return user

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en autenticación: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error en el proceso de autenticación"
        )


async def get_current_user(token: str = Depends(oauth2_scheme)) -> Dict:
    """
    Obtiene el usuario actual basado en el access token (Bearer).
    - Valida algoritmo, firma y expiración
    - Requiere type='access'
    - Usa claim estándar 'sub' como nombre de usuario
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        token_data = TokenPayload(**payload)

        if not token_data.sub or token_data.type != "access":
            raise credentials_exception

        username = token_data.sub

    except JWTError as e:
        logger.error(f"Error decodificando token: {str(e)}")
        raise credentials_exception
    except Exception as e:
        logger.error(f"Error procesando payload del token: {str(e)}")
        raise credentials_exception

    query = """
        SELECT usuario_id, nombre_usuario, correo, nombre, apellido, es_activo
        FROM usuario
        WHERE nombre_usuario = ? AND es_eliminado = 0
    """
    user = execute_auth_query(query, (username,))

    if not user:
        raise credentials_exception

    if not user['es_activo']:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario inactivo"
        )

    return user


async def get_current_user_from_refresh(
    refresh_token: Optional[str] = Cookie(None, alias=settings.REFRESH_COOKIE_NAME)
) -> Dict:
    """
    Obtiene el usuario actual validando el refresh token de la cookie
    """
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No refresh token provided"
        )

    try:
        payload = decode_refresh_token(refresh_token)
        token_data = TokenPayload(**payload)

        if not token_data.sub:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )

        username = token_data.sub

        query = """
            SELECT usuario_id, nombre_usuario, correo, nombre, apellido, es_activo
            FROM usuario
            WHERE nombre_usuario = ? AND es_eliminado = 0
        """
        user = execute_auth_query(query, (username,))

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Usuario no encontrado"
            )

        if not user['es_activo']:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Usuario inactivo"
            )

        return user

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validando refresh token: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )