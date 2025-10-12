# app/api/v1/endpoints/permisos.py

from fastapi import APIRouter, Depends, HTTPException, status, Body
from typing import List, Dict, Optional, Any

# Importar Schemas (Necesitamos definir Pydantic Schemas para los permisos)
# Vamos a definirlos aquí mismo por simplicidad, pero idealmente irían en app/schemas/permiso.py
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

# Importar Excepciones personalizadas
from app.core.exceptions import ServiceError, ValidationError

# Importar Dependencias de Autorización
from app.api.deps import get_current_active_user, RoleChecker

# Logging
from app.core.logging_config import get_logger
logger = get_logger(__name__)

router = APIRouter()

# Dependencia específica para requerir rol 'admin'
require_admin = RoleChecker(["Administrador"])

# --- Endpoint para Asignar/Actualizar Permisos ---
@router.put(
    "/roles/{rol_id}/menus/{menu_id}/",  # ✅ CAMBIO: Agregado /
    response_model=PermisoRead,
    summary="Asignar o actualizar permisos de un rol sobre un menú",
    description="Establece los permisos (ver, editar, eliminar) para un rol específico sobre un menú específico. Si el permiso no existe, se crea. Si existe, se actualiza con los valores proporcionados. **Requiere rol 'admin'.**",
    dependencies=[Depends(require_admin)]
)
async def set_permission(
    rol_id: int,
    menu_id: int,
    permisos_in: PermisoCreateUpdate = Body(...) # Usar Body para recibir el payload
    # current_user: Dict[str, Any] = Depends(get_current_active_user) # Opcional
):
    """
    Asigna o actualiza los permisos `puede_ver`, `puede_editar`, `puede_eliminar`
    para el `rol_id` sobre el `menu_id`.
    """
    try:
        # Pasar los valores directamente al servicio
        updated_perm = await PermisoService.asignar_o_actualizar_permiso(
            rol_id=rol_id,
            menu_id=menu_id,
            puede_ver=permisos_in.puede_ver,
            puede_editar=permisos_in.puede_editar,
            puede_eliminar=permisos_in.puede_eliminar
        )
        # El servicio ya devuelve un diccionario compatible con PermisoRead
        return updated_perm
    except ValidationError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except ServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        logger.exception(f"Error inesperado en endpoint set_permission (Rol: {rol_id}, Menú: {menu_id}): {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno del servidor al gestionar el permiso.")

# --- Endpoint para Obtener Permisos de un Rol ---
@router.get(
    "/roles/{rol_id}/permisos/",  # ✅ CAMBIO: Agregado /
    response_model=List[PermisoReadWithMenu], # Usamos el schema con datos del menú
    summary="Obtener todos los permisos de un rol",
    description="Devuelve una lista de todos los permisos asignados a un rol específico, incluyendo detalles del menú asociado. **Requiere rol 'admin'.**",
    # Podría requerir solo autenticación si un usuario necesita ver sus propios permisos
    dependencies=[Depends(require_admin)]
)
async def get_permissions_for_role(
    rol_id: int,
    # current_user: Dict[str, Any] = Depends(get_current_active_user) # Opcional
):
    """
    Obtiene la lista de permisos para el rol con el ID especificado.
    """
    try:
        permisos = await PermisoService.obtener_permisos_por_rol(rol_id=rol_id)
        # El servicio ya devuelve diccionarios compatibles con PermisoReadWithMenu
        return permisos
    except ServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        logger.exception(f"Error inesperado en endpoint get_permissions_for_role (Rol: {rol_id}): {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno del servidor al obtener los permisos.")

# --- Endpoint para Obtener Permiso Específico ---
@router.get(
    "/roles/{rol_id}/menus/{menu_id}/",  # ✅ CAMBIO: Agregado /
    response_model=PermisoRead,
    summary="Obtener el permiso específico de un rol sobre un menú",
    description="Devuelve los detalles del permiso de un rol sobre un menú específico. **Requiere rol 'admin'.**",
    dependencies=[Depends(require_admin)]
)
async def get_specific_permission(
    rol_id: int,
    menu_id: int,
    # current_user: Dict[str, Any] = Depends(get_current_active_user) # Opcional
):
    """
    Obtiene el permiso específico para el `rol_id` y `menu_id`.
    """
    try:
        permiso = await PermisoService.obtener_permiso_especifico(rol_id=rol_id, menu_id=menu_id)
        if permiso is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Permiso no encontrado para Rol {rol_id} y Menú {menu_id}.")
        return permiso
    except ServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        logger.exception(f"Error inesperado en endpoint get_specific_permission (Rol: {rol_id}, Menú: {menu_id}): {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno del servidor al obtener el permiso.")


# --- Endpoint para Revocar Permiso ---
@router.delete(
    "/roles/{rol_id}/menus/{menu_id}/",  # ✅ CAMBIO: Agregado /
    response_model=Dict[str, str], # Devuelve un mensaje de éxito
    summary="Revocar el permiso de un rol sobre un menú",
    description="Elimina la asignación de permisos entre un rol y un menú. **Requiere rol 'admin'.**",
    dependencies=[Depends(require_admin)]
)
async def revoke_permission(
    rol_id: int,
    menu_id: int,
    # current_user: Dict[str, Any] = Depends(get_current_active_user) # Opcional
):
    """
    Elimina el permiso asociado al `rol_id` y `menu_id`.
    """
    try:
        result = await PermisoService.revocar_permiso(rol_id=rol_id, menu_id=menu_id)
        return result
    except ValidationError as e: # Captura el 404 si no se encuentra
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except ServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        logger.exception(f"Error inesperado en endpoint revoke_permission (Rol: {rol_id}, Menú: {menu_id}): {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno del servidor al revocar el permiso.")