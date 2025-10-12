# app/api/v1/endpoints/roles.py

from fastapi import APIRouter, Depends, HTTPException, status, Query, Body, Path
from typing import List, Optional, Dict, Any

# Importar Schemas (Añadir PaginatedRolResponse)
from app.schemas.rol import RolCreate, RolUpdate, RolRead, PaginatedRolResponse, PermisoRead, PermisoUpdatePayload

# Importar Servicio
from app.services.rol_service import RolService

# Importar Excepciones personalizadas
from app.core.exceptions import ServiceError, ValidationError

# --- Importar Dependencias de Autorización ---
from app.api.deps import get_current_active_user, RoleChecker

# Logging
from app.core.logging_config import get_logger
logger = get_logger(__name__)

router = APIRouter()

# --- Dependencia específica para requerir rol 'admin' ---
# Asumiendo que tienes un rol llamado 'Administrador' en tu BD
require_admin = RoleChecker(["Administrador"])

# --- Endpoint para Crear Roles (SIN CAMBIOS) ---
@router.post(
    "/",  # ✅ YA TIENE /
    response_model=RolRead,
    status_code=status.HTTP_201_CREATED,
    summary="Crear un nuevo rol",
    description="Crea un nuevo rol en el sistema. **Requiere rol 'Administrador'.**",
    dependencies=[Depends(require_admin)] # Aplicar dependencia de rol
)
async def create_rol(
    rol_in: RolCreate,
    # current_user: Dict[str, Any] = Depends(get_current_active_user) # Opcional si necesitas info del admin que crea
):
    """
    Crea un nuevo rol con los datos proporcionados.
    - **nombre**: Nombre único del rol (obligatorio).
    - **descripcion**: Descripción opcional del rol.
    - **es_activo**: Estado inicial del rol (por defecto True).
    """
    try:
        rol_dict = rol_in.model_dump()
        created_rol = await RolService.crear_rol(rol_data=rol_dict)
        return created_rol
    except ValidationError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except ServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        logger.exception(f"Error inesperado en endpoint create_rol: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno del servidor al crear el rol.")

# --- Endpoint para Listar Roles (PAGINADO) (SIN CAMBIOS DESDE LA ÚLTIMA VERSIÓN) ---
@router.get(
    "/",  # ✅ YA TIENE /
    response_model=PaginatedRolResponse,
    summary="Obtener lista paginada de roles",
    description="Obtiene una lista paginada de roles (activos e inactivos), permitiendo búsqueda por nombre o descripción. **Requiere rol 'Administrador'.**",
    dependencies=[Depends(require_admin)]
)
async def read_roles_paginated(
    page: int = Query(1, ge=1, description="Número de página a recuperar"),
    limit: int = Query(10, ge=1, le=100, description="Número de roles por página"),
    search: Optional[str] = Query(None, description="Término de búsqueda para filtrar por nombre o descripción (insensible a mayúsculas/minúsculas)")
    # current_user: Dict[str, Any] = Depends(require_admin) # Ya está en dependencies
):
    """
    Devuelve una lista paginada de roles (activos e inactivos).
    Permite buscar por nombre o descripción.
    - **page**: Número de la página solicitada (empezando en 1).
    - **limit**: Cantidad de roles a devolver por página.
    - **search**: Texto para buscar en los campos nombre y descripción.
    """
    try:
        paginated_response = await RolService.obtener_roles_paginados(
            page=page,
            limit=limit,
            search=search
        )
        return paginated_response
    except ValidationError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except ServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        logger.exception(f"Error inesperado en endpoint read_roles_paginated: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno del servidor al obtener roles paginados.")

@router.get( # <--- Asegúrate que esta línea NO tenga espacios/tabs al inicio
    "/all-active/",  # ✅ CAMBIO: Agregado /
    response_model=List[RolRead], # La respuesta es una lista de roles
    summary="Obtener todos los roles activos",
    description="Devuelve una lista de todos los roles que están actualmente activos, sin paginación. Ideal para listas desplegables. **Requiere rol 'Administrador'.**",
    dependencies=[Depends(require_admin)] # Proteger el endpoint
)
async def read_all_active_roles(
    # No necesitamos db aquí si el servicio lo maneja
    # current_user: Dict[str, Any] = Depends(require_admin) # Ya está en dependencies
):
    """
    Endpoint para obtener todos los roles activos.
    Requiere que el usuario tenga el rol 'Administrador'.
    """
    logger.info("Accediendo a endpoint /roles/all-active/")
    try:
        # Llamar al método estático del servicio
        active_roles = await RolService.get_all_active_roles()
        logger.info(f"Se obtuvieron {len(active_roles)} roles activos del servicio.")
        # FastAPI se encarga de validar contra List[RolRead]
        return active_roles
    except ServiceError as e:
        # Captura errores específicos del servicio (ej. 500 por fallo en DB)
        logger.error(f"Error de servicio en endpoint /roles/all-active/: {e.detail}")
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        # Captura cualquier otro error inesperado
        logger.exception(f"Error inesperado en endpoint /roles/all-active/: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ocurrió un error interno al intentar obtener los roles activos."
        )    

# --- Endpoint para Obtener un Rol por ID (SIN CAMBIOS) ---
@router.get(
    "/{rol_id}/",  # ✅ CAMBIO: Agregado /
    response_model=RolRead,
    summary="Obtener un rol por ID",
    description="Obtiene los detalles de un rol específico por su ID (activo o inactivo). **Requiere rol 'Administrador'.**",
    dependencies=[Depends(require_admin)]
)
async def read_rol(
    rol_id: int
    # current_user: Dict[str, Any] = Depends(require_admin) # Ya está en dependencies
):
    """
    Devuelve los detalles del rol con el ID especificado.
    """
    try:
        # Llamar al servicio permitiendo buscar inactivos para que el admin los vea
        rol = await RolService.obtener_rol_por_id(rol_id=rol_id, incluir_inactivos=True)
        if rol is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Rol con ID {rol_id} no encontrado.")
        return rol
    except ServiceError as e:
        logger.error(f"Error de servicio obteniendo rol ID {rol_id}: {e.detail}")
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        logger.exception(f"Error inesperado en endpoint read_rol (ID: {rol_id}): {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno del servidor al obtener el rol.")


# --- Endpoint para Actualizar un Rol (SIN CAMBIOS) ---
@router.put(
    "/{rol_id}/",  # ✅ CAMBIO: Agregado /
    response_model=RolRead,
    summary="Actualizar un rol",
    description="Actualiza los datos de un rol existente. **Requiere rol 'Administrador'.**",
    dependencies=[Depends(require_admin)]
)
async def update_rol(
    rol_id: int,
    rol_in: RolUpdate
    # current_user: Dict[str, Any] = Depends(require_admin) # Opcional
):
    """
    Actualiza un rol existente.
    - **rol_id**: ID del rol a actualizar.
    - **rol_in**: Objeto con los campos a actualizar (nombre, descripcion, es_activo).
                 Solo se actualizarán los campos proporcionados.
    """
    try:
        update_data = rol_in.model_dump(exclude_unset=True)
        if not update_data:
             raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se proporcionaron datos para actualizar."
            )

        updated_rol = await RolService.actualizar_rol(rol_id=rol_id, rol_data=update_data)
        return updated_rol
    except ValidationError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except ServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        logger.exception(f"Error inesperado en endpoint update_rol (ID: {rol_id}): {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno del servidor al actualizar el rol.")

# --- Endpoint para Desactivar un Rol (Borrado Lógico) (SIN CAMBIOS) ---
@router.delete(
    "/{rol_id}/",  # ✅ CAMBIO: Agregado /
    response_model=RolRead, # Devuelve el rol actualizado (inactivo)
    summary="Desactivar un rol",
    description="Marca un rol como inactivo (borrado lógico). **Requiere rol 'Administrador'.**",
    dependencies=[Depends(require_admin)]
)
async def deactivate_rol(
    rol_id: int
    # current_user: Dict[str, Any] = Depends(require_admin) # Opcional
):
    """
    Desactiva el rol con el ID especificado. El rol no se elimina permanentemente.
    """
    try:
        deactivated_rol = await RolService.desactivar_rol(rol_id=rol_id)
        return deactivated_rol
    except ValidationError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except ServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        logger.exception(f"Error inesperado en endpoint deactivate_rol (ID: {rol_id}): {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno del servidor al desactivar el rol.")

# --- NUEVO Endpoint para Reactivar un Rol ---
@router.post(
    "/{rol_id}/reactivate/",  # ✅ CAMBIO: Agregado /
    response_model=RolRead, # Devuelve el rol actualizado (activo)
    status_code=status.HTTP_200_OK, # OK es apropiado para una acción exitosa
    summary="Reactivar un rol",
    description="Marca un rol inactivo como activo. **Requiere rol 'Administrador'.**",
    dependencies=[Depends(require_admin)] # Aplicar dependencia de rol
)
async def reactivate_rol(
    rol_id: int
    # current_user: Dict[str, Any] = Depends(require_admin) # Opcional
):
    """
    Reactiva el rol con el ID especificado que previamente fue desactivado.
    """
    try:
        reactivated_rol = await RolService.reactivar_rol(rol_id=rol_id)
        # El servicio ya maneja el caso de rol no encontrado o ya activo
        return reactivated_rol
    except ValidationError as e:
        # Captura 404 (no encontrado) o 400 (ya activo, si se implementó así en el servicio)
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except ServiceError as e:
        # Captura errores 500 del servicio
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        logger.exception(f"Error inesperado en endpoint reactivate_rol (ID: {rol_id}): {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno del servidor al reactivar el rol.")

@router.get(
    "/{rol_id}/permisos/",  # ✅ CAMBIO: Agregado /
    response_model=List[PermisoRead],
    summary="Obtener Permisos de un Rol",
    description="Obtiene la lista de permisos de menú asignados a un rol específico. Requiere rol 'admin'.",
    dependencies=[Depends(RoleChecker(["Administrador"]))]
)
async def get_permisos_por_rol(
    rol_id: int = Path(..., title="ID del Rol", description="El ID del rol para consultar sus permisos")
):
    logger.info(f"Solicitud recibida en GET /roles/{rol_id}/permisos/")
    try:
        # Llamada estática al servicio
        permisos = await RolService.obtener_permisos_por_rol(rol_id=rol_id)
        return permisos
    # --- CAPTURAR ServiceError ---
    except ServiceError as se:
        logger.error(f"Error de servicio en endpoint get_permisos_por_rol (ID: {rol_id}): {se.detail}")
        # Convertir ServiceError a HTTPException
        raise HTTPException(status_code=se.status_code, detail=se.detail)
    # --- QUITAR except NotFoundError ---
    # except NotFoundError as e:
    #      logger.warning(f"Rol no encontrado al obtener permisos: {e}")
    #      raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.exception(f"Error inesperado al obtener permisos para rol {rol_id}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al obtener los permisos del rol."
        )

@router.put(
    "/{rol_id}/permisos/",  # ✅ CAMBIO: Agregado /
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Actualizar Permisos de un Rol",
    description="Sobrescribe TODOS los permisos de menú para un rol específico. Requiere rol 'admin'.",
    dependencies=[Depends(RoleChecker(["Administrador"]))]
)
async def update_permisos_rol(
    rol_id: int = Path(..., title="ID del Rol", description="El ID del rol cuyos permisos se actualizarán"),
    payload: PermisoUpdatePayload = Body(..., description="Objeto que contiene la lista completa de los nuevos permisos para el rol")
):
    logger.info(f"Solicitud recibida en PUT /roles/{rol_id}/permisos/")
    try:
        # Llamada estática al servicio
        await RolService.actualizar_permisos_rol(rol_id=rol_id, permisos_payload=payload)
        return None
    # --- CAPTURAR ServiceError ---
    except ServiceError as se:
        logger.error(f"Error de servicio en endpoint update_permisos_rol (ID: {rol_id}): {se.detail}")
        # Convertir ServiceError a HTTPException
        raise HTTPException(status_code=se.status_code, detail=se.detail)
    # --- QUITAR except NotFoundError ---
    # except NotFoundError as e:
    #     logger.warning(f"Rol no encontrado al intentar actualizar permisos: {e}")
    #     raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.exception(f"Error inesperado al actualizar permisos para rol {rol_id}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al actualizar los permisos del rol."
        )

# --- FIN DE LOS ENDPOINTS DE ROLES ---