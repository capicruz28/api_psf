# app/api/v1/endpoints/areas.py
"""
Módulo de endpoints para la gestión de áreas del sistema.

Este módulo proporciona una API REST completa para operaciones CRUD sobre áreas,
incluyendo creación, lectura, actualización y desactivación de áreas de menú.

Características principales:
- Autenticación JWT con requerimiento de rol 'Administrador'
- Validación robusta de datos de entrada
- Manejo consistente de errores con mensajes descriptivos
- Paginación y búsqueda para listados
- Operaciones de activación/desactivación (borrado lógico)
"""

from fastapi import APIRouter, Depends, HTTPException, status, Body, Query
from typing import List, Dict, Any, Optional
import logging

# Schemas para áreas
from app.schemas.area import AreaCreate, AreaUpdate, AreaRead, PaginatedAreaResponse, AreaSimpleList

# Servicio de áreas con manejo de errores mejorado
from app.services.area_service import AreaService

# Sistema de excepciones personalizado
from app.core.exceptions import CustomException  # Importar CustomException

# Dependencias de autorización
from app.api.deps import RoleChecker

logger = logging.getLogger(__name__)
router = APIRouter()

# --- CONFIGURACIÓN DE DEPENDENCIAS ---
# Requiere rol de administrador para todas las operaciones
require_admin = RoleChecker(["Administrador"])


# --- ENDPOINTS DE GESTIÓN DE ÁREAS ---

@router.post(
    "/",
    response_model=AreaRead,
    status_code=status.HTTP_201_CREATED,
    summary="Crear una nueva área",
    description="""
    Crea una nueva área en el sistema con los datos proporcionados.
    
    **Permisos requeridos:** 
    - Rol 'Administrador'
    
    **Validaciones:**
    - Nombre único (no duplicado)
    - Formato válido de nombre, descripción e icono
    - Campos obligatorios: nombre
    
    **Respuestas:**
    - 201: Área creada exitosamente
    - 409: Conflicto - El nombre del área ya existe
    - 422: Error de validación en los datos de entrada
    - 500: Error interno del servidor
    """,
    dependencies=[Depends(require_admin)]
)
async def crear_area_endpoint(area_in: AreaCreate = Body(...)):
    """
    Endpoint para crear una nueva área de menú en el sistema.
    
    Args:
        area_in: Datos validados del área a crear
        
    Returns:
        AreaRead: Área creada con todos sus datos incluyendo ID generado
        
    Raises:
        HTTPException: En caso de error de validación, conflicto o error interno
    """
    logger.info(f"Solicitud POST /areas/ recibida para crear área: '{area_in.nombre}'")
    
    try:
        # Delegar la lógica de negocio al servicio
        created_area = await AreaService.crear_area(area_in)
        
        logger.info(f"Área '{created_area.nombre}' creada exitosamente con ID: {created_area.area_id}")
        return created_area
        
    except CustomException as ce:  # Capturamos todas las excepciones personalizadas
        # Log del error
        if ce.status_code == status.HTTP_409_CONFLICT:
            logger.warning(f"Conflicto al crear área '{area_in.nombre}': {ce.detail}")
        else:
            logger.error(f"Error de servicio al crear área: {ce.detail} (Código: {ce.internal_code})")
        raise HTTPException(
            status_code=ce.status_code, 
            detail=ce.detail
        )
    except Exception as e:
        # Error inesperado - log completo pero respuesta genérica al cliente
        logger.exception("Error inesperado en endpoint POST /areas/")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor al crear el área. Por favor, contacte al administrador."
        )


@router.get(
    "/",
    response_model=PaginatedAreaResponse,
    summary="Obtener lista paginada de áreas",
    description="""
    Recupera una lista paginada de áreas con capacidad de búsqueda y filtrado.
    
    **Permisos requeridos:**
    - Rol 'Administrador'
    
    **Parámetros de consulta:**
    - search: Término opcional para buscar en nombre o descripción
    - skip: Número de registros a omitir (para paginación)
    - limit: Número máximo de registros por página (1-100)
    
    **Respuestas:**
    - 200: Lista paginada recuperada exitosamente
    - 422: Parámetros de consulta inválidos
    - 500: Error interno del servidor
    """,
    dependencies=[Depends(require_admin)]
)
async def obtener_areas_paginadas_endpoint(
    search: Optional[str] = Query(
        None, 
        description="Término de búsqueda para filtrar por nombre o descripción"
    ),
    skip: int = Query(
        0, 
        ge=0, 
        description="Número de registros a saltar (offset para paginación)"
    ),
    limit: int = Query(
        10, 
        ge=1, 
        le=100,
        description="Número máximo de registros a devolver por página"
    )
):
    """
    Endpoint para obtener una lista paginada y filtrada de áreas.
    
    Args:
        search: Término opcional para búsqueda textual
        skip: Offset para paginación
        limit: Límite de resultados por página
        
    Returns:
        PaginatedAreaResponse: Respuesta paginada con áreas y metadatos
        
    Raises:
        HTTPException: En caso de error en los parámetros o error interno
    """
    logger.info(
        f"Solicitud GET /areas/ recibida - "
        f"Paginación: skip={skip}, limit={limit}, "
        f"Búsqueda: '{search}'"
    )
    
    try:
        # Obtener datos paginados del servicio
        paginated_response = await AreaService.obtener_areas_paginadas(
            skip=skip, 
            limit=limit, 
            search=search
        )
        
        logger.info(
            f"Lista paginada de áreas recuperada - "
            f"Total: {paginated_response.total_areas}, "
            f"Página: {paginated_response.pagina_actual}"
        )
        return paginated_response
        
    except CustomException as ce:  # Cambio de ServiceError a CustomException
        logger.error(f"Error de servicio al obtener áreas paginadas: {ce.detail}")
        raise HTTPException(
            status_code=ce.status_code, 
            detail=ce.detail
        )
    except Exception as e:
        logger.exception("Error inesperado en endpoint GET /areas/ (paginado)")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor al recuperar la lista de áreas."
        )


@router.get(
    "/list/",
    response_model=List[AreaSimpleList],
    summary="Obtener lista simple de áreas activas",
    description="""
    Devuelve una lista simplificada de áreas activas para uso en selectores o listas desplegables.
    
    **Permisos requeridos:**
    - Rol 'Administrador'
    
    **Respuestas:**
    - 200: Lista simple recuperada exitosamente
    - 500: Error interno del servidor
    """,
    dependencies=[Depends(require_admin)]
)
async def obtener_lista_simple_areas_endpoint():
    """
    Endpoint para obtener una lista simplificada de áreas activas.
    
    Ideal para componentes UI que necesitan solo ID y nombre (selectores, combobox, etc.).
    
    Returns:
        List[AreaSimpleList]: Lista de áreas activas con ID y nombre
        
    Raises:
        HTTPException: En caso de error interno del servidor
    """
    logger.info("Solicitud GET /areas/list/ recibida para lista simple")
    
    try:
        areas_list = await AreaService.obtener_lista_simple_areas_activas()
        
        logger.info(f"Lista simple de áreas recuperada - Total: {len(areas_list)} áreas activas")
        return areas_list
        
    except CustomException as ce:  # Cambio de ServiceError a CustomException
        logger.error(f"Error de servicio al obtener lista simple de áreas: {ce.detail}")
        raise HTTPException(
            status_code=ce.status_code, 
            detail=ce.detail
        )
    except Exception as e:
        logger.exception("Error inesperado en endpoint GET /areas/list/")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor al obtener la lista simplificada de áreas."
        )


@router.get(
    "/{area_id}/",
    response_model=AreaRead,
    summary="Obtener un área por ID",
    description="""
    Recupera los detalles completos de un área específica mediante su ID.
    
    **Permisos requeridos:**
    - Rol 'Administrador'
    
    **Parámetros de ruta:**
    - area_id: ID numérico del área a consultar
    
    **Respuestas:**
    - 200: Área encontrada y devuelta
    - 404: Área no encontrada
    - 500: Error interno del servidor
    """,
    dependencies=[Depends(require_admin)]
)
async def obtener_area_por_id_endpoint(area_id: int):
    """
    Endpoint para obtener los detalles completos de un área específica.
    
    Args:
        area_id: Identificador único del área a consultar
        
    Returns:
        AreaRead: Detalles completos del área solicitada
        
    Raises:
        HTTPException: Si el área no existe o hay error interno
    """
    logger.debug(f"Solicitud GET /areas/{area_id}/ recibida")
    
    try:
        area = await AreaService.obtener_area_por_id(area_id)
        
        if area is None:
            logger.warning(f"Área con ID {area_id} no encontrada")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Área con ID {area_id} no encontrada."
            )
            
        logger.debug(f"Área ID {area_id} encontrada: '{area.nombre}'")
        return area
        
    except CustomException as ce:  # Cambio de ServiceError a CustomException
        logger.error(f"Error de servicio obteniendo área {area_id}: {ce.detail}")
        raise HTTPException(
            status_code=ce.status_code, 
            detail=ce.detail
        )
    except Exception as e:
        logger.exception(f"Error inesperado obteniendo área {area_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor al recuperar el área solicitada."
        )


@router.put(
    "/{area_id}/",
    response_model=AreaRead,
    summary="Actualizar un área existente",
    description="""
    Actualiza la información de un área existente mediante operación parcial (PATCH).
    
    **Permisos requeridos:**
    - Rol 'Administrador'
    
    **Parámetros de ruta:**
    - area_id: ID numérico del área a actualizar
    
    **Validaciones:**
    - Al menos un campo debe ser proporcionado para actualizar
    - Si se actualiza el nombre, debe mantenerse único
    
    **Respuestas:**
    - 200: Área actualizada exitosamente
    - 400: Cuerpo de solicitud vacío
    - 404: Área no encontrada
    - 409: Conflicto - Nuevo nombre ya existe
    - 422: Error de validación en los datos
    - 500: Error interno del servidor
    """,
    dependencies=[Depends(require_admin)]
)
async def actualizar_area_endpoint(
    area_id: int, 
    area_in: AreaUpdate = Body(...)
):
    """
    Endpoint para actualizar parcialmente un área existente.
    
    Args:
        area_id: Identificador único del área a actualizar
        area_in: Campos a actualizar (actualización parcial)
        
    Returns:
        AreaRead: Área actualizada con los nuevos datos
        
    Raises:
        HTTPException: En caso de error de validación, no encontrado o conflicto
    """
    logger.info(f"Solicitud PUT /areas/{area_id}/ recibida para actualizar")
    
    # Validar que hay datos para actualizar
    update_data = area_in.model_dump(exclude_unset=True)
    if not update_data:
        logger.warning(f"Intento de actualizar área {area_id} sin datos")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Se debe proporcionar al menos un campo para actualizar el área."
        )
    
    try:
        # Delegar actualización al servicio
        updated_area = await AreaService.actualizar_area(area_id, area_in)
        
        logger.info(f"Área ID {area_id} actualizada exitosamente: '{updated_area.nombre}'")
        return updated_area
        
    except CustomException as ce:  # Cambio de ServiceError a CustomException
        logger.warning(f"Error de negocio al actualizar área {area_id}: {ce.detail}")
        raise HTTPException(
            status_code=ce.status_code, 
            detail=ce.detail
        )
    except Exception as e:
        logger.exception(f"Error inesperado en endpoint PUT /areas/{area_id}/")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor al actualizar el área."
        )


@router.delete(
    "/{area_id}/",
    response_model=AreaRead,
    status_code=status.HTTP_200_OK,
    summary="Desactivar un área (Borrado Lógico)",
    description="""
    Desactiva un área estableciendo su estado 'es_activo' a False (borrado lógico).
    
    **Permisos requeridos:**
    - Rol 'Administrador'
    
    **Parámetros de ruta:**
    - area_id: ID numérico del área a desactivar
    
    **Notas:**
    - Operación reversible (usar endpoint de reactivación)
    - No elimina físicamente el registro
    
    **Respuestas:**
    - 200: Área desactivada exitosamente
    - 404: Área no encontrada
    - 400: Área ya está desactivada
    - 500: Error interno del servidor
    """,
    dependencies=[Depends(require_admin)]
)
async def desactivar_area_endpoint(area_id: int):
    """
    Endpoint para desactivar un área (borrado lógico).
    
    Args:
        area_id: Identificador único del área a desactivar
        
    Returns:
        AreaRead: Área desactivada con estado actualizado
        
    Raises:
        HTTPException: Si el área no existe, ya está desactivada o hay error interno
    """
    logger.info(f"Solicitud DELETE /areas/{area_id}/ recibida (desactivar)")
    
    try:
        # Usar el servicio unificado para cambiar estado
        deactivated_area = await AreaService.cambiar_estado_area(area_id, activar=False)
        
        logger.info(f"Área ID {area_id} desactivada exitosamente")
        return deactivated_area
        
    except CustomException as ce:  # Cambio de ServiceError a CustomException
        logger.warning(f"No se pudo desactivar área {area_id}: {ce.detail}")
        raise HTTPException(
            status_code=ce.status_code, 
            detail=ce.detail
        )
    except Exception as e:
        logger.exception(f"Error inesperado en endpoint DELETE /areas/{area_id}/")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor al desactivar el área."
        )


@router.put(
    "/{area_id}/reactivate/",
    response_model=AreaRead,
    summary="Reactivar un área desactivada",
    description="""
    Reactiva un área previamente desactivada estableciendo 'es_activo' a True.
    
    **Permisos requeridos:**
    - Rol 'Administrador'
    
    **Parámetros de ruta:**
    - area_id: ID numérico del área a reactivar
    
    **Respuestas:**
    - 200: Área reactivada exitosamente
    - 404: Área no encontrada
    - 400: Área ya está activa
    - 500: Error interno del servidor
    """,
    dependencies=[Depends(require_admin)]
)
async def reactivar_area_endpoint(area_id: int):
    """
    Endpoint para reactivar un área previamente desactivada.
    
    Args:
        area_id: Identificador único del área a reactivar
        
    Returns:
        AreaRead: Área reactivada con estado actualizado
        
    Raises:
        HTTPException: Si el área no existe, ya está activa o hay error interno
    """
    logger.info(f"Solicitud PUT /areas/{area_id}/reactivate/ recibida")
    
    try:
        # Usar el servicio unificado para cambiar estado
        reactivated_area = await AreaService.cambiar_estado_area(area_id, activar=True)
        
        logger.info(f"Área ID {area_id} reactivada exitosamente")
        return reactivated_area
        
    except CustomException as ce:  # Cambio de ServiceError a CustomException
        logger.warning(f"No se pudo reactivar área {area_id}: {ce.detail}")
        raise HTTPException(
            status_code=ce.status_code, 
            detail=ce.detail
        )
    except Exception as e:
        logger.exception(f"Error inesperado en endpoint PUT /areas/{area_id}/reactivate/")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor al reactivar el área."
        )