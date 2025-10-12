# app/api/v1/endpoints/usuarios.py (ACTUALIZADO)

from fastapi import APIRouter, HTTPException, Depends, status, Query
from typing import List, Optional, Dict, Any

# Importar Schemas
from app.schemas.usuario import (
    UsuarioCreate,
    UsuarioUpdate,
    UsuarioRead,
    UsuarioReadWithRoles,
    PaginatedUsuarioResponse # <--- AÑADIR IMPORTACIÓN
)
from app.schemas.rol import RolRead
from app.schemas.usuario_rol import UsuarioRolRead

# Importar Servicios
from app.services.usuario_service import UsuarioService

# Importar Excepciones personalizadas
from app.core.exceptions import ServiceError, ValidationError

# --- Importar Dependencias de Autorización ---
# Asumiendo que get_current_active_user devuelve un objeto/dict con info del usuario
# y RoleChecker es una clase/función que verifica roles
from app.api.deps import get_current_active_user, RoleChecker

# Logging
from app.core.logging_config import get_logger
logger = get_logger(__name__)

router = APIRouter()

# --- Dependencia específica para requerir rol 'admin' ---
# Asegúrate que RoleChecker funcione como esperas.
# Podría necesitar acceso al usuario actual o al servicio para verificar roles.
require_admin = RoleChecker(["Administrador"])

# --- NUEVO ENDPOINT PARA LISTAR USUARIOS PAGINADOS ---
@router.get(
    "/",  # ✅ YA TIENE /
    response_model=PaginatedUsuarioResponse,
    summary="Listar usuarios paginados",
    description="Obtiene una lista paginada de usuarios activos con sus roles. Permite búsqueda. **Requiere rol 'admin'.**",
    dependencies=[Depends(require_admin)] # Proteger con rol admin
)
async def list_usuarios(
    page: int = Query(1, ge=1, description="Número de página a mostrar"),
    limit: int = Query(10, ge=1, le=100, description="Número de usuarios por página"),
    search: Optional[str] = Query(None, min_length=1, max_length=50, description="Término de búsqueda opcional (nombre, apellido, correo, nombre_usuario)")
    # current_user: Dict[str, Any] = Depends(get_current_active_user) # Ya está en dependencies
):
    """
    Devuelve una lista paginada de usuarios no eliminados.
    - **page**: Página actual.
    - **limit**: Resultados por página.
    - **search**: Busca coincidencias en campos clave del usuario.
    """
    try:
        logger.debug(f"Endpoint list_usuarios llamado con page={page}, limit={limit}, search='{search}'")
        # Llamar al nuevo método del servicio
        paginated_data = await UsuarioService.get_usuarios_paginated(
            page=page,
            limit=limit,
            search=search
        )
        # El servicio ya devuelve un diccionario con la estructura correcta,
        # FastAPI lo validará contra PaginatedUsuarioResponse
        return paginated_data
    except ValidationError as e:
        logger.warning(f"Error de validación en list_usuarios: {e.detail}")
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except ServiceError as e:
        logger.error(f"Error de servicio en list_usuarios: {e.detail}")
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        logger.exception(f"Error inesperado en endpoint list_usuarios: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno del servidor al listar usuarios.")


# --- Endpoint para Crear Usuario ---
@router.post(
    "/",  # ✅ YA TIENE /
    response_model=UsuarioRead, # Mantenemos UsuarioRead aquí, la creación no suele devolver roles
    status_code=status.HTTP_201_CREATED,
    summary="Crear un nuevo usuario",
    description="Crea un nuevo usuario. **Requiere rol 'admin'.**",
    dependencies=[Depends(require_admin)]
)
async def crear_usuario(
    usuario_in: UsuarioCreate,
):
    # ... (código existente sin cambios) ...
    try:
        usuario_dict = usuario_in.model_dump()
        created_usuario = await UsuarioService.crear_usuario(usuario_dict)
        # Convertir el diccionario devuelto por el servicio a UsuarioRead si es necesario
        # o asegurar que el servicio devuelva un objeto compatible
        return created_usuario # Asume que el servicio devuelve dict compatible con UsuarioRead
    except ValidationError as e:
        logger.warning(f"Error de validación al crear usuario: {e.detail}")
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except ServiceError as e:
        logger.error(f"Error de servicio al crear usuario: {e.detail}")
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        logger.exception(f"Error inesperado en endpoint crear_usuario: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno del servidor al crear el usuario.")


# --- Endpoint para Obtener un Usuario por ID (con Roles) ---
@router.get(
    "/{usuario_id}/",  # ✅ CAMBIO: Agregado /
    response_model=UsuarioReadWithRoles,
    summary="Obtener un usuario por ID",
    description="Obtiene los detalles de un usuario específico, incluyendo sus roles activos. **Requiere autenticación.**",
    dependencies=[Depends(get_current_active_user)]
)
async def read_usuario(
    usuario_id: int,
):
    # ... (código existente sin cambios) ...
    try:
        usuario = await UsuarioService.obtener_usuario_por_id(usuario_id=usuario_id)
        if usuario is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Usuario con ID {usuario_id} no encontrado.")

        roles = await UsuarioService.obtener_roles_de_usuario(usuario_id=usuario_id)
        # Asegurarse que 'usuario' sea un dict compatible con UsuarioReadWithRoles
        # y 'roles' sea una lista de dicts compatibles con RolRead
        usuario_con_roles = UsuarioReadWithRoles(**usuario, roles=roles)
        return usuario_con_roles

    except ServiceError as e:
        logger.error(f"Error de servicio obteniendo usuario/roles ID {usuario_id}: {e.detail}")
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        logger.exception(f"Error inesperado en endpoint read_usuario (ID: {usuario_id}): {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno del servidor al obtener el usuario.")


# --- Endpoint para Actualizar Usuario ---
@router.put(
    "/{usuario_id}/",  # ✅ CAMBIO: Agregado /
    response_model=UsuarioRead, # Mantenemos UsuarioRead, la actualización no suele devolver roles
    summary="Actualizar un usuario",
    description="Actualiza los datos de un usuario existente. No modifica roles. **Requiere rol 'admin'.**",
    dependencies=[Depends(require_admin)]
)
async def actualizar_usuario(
    usuario_id: int,
    usuario_in: UsuarioUpdate,
):
    # ... (código existente sin cambios) ...
    try:
        update_data = usuario_in.model_dump(exclude_unset=True)
        if not update_data:
             raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se proporcionaron datos para actualizar."
            )
        updated_usuario = await UsuarioService.actualizar_usuario(usuario_id, update_data)
        return updated_usuario # Asume que el servicio devuelve dict compatible con UsuarioRead
    except ValidationError as e:
        logger.warning(f"Error de validación al actualizar usuario ID {usuario_id}: {e.detail}")
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except ServiceError as e:
        logger.error(f"Error de servicio al actualizar usuario ID {usuario_id}: {e.detail}")
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        logger.exception(f"Error inesperado en endpoint actualizar_usuario (ID: {usuario_id}): {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno del servidor al actualizar el usuario.")


# --- Endpoint para Eliminar Usuario (Lógico) ---
@router.delete(
    "/{usuario_id}/",  # ✅ CAMBIO: Agregado /
    response_model=dict,
    summary="Eliminar (lógicamente) un usuario",
    description="Marca un usuario como eliminado y lo desactiva. También desactiva sus asignaciones de roles. **Requiere rol 'admin'.**",
    dependencies=[Depends(require_admin)]
)
async def eliminar_usuario(
    usuario_id: int,
):
    # ... (código existente sin cambios) ...
    try:
        result = await UsuarioService.eliminar_usuario(usuario_id)
        return result
    except ValidationError as e:
        logger.warning(f"Error de validación al eliminar usuario ID {usuario_id}: {e.detail}")
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except ServiceError as e:
        logger.error(f"Error de servicio al eliminar usuario ID {usuario_id}: {e.detail}")
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        logger.exception(f"Error inesperado en endpoint eliminar_usuario (ID: {usuario_id}): {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno del servidor al eliminar el usuario.")


# --- Endpoints para Gestión de Roles de Usuario ---

@router.post(
    "/{usuario_id}/roles/{rol_id}/",  # ✅ CAMBIO: Agregado /
    response_model=UsuarioRolRead, # Schema para la relación usuario-rol
    status_code=status.HTTP_201_CREATED,
    summary="Asignar un rol a un usuario",
    description="Asigna un rol específico a un usuario. Si la asignación existía inactiva, la reactiva. **Requiere rol 'admin'.**",
    dependencies=[Depends(require_admin)]
)
async def assign_rol_to_usuario(
    usuario_id: int,
    rol_id: int,
):
    # ... (código existente sin cambios) ...
    try:
        assignment = await UsuarioService.asignar_rol_a_usuario(usuario_id, rol_id)
        return assignment # Asume que el servicio devuelve dict compatible con UsuarioRolRead
    except ValidationError as e:
        logger.warning(f"Error de validación asignando rol {rol_id} a usuario {usuario_id}: {e.detail}")
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except ServiceError as e:
        logger.error(f"Error de servicio asignando rol {rol_id} a usuario {usuario_id}: {e.detail}")
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        logger.exception(f"Error inesperado asignando rol {rol_id} a usuario {usuario_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno del servidor al asignar el rol.")


@router.delete(
    "/{usuario_id}/roles/{rol_id}/",  # ✅ CAMBIO: Agregado /
    response_model=UsuarioRolRead, # Schema para la relación usuario-rol
    summary="Revocar un rol de un usuario",
    description="Desactiva la asignación de un rol específico para un usuario. **Requiere rol 'admin'.**",
    dependencies=[Depends(require_admin)]
)
async def revoke_rol_from_usuario(
    usuario_id: int,
    rol_id: int,
):
    # ... (código existente sin cambios) ...
    try:
        assignment = await UsuarioService.revocar_rol_de_usuario(usuario_id, rol_id)
        return assignment # Asume que el servicio devuelve dict compatible con UsuarioRolRead
    except ValidationError as e:
        logger.warning(f"Error de validación revocando rol {rol_id} de usuario {usuario_id}: {e.detail}")
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except ServiceError as e:
        logger.error(f"Error de servicio revocando rol {rol_id} de usuario {usuario_id}: {e.detail}")
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        logger.exception(f"Error inesperado revocando rol {rol_id} de usuario {usuario_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno del servidor al revocar el rol.")


@router.get(
    "/{usuario_id}/roles/",  # ✅ CAMBIO: Agregado /
    response_model=List[RolRead],
    summary="Obtener los roles de un usuario",
    description="Devuelve una lista de todos los roles activos asignados a un usuario específico. **Requiere autenticación.**",
    dependencies=[Depends(get_current_active_user)]
)
async def read_usuario_roles(
    usuario_id: int,
):
    # ... (código existente sin cambios) ...
    try:
        roles = await UsuarioService.obtener_roles_de_usuario(usuario_id)
        return roles # Asume que el servicio devuelve lista de dicts compatibles con RolRead
    except ServiceError as e:
        logger.error(f"Error de servicio obteniendo roles para usuario {usuario_id}: {e.detail}")
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        logger.exception(f"Error inesperado obteniendo roles para usuario {usuario_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno del servidor al obtener los roles del usuario.")