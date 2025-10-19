# app/api/v1/endpoints/permisos.py
"""
Módulo de endpoints para la gestión granular de permisos de roles sobre elementos de menú.

Este módulo proporciona una API REST dedicada a las operaciones CRUD (Creación, Lectura, Actualización, Eliminación)
de la relación Rol-Menú-Permiso. Permite establecer qué acciones (ver, editar, eliminar)
puede realizar un rol específico sobre un determinado menú o característica.

Características principales:
- Gestión completa de la matriz de permisos (Rol x Menú x Acción).
- Autenticación JWT con requerimiento estricto del rol 'Administrador'.
- Manejo consistente de errores utilizando CustomException.
- Operación de asignación/actualización unificada (PUT).
- Eliminación (Revocación) del registro de permiso.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Body
from typing import List, Dict, Optional, Any

# Importar Schemas (Manteniéndolos aquí como se especificó, idealmente en app/schemas/permiso.py)
from pydantic import BaseModel, Field

class PermisoBase(BaseModel):
    puede_ver: Optional[bool] = Field(None, description="Permiso para ver el menú")
    puede_editar: Optional[bool] = Field(None, description="Permiso para editar (ej. contenido asociado al menú)")
    puede_eliminar: Optional[bool] = Field(None, description="Permiso para eliminar (ej. contenido asociado al menú)")

class PermisoCreateUpdate(PermisoBase):
    # Al menos uno debe ser proporcionado al crear/actualizar
    pass

class PermisoRead(PermisoBase):
    rol_menu_id: int
    rol_id: int
    menu_id: int

    class Config:
        from_attributes = True # Compatible con ORM o diccionarios

class PermisoReadWithMenu(PermisoRead):
    menu_nombre: Optional[str] = None
    menu_url: Optional[str] = None
    menu_icono: Optional[str] = None

    class Config:
        from_attributes = True


# Importar Servicio
from app.services.permiso_service import PermisoService

# Importar Excepciones personalizadas (Estandarizado a CustomException)
from app.core.exceptions import CustomException 
# from app.core.exceptions import ServiceError, ValidationError # ELIMINADAS/IGNORADAS

# Importar Dependencias de Autorización
from app.api.deps import get_current_active_user, RoleChecker

# Logging
from app.core.logging_config import get_logger
logger = get_logger(__name__)

router = APIRouter()

# Dependencia específica para requerir rol 'admin'
require_admin = RoleChecker(["Administrador"])

# ----------------------------------------------------------------------
# --- Endpoint para Asignar/Actualizar Permisos (PUT) ---
# ----------------------------------------------------------------------
@router.put(
    "/roles/{rol_id}/menus/{menu_id}/",
    response_model=PermisoRead,
    summary="Asignar o actualizar permisos de un rol sobre un menú",
    description="""
    Establece los permisos (ver, editar, eliminar) para un rol específico sobre un menú específico. 
    Si la asignación de permisos no existe, se crea. Si existe, se actualiza con los valores proporcionados.

    **Permisos requeridos:**
    - Rol 'Administrador'

    **Respuestas:**
    - 200: Permiso creado/actualizado exitosamente
    - 404: Rol o Menú no encontrado
    - 422: Error de validación en los datos de entrada
    - 500: Error interno del servidor
    """,
    dependencies=[Depends(require_admin)]
)
async def set_permission(
    rol_id: int,
    menu_id: int,
    permisos_in: PermisoCreateUpdate = Body(...)
):
    """
    Asigna o actualiza los permisos `puede_ver`, `puede_editar`, `puede_eliminar`
    para el `rol_id` sobre el `menu_id`.

    Args:
        rol_id: ID del rol al que se le asigna el permiso.
        menu_id: ID del menú sobre el que se asigna el permiso.
        permisos_in: Objeto con los flags booleanos (puede_ver, puede_editar, puede_eliminar) a establecer.

    Returns:
        PermisoRead: La asignación de permiso resultante, con sus IDs de relación.

    Raises:
        HTTPException: En caso de rol/menú no encontrado (404), error de validación (422) o error interno (500).
    """
    logger.info(f"Solicitud PUT /permisos/roles/{rol_id}/menus/{menu_id}/ recibida para crear/actualizar")
    try:
        updated_perm = await PermisoService.asignar_o_actualizar_permiso(
            rol_id=rol_id,
            menu_id=menu_id,
            puede_ver=permisos_in.puede_ver,
            puede_editar=permisos_in.puede_editar,
            puede_eliminar=permisos_in.puede_eliminar
        )
        logger.info(f"Permiso para Rol {rol_id} y Menú {menu_id} gestionado exitosamente.")
        return updated_perm
    # MODIFICACIÓN: Capturar CustomException en lugar de ServiceError/ValidationError
    except CustomException as ce:
        logger.warning(f"Error de negocio al gestionar permiso (Rol: {rol_id}, Menú: {menu_id}): {ce.detail}")
        raise HTTPException(status_code=ce.status_code, detail=ce.detail)
    except Exception as e:
        logger.exception(f"Error inesperado en endpoint PUT /permisos/roles/{rol_id}/menus/{menu_id}/")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno del servidor al gestionar el permiso.")

# ----------------------------------------------------------------------
# --- Endpoint para Obtener Permisos de un Rol (LISTA) ---
# ----------------------------------------------------------------------
@router.get(
    "/roles/{rol_id}/permisos/",
    response_model=List[PermisoReadWithMenu],
    summary="Obtener todos los permisos de un rol",
    description="""
    Devuelve una lista de todos los permisos asignados a un rol específico, incluyendo detalles del menú asociado (nombre, URL, ícono).

    **Permisos requeridos:**
    - Rol 'Administrador'

    **Respuestas:**
    - 200: Lista de permisos recuperada exitosamente
    - 404: Rol no encontrado
    - 500: Error interno del servidor
    """,
    dependencies=[Depends(require_admin)]
)
async def get_permissions_for_role(rol_id: int):
    """
    Obtiene la lista de permisos para el rol con el ID especificado, con detalles de menú.

    Args:
        rol_id: ID del rol cuyos permisos se desean consultar.

    Returns:
        List[PermisoReadWithMenu]: Lista de permisos del rol, con información del menú.

    Raises:
        HTTPException: En caso de rol no encontrado (404) o error interno (500).
    """
    logger.debug(f"Solicitud GET /permisos/roles/{rol_id}/permisos/ recibida")
    try:
        permisos = await PermisoService.obtener_permisos_por_rol(rol_id=rol_id)
        logger.debug(f"Permisos para Rol {rol_id} recuperados - Total: {len(permisos)}")
        return permisos
    # MODIFICACIÓN: Capturar CustomException
    except CustomException as ce:
        logger.error(f"Error de negocio al obtener permisos para Rol {rol_id}: {ce.detail}")
        raise HTTPException(status_code=ce.status_code, detail=ce.detail)
    except Exception as e:
        logger.exception(f"Error inesperado en endpoint GET /permisos/roles/{rol_id}/permisos/")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno del servidor al obtener los permisos.")

# ----------------------------------------------------------------------
# --- Endpoint para Obtener Permiso Específico (GET) ---
# ----------------------------------------------------------------------
@router.get(
    "/roles/{rol_id}/menus/{menu_id}/",
    response_model=PermisoRead,
    summary="Obtener el permiso específico de un rol sobre un menú",
    description="""
    Devuelve los detalles de la asignación de permisos de un rol sobre un menú específico.

    **Permisos requeridos:**
    - Rol 'Administrador'

    **Respuestas:**
    - 200: Permiso encontrado y devuelto
    - 404: Permiso (asignación Rol-Menú) no encontrado
    - 500: Error interno del servidor
    """,
    dependencies=[Depends(require_admin)]
)
async def get_specific_permission(rol_id: int, menu_id: int):
    """
    Obtiene el permiso específico para el `rol_id` y `menu_id`.

    Args:
        rol_id: ID del rol asociado al permiso.
        menu_id: ID del menú asociado al permiso.

    Returns:
        PermisoRead: La asignación de permiso encontrada.

    Raises:
        HTTPException: Si la asignación de permiso no existe (404) o hay error interno (500).
    """
    logger.debug(f"Solicitud GET /permisos/roles/{rol_id}/menus/{menu_id}/ recibida")
    try:
        permiso = await PermisoService.obtener_permiso_especifico(rol_id=rol_id, menu_id=menu_id)
        if permiso is None:
            logger.warning(f"Permiso no encontrado para Rol {rol_id} y Menú {menu_id}")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Permiso no encontrado para Rol {rol_id} y Menú {menu_id}.")
        return permiso
    # MODIFICACIÓN: Capturar CustomException
    except CustomException as ce:
        logger.error(f"Error de negocio al obtener permiso específico (Rol: {rol_id}, Menú: {menu_id}): {ce.detail}")
        raise HTTPException(status_code=ce.status_code, detail=ce.detail)
    except Exception as e:
        logger.exception(f"Error inesperado en endpoint GET /permisos/roles/{rol_id}/menus/{menu_id}/")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno del servidor al obtener el permiso.")


# ----------------------------------------------------------------------
# --- Endpoint para Revocar Permiso (DELETE) ---
# ----------------------------------------------------------------------
@router.delete(
    "/roles/{rol_id}/menus/{menu_id}/",
    response_model=Dict[str, str],
    summary="Revocar el permiso de un rol sobre un menú",
    description="""
    Elimina (revoca) la asignación de permisos entre un rol y un menú.

    **Permisos requeridos:**
    - Rol 'Administrador'

    **Respuestas:**
    - 200: Permiso revocado exitosamente
    - 404: Permiso no encontrado (no se puede eliminar lo que no existe)
    - 500: Error interno del servidor
    """,
    dependencies=[Depends(require_admin)]
)
async def revoke_permission(rol_id: int, menu_id: int):
    """
    Elimina el permiso asociado al `rol_id` y `menu_id`.

    Args:
        rol_id: ID del rol al que se le revoca el permiso.
        menu_id: ID del menú del que se revoca el permiso.

    Returns:
        Dict[str, str]: Mensaje de éxito de la operación.

    Raises:
        HTTPException: Si el permiso no existe (404) o hay error interno (500).
    """
    logger.info(f"Solicitud DELETE /permisos/roles/{rol_id}/menus/{menu_id}/ recibida para revocar")
    try:
        result = await PermisoService.revocar_permiso(rol_id=rol_id, menu_id=menu_id)
        logger.info(f"Permiso para Rol {rol_id} y Menú {menu_id} revocado exitosamente.")
        return result
    # MODIFICACIÓN: Capturar CustomException
    except CustomException as ce:
        logger.warning(f"Error de negocio al revocar permiso (Rol: {rol_id}, Menú: {menu_id}): {ce.detail}")
        raise HTTPException(status_code=ce.status_code, detail=ce.detail)
    except Exception as e:
        logger.exception(f"Error inesperado en endpoint DELETE /permisos/roles/{rol_id}/menus/{menu_id}/")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno del servidor al revocar el permiso.")