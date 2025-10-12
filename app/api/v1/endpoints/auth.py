# app/api/v1/endpoints/auth.py
from fastapi import APIRouter, HTTPException, status, Depends, Response, Request
from fastapi.security import OAuth2PasswordRequestForm

from app.schemas.auth import Token, UserDataWithRoles
from app.core.auth import (
    authenticate_user,
    create_access_token,
    create_refresh_token,
    get_current_user,
    get_current_user_from_refresh,
)
from app.core.config import settings
from app.core.logging_config import get_logger
from app.services.usuario_service import UsuarioService

router = APIRouter()
logger = get_logger(__name__)

@router.post(
    "/login/",  # ✅ CAMBIO: Agregado /
    response_model=Token,
    summary="Autenticar usuario y obtener token",
    description="Verifica credenciales, genera access y refresh token (cookie HttpOnly) y retorna datos de usuario."
)
async def login(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends()
):
    usuario_service = UsuarioService()
    try:
        # 1) Autenticación
        user_base_data = await authenticate_user(form_data.username, form_data.password)

        # 2) Roles
        user_id = user_base_data.get('usuario_id')
        user_role_names = await usuario_service.get_user_role_names(user_id=user_id)

        user_full_data = {**user_base_data, "roles": user_role_names}

        # 3) Tokens
        access_token = create_access_token(data={"sub": form_data.username})
        refresh_token = create_refresh_token(data={"sub": form_data.username})

        # 4) Setear refresh en cookie HttpOnly con configuración dinámica según entorno
        response.set_cookie(
            key=settings.REFRESH_COOKIE_NAME,
            value=refresh_token,
            httponly=True,
            secure=settings.COOKIE_SECURE,      # False en dev, True en prod
            samesite=settings.COOKIE_SAMESITE,  # "none" en dev, "lax" en prod
            max_age=settings.REFRESH_COOKIE_MAX_AGE,
            path="/",
        )

        logger.info(f"Usuario {form_data.username} autenticado exitosamente")

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user_data": user_full_data
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error inesperado en /login/ para usuario {form_data.username}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ocurrió un error inesperado durante el proceso de login."
        )

@router.get(
    "/me/",  # ✅ CAMBIO: Agregado /
    response_model=UserDataWithRoles,
    summary="Obtener usuario actual",
    description="Retorna datos del usuario autenticado, incluyendo roles. Requiere Access Token válido."
)
async def get_me(current_user: dict = Depends(get_current_user)):
    try:
        usuario_service = UsuarioService()
        user_id = current_user.get('usuario_id')
        user_role_names = await usuario_service.get_user_role_names(user_id=user_id)
        user_full_data = {**current_user, "roles": user_role_names}
        return user_full_data
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error en /me/: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error obteniendo datos del usuario"
        )

@router.post(
    "/refresh/",  # ✅ CAMBIO: Agregado /
    response_model=Token,
    summary="Refrescar Access Token",
    description="Genera un nuevo access token usando el refresh token en cookie HttpOnly. Rota el refresh."
)
async def refresh_access_token(
    request: Request,  # ← AGREGAR ESTO
    response: Response,
    current_user: dict = Depends(get_current_user_from_refresh)
):
# ✅ AGREGAR ESTOS LOGS AL INICIO (ANTES DEL TRY)
    cookies = request.cookies
    logger.info(f"🍪 [REFRESH] Cookies recibidas: {list(cookies.keys())}")
    logger.info(f"🍪 [REFRESH] refresh_token presente: {'refresh_token' in cookies}")
    if 'refresh_token' in cookies:
        token_preview = cookies['refresh_token'][:30] if len(cookies['refresh_token']) > 30 else cookies['refresh_token']
        logger.info(f"🍪 [REFRESH] refresh_token value (primeros 30 chars): {token_preview}...")
    else:
        logger.warning(f"⚠️ [REFRESH] NO SE RECIBIÓ COOKIE refresh_token")
    
    logger.info(f"🔍 [REFRESH] Headers recibidos: {dict(request.headers)}")

    try:
        username = current_user.get("nombre_usuario")
        if not username:
            raise HTTPException(status_code=401, detail="Usuario no válido")

        # Access
        new_access_token = create_access_token(data={"sub": username})

        # Rotar refresh con configuración dinámica según entorno
        new_refresh_token = create_refresh_token(data={"sub": username})
        response.set_cookie(
            key=settings.REFRESH_COOKIE_NAME,
            value=new_refresh_token,
            httponly=True,
            secure=settings.COOKIE_SECURE,      # False en dev, True en prod
            samesite=settings.COOKIE_SAMESITE,  # "none" en dev, "lax" en prod
            max_age=settings.REFRESH_COOKIE_MAX_AGE,
            path="/",
        )
        logger.info(f"✅ [REFRESH] Token refrescado exitosamente para usuario: {username}")
        return {
            "access_token": new_access_token,
            "token_type": "bearer",
            "user_data": None  # opcionalmente podrías devolver datos de usuario
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error en /refresh/: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al refrescar el token"
        )

@router.post(
    "/logout/",  # ✅ CAMBIO: Agregado /
    summary="Cerrar sesión",
    description="Elimina el refresh token de la cookie."
)
async def logout(response: Response):
    response.delete_cookie(
        key=settings.REFRESH_COOKIE_NAME,
        path="/",
        samesite=settings.COOKIE_SAMESITE  # Importante: usar mismo samesite para borrar correctamente
    )
    logger.info("Usuario cerró sesión exitosamente")
    return {"message": "Sesión cerrada exitosamente"}