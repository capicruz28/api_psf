# app/api/v1/endpoints/areas.py

from fastapi import APIRouter, Depends, HTTPException, status, Body, Query # Añadir Query
from typing import List, Dict, Any, Optional # Añadir Optional

# Importa los schemas necesarios, incluyendo el de paginación
from app.schemas.area import AreaCreate, AreaUpdate, AreaRead, PaginatedAreaResponse
from app.services.area_service import AreaService # Importa tu servicio actualizado
from app.core.exceptions import ServiceError
from app.api.deps import RoleChecker # Asumiendo que RoleChecker está en deps
import logging
from app.schemas.area import AreaSimpleList

logger = logging.getLogger(__name__)
router = APIRouter()

# Dependencia para verificar rol de Administrador (se mantiene igual)
ADMIN_ROLE_CHECK = Depends(RoleChecker(["Administrador"]))

# --- Endpoint POST para Crear ---
@router.post(
    "/",
    response_model=AreaRead,
    status_code=status.HTTP_201_CREATED,
    summary="Crear una nueva área (Admin)",
    dependencies=[ADMIN_ROLE_CHECK]
)
async def crear_area_endpoint(area_in: AreaCreate = Body(...)):
    """Crea una nueva área de menú."""
    logger.info(f"Solicitud POST /areas recibida para crear área: {area_in.nombre}")
    try:
        # Llama al método en español del servicio
        created_area = await AreaService.crear_area(area_in)
        return created_area
    except ServiceError as se:
        logger.warning(f"Error de servicio al crear área: {se.detail} (Status: {se.status_code})")
        raise HTTPException(status_code=se.status_code, detail=se.detail)
    except Exception as e:
        logger.exception("Error inesperado en endpoint POST /areas")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno al crear área.")

# --- Endpoint GET para Obtener Lista Paginada ---
@router.get(
    "/",
    # Cambia el response_model al schema de paginación
    response_model=PaginatedAreaResponse,
    summary="Obtener lista paginada de áreas (Admin)",
    description="Obtiene una lista de áreas con opción de paginación y búsqueda por nombre o descripción. Requiere rol 'Administrador'.",
    dependencies=[ADMIN_ROLE_CHECK]
)
async def obtener_areas_paginadas_endpoint(
    # Añade los parámetros de Query para paginación y búsqueda
    search: Optional[str] = Query(None, description="Término de búsqueda para filtrar por nombre o descripción"),
    skip: int = Query(0, ge=0, description="Número de registros a saltar (paginación)"),
    limit: int = Query(10, ge=1, le=100, description="Número máximo de registros a devolver por página")
):
    """
    Recupera una lista paginada de áreas.

    - **search**: Filtra áreas cuyo nombre o descripción contengan el término.
    - **skip**: Offset para la paginación.
    - **limit**: Tamaño de la página.
    """
    logger.info(f"Solicitud GET /areas recibida (paginada): skip={skip}, limit={limit}, search='{search}'")
    try:
        # Llama al método de paginación del servicio
        paginated_response = await AreaService.obtener_areas_paginadas(skip=skip, limit=limit, search=search)
        return paginated_response
    except ServiceError as se:
        logger.error(f"Error de servicio al obtener áreas paginadas: {se.detail}")
        raise HTTPException(status_code=se.status_code, detail=se.detail)
    except Exception as e:
        logger.exception("Error inesperado en endpoint GET /areas (paginado)")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno al obtener áreas.")

@router.get(
    "/list/",  # ✅ CAMBIO: Agregado /
    response_model=List[AreaSimpleList], # Devuelve una lista del nuevo schema simple
    summary="Obtener lista simple de áreas activas (para selectores)",
    description="Devuelve solo el ID y el nombre de todas las áreas activas. Ideal para poblar listas desplegables.",
    # Podrías quitar la dependencia de Admin si cualquier usuario logueado puede ver las áreas
    dependencies=[ADMIN_ROLE_CHECK]
)
async def obtener_lista_simple_areas_endpoint():
    """Obtiene una lista simplificada (ID, Nombre) de todas las áreas activas."""
    logger.info("Solicitud GET /areas/list/ recibida.")
    try:
        # Necesitarás añadir un método al AreaService para esto
        areas_list = await AreaService.obtener_lista_simple_areas_activas()
        return areas_list
    except ServiceError as se:
        logger.error(f"Error de servicio al obtener lista simple de áreas: {se.detail}")
        raise HTTPException(status_code=se.status_code, detail=se.detail)
    except Exception as e:
        logger.exception("Error inesperado en endpoint GET /areas/list/")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno al obtener la lista de áreas.")

# --- Endpoint GET por ID ---
@router.get(
    "/{area_id}/",  # ✅ CAMBIO: Agregado /
    response_model=AreaRead,
    summary="Obtener un área por ID (Admin)",
    dependencies=[ADMIN_ROLE_CHECK]
)
async def obtener_area_por_id_endpoint(area_id: int):
    """Obtiene los detalles de un área específica por su ID."""
    logger.debug(f"Solicitud GET /areas/{area_id}/ recibida.")
    try:
        # Llama al método en español del servicio
        area = await AreaService.obtener_area_por_id(area_id)
        if area is None:
            logger.warning(f"Área con ID {area_id} no encontrada (servicio devolvió None).")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Área no encontrada")
        return area
    # El servicio obtener_area_por_id ahora no lanza ServiceError directamente,
    # pero lo mantenemos por si acaso o para otros errores inesperados.
    except ServiceError as se:
        logger.error(f"Error de servicio obteniendo área {area_id}: {se.detail}")
        raise HTTPException(status_code=se.status_code, detail=se.detail)
    except Exception as e:
        logger.exception(f"Error inesperado obteniendo área {area_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno al obtener área.")

# --- Endpoint PUT para Actualizar ---
@router.put(
    "/{area_id}/",  # ✅ CAMBIO: Agregado /
    response_model=AreaRead,
    summary="Actualizar un área existente (Admin)",
    dependencies=[ADMIN_ROLE_CHECK]
)
async def actualizar_area_endpoint(area_id: int, area_in: AreaUpdate = Body(...)):
    """Actualiza la información de un área existente."""
    logger.info(f"Solicitud PUT /areas/{area_id}/ recibida.")
    # Pequeña validación para evitar cuerpos vacíos que el servicio también rechazaría
    update_data = area_in.model_dump(exclude_unset=True)
    if not update_data:
         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El cuerpo de la solicitud no puede estar vacío para actualizar.")
    try:
        # Llama al método en español del servicio
        updated_area = await AreaService.actualizar_area(area_id, area_in)
        # El servicio ahora devuelve None si no se encuentra, manejado por la excepción 404 dentro del servicio
        # if updated_area is None: # Esta verificación ya no es necesaria aquí si el servicio lanza 404
        #     raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Área no encontrada para actualizar")
        return updated_area
    except ServiceError as se:
        logger.warning(f"Error de servicio al actualizar área {area_id}: {se.detail} (Status: {se.status_code})")
        raise HTTPException(status_code=se.status_code, detail=se.detail)
    except Exception as e:
        logger.exception(f"Error inesperado en endpoint PUT /areas/{area_id}/")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno al actualizar área.")

# --- Endpoint DELETE para Desactivar ---
@router.delete(
    "/{area_id}/",  # ✅ CAMBIO: Agregado /
    # Cambia el response_model a AreaRead, ya que el servicio devuelve el objeto actualizado
    response_model=AreaRead,
    status_code=status.HTTP_200_OK, # 200 OK es apropiado para una actualización de estado
    summary="Desactivar un área (Borrado Lógico) (Admin)",
    dependencies=[ADMIN_ROLE_CHECK]
)
async def desactivar_area_endpoint(area_id: int):
    """Desactiva un área estableciendo 'es_activo' a False."""
    logger.info(f"Solicitud DELETE /areas/{area_id}/ (desactivar) recibida.")
    try:
        # Llama al método unificado del servicio pasando activar=False
        deactivated_area = await AreaService.cambiar_estado_area(area_id, activar=False)
        # El servicio lanza excepciones 404 o 400 si no se puede desactivar
        return deactivated_area # Devuelve el objeto AreaRead completo
    except ServiceError as se:
        logger.warning(f"No se pudo desactivar área {area_id}: {se.detail} (Status: {se.status_code})")
        raise HTTPException(status_code=se.status_code, detail=se.detail)
    except Exception as e:
        logger.exception(f"Error inesperado en endpoint DELETE /areas/{area_id}/")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno al desactivar área.")

# --- Endpoint PUT para Reactivar ---
@router.put(
    "/{area_id}/reactivate/",  # ✅ CAMBIO: Agregado /
    # Cambia el response_model a AreaRead
    response_model=AreaRead,
    summary="Reactivar un área desactivada (Admin)",
    dependencies=[ADMIN_ROLE_CHECK]
)
async def reactivar_area_endpoint(area_id: int):
    """Reactiva un área estableciendo 'es_activo' a True."""
    logger.info(f"Solicitud PUT /areas/{area_id}/reactivate/ recibida.")
    try:
        # Llama al método unificado del servicio pasando activar=True
        reactivated_area = await AreaService.cambiar_estado_area(area_id, activar=True)
        # El servicio lanza excepciones 404 o 400 si no se puede reactivar
        return reactivated_area # Devuelve el objeto AreaRead completo
    except ServiceError as se:
        logger.warning(f"No se pudo reactivar área {area_id}: {se.detail} (Status: {se.status_code})")
        raise HTTPException(status_code=se.status_code, detail=se.detail)
    except Exception as e:
        logger.exception(f"Error inesperado en endpoint PUT /areas/{area_id}/reactivate/")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno al reactivar área.")