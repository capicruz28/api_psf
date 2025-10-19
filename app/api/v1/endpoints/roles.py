# app/api/v1/endpoints/roles.py
"""
Módulo de endpoints para la gestión de roles y permisos de acceso.

Este módulo proporciona una API REST completa para operaciones CRUD sobre roles,
incluyendo la creación, lectura, actualización y desactivación de roles.
Además, gestiona las operaciones de asignación y revocación de permisos a cada rol.

Características principales:
- Autenticación JWT con requerimiento de rol 'Administrador' para todas las operaciones de gestión.
- Validación robusta de datos de entrada (Pydantic).
- Manejo consistente de errores de negocio con CustomException y mensajes descriptivos.
- Implementación de paginación y búsqueda para el listado de roles.
- Borrado lógico (`es_activo = False`) como mecanismo de desactivación, con opción de reactivación.
- Endpoints específicos para la gestión integral de permisos asociados a cada rol.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, Body, Path
from typing import List, Optional, Dict, Any

# Importar Schemas
from app.schemas.rol import RolCreate, RolUpdate, RolRead, PaginatedRolResponse, PermisoRead, PermisoUpdatePayload

# Importar Servicio
from app.services.rol_service import RolService

# Importar Excepciones personalizadas
from app.core.exceptions import CustomException

# Importar Dependencias de Autorización
from app.api.deps import get_current_active_user, RoleChecker

# Logging
from app.core.logging_config import get_logger
logger = get_logger(__name__)

router = APIRouter()

# --- CONFIGURACIÓN DE DEPENDENCIAS ---
# Requiere rol de administrador para todas las operaciones de gestión
require_admin = RoleChecker(["Administrador"])


# ----------------------------------------------------------------------
# --- Endpoint para Crear Roles ---
# ----------------------------------------------------------------------
@router.post(
    "/",
    response_model=RolRead,
    status_code=status.HTTP_201_CREATED,
    summary="Crear un nuevo rol",
    description="""
    Crea un nuevo rol en el sistema con un nombre único y su descripción.

    **Permisos requeridos:**
    - Rol 'Administrador'

    **Validaciones:**
    - Nombre único (no duplicado).
    - Campos obligatorios: nombre.

    **Respuestas:**
    - 201: Rol creado exitosamente
    - 409: Conflicto - El nombre del rol ya existe
    - 422: Error de validación en los datos de entrada
    - 500: Error interno del servidor
    """,
    dependencies=[Depends(require_admin)]
)
async def create_rol(rol_in: RolCreate = Body(...)):
    """
    Endpoint para crear un nuevo rol.

    Args:
        rol_in: Datos validados del rol a crear (RolCreate).

    Returns:
        RolRead: Rol creado con todos sus datos, incluyendo el ID generado.

    Raises:
        HTTPException: En caso de conflicto de nombre (409), error de validación (422)
                       o error interno del servidor (500).
    """
    logger.info(f"Solicitud POST /roles/ recibida para crear rol: '{rol_in.nombre}'")
    try:
        rol_dict = rol_in.model_dump()
        created_rol = await RolService.crear_rol(rol_data=rol_dict)
        logger.info(f"Rol '{created_rol['nombre']}' creado exitosamente.")
        return created_rol
    except CustomException as ce:
        logger.warning(f"Error de negocio al crear rol '{rol_in.nombre}': {ce.detail}")
        raise HTTPException(status_code=ce.status_code, detail=ce.detail)
    except Exception as e:
        logger.exception("Error inesperado en endpoint POST /roles/")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno del servidor al crear el rol.")


# ----------------------------------------------------------------------
# --- Endpoint para Listar Roles (PAGINADO) ---
# ----------------------------------------------------------------------
@router.get(
    "/",
    response_model=PaginatedRolResponse,
    summary="Obtener lista paginada de roles",
    description="""
    Recupera una lista paginada de roles (activos e inactivos), permitiendo búsqueda por nombre o descripción.

    **Permisos requeridos:**
    - Rol 'Administrador'

    **Parámetros de consulta:**
    - page: Número de página a mostrar (comienza en 1)
    - limit: Número máximo de roles por página (1-100)
    - search: Término opcional para buscar en nombre o descripción

    **Respuestas:**
    - 200: Lista paginada recuperada exitosamente
    - 422: Parámetros de consulta inválidos
    - 500: Error interno del servidor
    """,
    dependencies=[Depends(require_admin)]
)
async def read_roles_paginated(
    page: int = Query(1, ge=1, description="Número de página a recuperar"),
    limit: int = Query(10, ge=1, le=100, description="Número de roles por página"),
    search: Optional[str] = Query(None, description="Término de búsqueda para filtrar por nombre o descripción")
):
    """
    Endpoint para obtener una lista paginada y filtrada de roles.

    Args:
        page: Número de página solicitada.
        limit: Límite de resultados por página.
        search: Término opcional para búsqueda textual.

    Returns:
        PaginatedRolResponse: Respuesta paginada con roles y metadatos.

    Raises:
        HTTPException: En caso de error en los parámetros (422) o error interno (500).
    """
    logger.info(f"Solicitud GET /roles/ recibida - Paginación: page={page}, limit={limit}, Búsqueda: '{search}'")
    try:
        paginated_response = await RolService.obtener_roles_paginados(
            page=page,
            limit=limit,
            search=search
        )
        return paginated_response
    except CustomException as ce:
        logger.warning(f"Error de negocio al listar roles: {ce.detail}")
        raise HTTPException(status_code=ce.status_code, detail=ce.detail)
    except Exception as e:
        logger.exception("Error inesperado en endpoint GET /roles/ (paginado)")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno del servidor al obtener roles paginados.")


# ----------------------------------------------------------------------
# --- Endpoint para Obtener todos los roles activos ---
# ----------------------------------------------------------------------
@router.get(
    "/all-active/",
    response_model=List[RolRead],
    summary="Obtener todos los roles activos",
    description="""
    Devuelve una lista de todos los roles que están actualmente activos, sin paginación.
    Ideal para selectores y listas desplegables en interfaces de usuario.

    **Permisos requeridos:**
    - Rol 'Administrador'

    **Respuestas:**
    - 200: Lista simple recuperada exitosamente
    - 500: Error interno del servidor
    """,
    dependencies=[Depends(require_admin)]
)
async def read_all_active_roles():
    """
    Endpoint para obtener una lista simplificada de roles activos.

    Args:
        None

    Returns:
        List[RolRead]: Lista de todos los roles activos.

    Raises:
        HTTPException: En caso de error interno del servidor (500).
    """
    logger.info("Solicitud GET /roles/all-active/ recibida para lista simple")
    try:
        active_roles = await RolService.get_all_active_roles()
        logger.info(f"Lista simple de roles activos recuperada - Total: {len(active_roles)}")
        return active_roles
    except CustomException as ce:
        logger.error(f"Error de servicio en endpoint /roles/all-active/: {ce.detail}")
        raise HTTPException(status_code=ce.status_code, detail=ce.detail)
    except Exception as e:
        logger.exception("Error inesperado en endpoint GET /roles/all-active/")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ocurrió un error interno al intentar obtener los roles activos."
        )


# ----------------------------------------------------------------------
# --- Endpoint para Obtener un Rol por ID ---
# ----------------------------------------------------------------------
@router.get(
    "/{rol_id}/",
    response_model=RolRead,
    summary="Obtener un rol por ID",
    description="""
    Recupera los detalles completos de un rol específico por su ID.
    Permite obtener roles activos e inactivos (para revisión administrativa).

    **Permisos requeridos:**
    - Rol 'Administrador'

    **Respuestas:**
    - 200: Rol encontrado y devuelto
    - 404: Rol no encontrado
    - 500: Error interno del servidor
    """,
    dependencies=[Depends(require_admin)]
)
async def read_rol(rol_id: int):
    """
    Endpoint para obtener los detalles completos de un rol específico.

    Args:
        rol_id: Identificador único del rol a consultar.

    Returns:
        RolRead: Detalles completos del rol solicitado.

    Raises:
        HTTPException: Si el rol no existe (404) o hay error interno (500).
    """
    logger.debug(f"Solicitud GET /roles/{rol_id}/ recibida")
    try:
        rol = await RolService.obtener_rol_por_id(rol_id=rol_id, incluir_inactivos=True)
        if rol is None:
            logger.warning(f"Rol con ID {rol_id} no encontrado")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Rol con ID {rol_id} no encontrado.")
        logger.debug(f"Rol ID {rol_id} encontrado: '{rol['nombre']}'")
        return rol
    except CustomException as ce:
        logger.error(f"Error de servicio obteniendo rol ID {rol_id}: {ce.detail}")
        raise HTTPException(status_code=ce.status_code, detail=ce.detail)
    except Exception as e:
        logger.exception(f"Error inesperado en endpoint GET /roles/{rol_id}/")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno del servidor al obtener el rol.")


# ----------------------------------------------------------------------
# --- Endpoint para Actualizar un Rol ---
# ----------------------------------------------------------------------
@router.put(
    "/{rol_id}/",
    response_model=RolRead,
    summary="Actualizar un rol existente",
    description="""
    Actualiza la información de un rol existente mediante operación parcial.

    **Permisos requeridos:**
    - Rol 'Administrador'

    **Validaciones:**
    - Si se actualiza el nombre, debe mantenerse único.
    - Al menos un campo debe ser proporcionado.

    **Respuestas:**
    - 200: Rol actualizado exitosamente
    - 400: Cuerpo de solicitud vacío
    - 404: Rol no encontrado
    - 409: Conflicto - Nuevo nombre ya existe
    - 422: Error de validación en los datos
    - 500: Error interno del servidor
    """,
    dependencies=[Depends(require_admin)]
)
async def update_rol(rol_id: int, rol_in: RolUpdate = Body(...)):
    """
    Endpoint para actualizar parcialmente un rol existente.

    Args:
        rol_id: Identificador único del rol a actualizar.
        rol_in: Campos a actualizar (actualización parcial).

    Returns:
        RolRead: Rol actualizado con los nuevos datos.

    Raises:
        HTTPException: En caso de cuerpo vacío (400), rol no encontrado (404),
                       conflicto de nombre (409), o error interno (500).
    """
    logger.info(f"Solicitud PUT /roles/{rol_id}/ recibida para actualizar")
    try:
        update_data = rol_in.model_dump(exclude_unset=True)
        if not update_data:
             logger.warning(f"Intento de actualizar rol {rol_id} sin datos")
             raise HTTPException(
                 status_code=status.HTTP_400_BAD_REQUEST,
                 detail="Se debe proporcionar al menos un campo para actualizar el rol."
             )

        updated_rol = await RolService.actualizar_rol(rol_id=rol_id, rol_data=update_data)
        logger.info(f"Rol ID {rol_id} actualizado exitosamente: '{updated_rol['nombre']}'")
        return updated_rol
    except CustomException as ce:
        logger.warning(f"Error de negocio al actualizar rol {rol_id}: {ce.detail}")
        raise HTTPException(status_code=ce.status_code, detail=ce.detail)
    except Exception as e:
        logger.exception(f"Error inesperado en endpoint PUT /roles/{rol_id}/")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno del servidor al actualizar el rol.")


# ----------------------------------------------------------------------
# --- Endpoint para Desactivar un Rol (Borrado Lógico) ---
# ----------------------------------------------------------------------
@router.delete(
    "/{rol_id}/",
    response_model=RolRead,
    summary="Desactivar un rol (Borrado Lógico)",
    description="""
    Desactiva un rol estableciendo su estado 'es_activo' a False (borrado lógico).

    **Permisos requeridos:**
    - Rol 'Administrador'

    **Notas:**
    - Operación reversible mediante el endpoint de reactivación.
    - No elimina físicamente el registro.

    **Respuestas:**
    - 200: Rol desactivado exitosamente
    - 404: Rol no encontrado
    - 400: Rol ya está desactivado
    - 500: Error interno del servidor
    """,
    dependencies=[Depends(require_admin)]
)
async def deactivate_rol(rol_id: int):
    """
    Endpoint para desactivar un rol (borrado lógico).

    Args:
        rol_id: Identificador único del rol a desactivar.

    Returns:
        RolRead: El rol con el estado `es_activo=False`.

    Raises:
        HTTPException: Si el rol no existe (404), ya está inactivo (400), o hay error interno (500).
    """
    logger.info(f"Solicitud DELETE /roles/{rol_id}/ recibida (desactivar)")
    try:
        deactivated_rol = await RolService.desactivar_rol(rol_id=rol_id)
        logger.info(f"Rol ID {rol_id} desactivado exitosamente")
        return deactivated_rol
    except CustomException as ce:
        logger.warning(f"No se pudo desactivar rol {rol_id}: {ce.detail}")
        raise HTTPException(status_code=ce.status_code, detail=ce.detail)
    except Exception as e:
        logger.exception(f"Error inesperado en endpoint DELETE /roles/{rol_id}/")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno del servidor al desactivar el rol.")


# ----------------------------------------------------------------------
# --- Endpoint para Reactivar un Rol ---
# ----------------------------------------------------------------------
@router.post(
    "/{rol_id}/reactivate/",
    response_model=RolRead,
    status_code=status.HTTP_200_OK,
    summary="Reactivar un rol desactivado",
    description="""
    Reactiva un rol previamente desactivado estableciendo 'es_activo' a True.

    **Permisos requeridos:**
    - Rol 'Administrador'

    **Respuestas:**
    - 200: Rol reactivado exitosamente
    - 404: Rol no encontrado
    - 400: Rol ya está activo
    - 500: Error interno del servidor
    """,
    dependencies=[Depends(require_admin)]
)
async def reactivate_rol(rol_id: int):
    """
    Endpoint para reactivar un rol inactivo.

    Args:
        rol_id: Identificador único del rol a reactivar.

    Returns:
        RolRead: El rol con el estado `es_activo=True`.

    Raises:
        HTTPException: Si el rol no existe (404), ya está activo (400), o hay error interno (500).
    """
    logger.info(f"Solicitud POST /roles/{rol_id}/reactivate/ recibida")
    try:
        reactivated_rol = await RolService.reactivar_rol(rol_id=rol_id)
        logger.info(f"Rol ID {rol_id} reactivado exitosamente")
        return reactivated_rol
    except CustomException as ce:
        logger.warning(f"No se pudo reactivar rol {rol_id}: {ce.detail}")
        raise HTTPException(status_code=ce.status_code, detail=ce.detail)
    except Exception as e:
        logger.exception(f"Error inesperado en endpoint POST /roles/{rol_id}/reactivate/")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno del servidor al reactivar el rol.")


# ----------------------------------------------------------------------
# --- Endpoint para Obtener Permisos de un Rol ---
# ----------------------------------------------------------------------
@router.get(
    "/{rol_id}/permisos/",
    response_model=List[PermisoRead],
    summary="Obtener Permisos de un Rol",
    description="""
    Obtiene la lista de permisos de menú activos asignados a un rol específico.

    **Permisos requeridos:**
    - Rol 'Administrador'

    **Respuestas:**
    - 200: Lista de permisos recuperada
    - 404: Rol no encontrado
    - 500: Error interno del servidor
    """,
    dependencies=[Depends(require_admin)]
)
async def get_permisos_por_rol(
    rol_id: int = Path(..., title="ID del Rol", description="El ID del rol para consultar sus permisos")
):
    """
    Endpoint para obtener los permisos activos asignados a un rol.

    Args:
        rol_id: Identificador único del rol a consultar.

    Returns:
        List[PermisoRead]: Lista de roles activos asignados al usuario.

    Raises:
        HTTPException: Si el rol no existe (404) o hay error interno (500).
    """
    logger.info(f"Solicitud recibida en GET /roles/{rol_id}/permisos/")
    try:
        permisos = await RolService.obtener_permisos_por_rol(rol_id=rol_id)
        logger.debug(f"Permisos para rol {rol_id} recuperados - Total: {len(permisos)}")
        return permisos
    except CustomException as ce:
        logger.error(f"Error de servicio obteniendo permisos para rol {rol_id}: {ce.detail}")
        raise HTTPException(status_code=ce.status_code, detail=ce.detail)
    except Exception as e:
        logger.exception(f"Error inesperado al obtener permisos para rol {rol_id}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al obtener los permisos del rol."
        )


# ----------------------------------------------------------------------
# --- Endpoint para Actualizar Permisos de un Rol ---
# ----------------------------------------------------------------------
@router.put(
    "/{rol_id}/permisos/",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Actualizar Permisos de un Rol",
    description="""
    Sobrescribe **TODOS** los permisos de menú para un rol específico.
    La lista enviada reemplazará completamente la lista actual de permisos.

    **Permisos requeridos:**
    - Rol 'Administrador'

    **Respuestas:**
    - 204: Permisos actualizados exitosamente (No Content)
    - 404: Rol no encontrado
    - 422: Error de validación en la lista de permisos
    - 500: Error interno del servidor
    """,
    dependencies=[Depends(require_admin)]
)
async def update_permisos_rol(
    rol_id: int = Path(..., title="ID del Rol", description="El ID del rol cuyos permisos se actualizarán"),
    payload: PermisoUpdatePayload = Body(..., description="Objeto que contiene la lista completa de los nuevos permisos para el rol")
):
    """
    Endpoint para sobrescribir la lista de permisos de un rol.

    Args:
        rol_id: Identificador único del rol a actualizar.
        payload: Objeto que contiene la lista completa de IDs de permisos a asignar.

    Returns:
        None: Respuesta sin contenido (204).

    Raises:
        HTTPException: Si el rol no existe (404), hay error de validación (422),
                       o error interno (500).
    """
    logger.info(f"Solicitud recibida en PUT /roles/{rol_id}/permisos/")
    try:
        await RolService.actualizar_permisos_rol(rol_id=rol_id, permisos_payload=payload)
        logger.info(f"Permisos para rol {rol_id} actualizados exitosamente")
        return None
    except CustomException as ce:
        logger.error(f"Error de servicio al actualizar permisos para rol {rol_id}: {ce.detail}")
        raise HTTPException(status_code=ce.status_code, detail=ce.detail)
    except Exception as e:
        logger.exception(f"Error inesperado al actualizar permisos para rol {rol_id}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al actualizar los permisos del rol."
        )