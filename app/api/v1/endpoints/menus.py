# app/api/v1/endpoints/menus.py
"""
Módulo de endpoints para la gestión y consulta de la estructura del menú.

Este módulo proporciona la lógica para:
- Obtener el menú de navegación específico para un usuario autenticado (basado en roles/permisos).
- Operaciones CRUD (Crear, Leer, Actualizar, Desactivar/Reactivar) sobre ítems del menú.
- Obtener la estructura jerárquica completa del menú para administración.
- Obtener la estructura del menú filtrada por Área.

Características principales:
- Autenticación JWT.
- Requerimiento de rol 'Administrador' para todas las operaciones de gestión (CRUD y listados completos).
- Manejo consistente de errores de negocio con CustomException y mensajes descriptivos.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Body, Path
from typing import Dict, Any, List # Mantenemos List por si hay endpoints que devuelven listas simples

# Importar Schemas
from app.schemas.menu import (
    MenuResponse, MenuCreate, MenuUpdate, MenuReadSingle, MenuItem
)
from app.schemas.usuario import UsuarioReadWithRoles # Para dependencia de usuario

# Importar Servicio
from app.services.menu_service import MenuService

# Importar Excepciones personalizadas (Asumimos CustomException es la estándar ahora)
from app.core.exceptions import CustomException # Reemplaza ServiceError

# Importar Dependencias de Autorización
from app.api.deps import get_current_active_user, RoleChecker

# Logging
from app.core.logging_config import get_logger
logger = get_logger(__name__)

# --- Declaración del Router ---
router = APIRouter()

# --- CONFIGURACIÓN DE DEPENDENCIAS ---
# Requiere rol de administrador para todas las operaciones de gestión
# Asumiendo que 'Administrador' es el rol usado en la BD
require_admin = RoleChecker(["Administrador"])


# ----------------------------------------------------------------------
# --- Endpoint: Obtener Menú del Usuario Autenticado ---
# ----------------------------------------------------------------------
@router.get(
    "/getmenu/",
    response_model=MenuResponse,
    summary="Obtener Menú del Usuario Autenticado",
    description="""
    Obtiene la estructura de menú permitida para el usuario actualmente autenticado, 
    basada en sus roles y permisos asignados.

    **Permisos requeridos:**
    - Usuario autenticado y activo.

    **Respuestas:**
    - 200: Menú estructurado devuelto.
    - 401: No autenticado.
    - 500: Error interno del servidor.
    """,
)
async def get_menu(
    current_user: UsuarioReadWithRoles = Depends(get_current_active_user)
):
    """
    Endpoint para obtener el menú de navegación específico para el usuario.

    Args:
        current_user: El objeto usuario autenticado y activo (inyectado por dependencia).

    Returns:
        MenuResponse: Estructura jerárquica del menú permitida.

    Raises:
        HTTPException: En caso de error de servicio (ServiceError -> CustomException) o error interno (500).
    """
    logger.info(f"Solicitud GET /menus/getmenu/ recibida para usuario ID: {current_user.usuario_id}")
    try:
        menu_response = await MenuService.get_menu_for_user(current_user.usuario_id)
        return menu_response
    except CustomException as ce:
        logger.error(f"Error de servicio en GET /getmenu/ para usuario {current_user.usuario_id}: {ce.detail}")
        raise HTTPException(status_code=ce.status_code, detail=ce.detail)
    except Exception as e:
        logger.exception(f"Error inesperado durante la obtención del menú para usuario {current_user.usuario_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor al procesar el menú del usuario."
        )


# ----------------------------------------------------------------------
# --- Endpoint: Obtener Árbol Completo de Menús (Admin) ---
# ----------------------------------------------------------------------
@router.get(
    "/all-structured/",
    response_model=MenuResponse,
    summary="Obtener Árbol Completo de Menús (Admin)",
    description="""
    Obtiene todos los elementos del menú (activos e inactivos) estructurados jerárquicamente. 
    Ideal para la administración completa del menú.

    **Permisos requeridos:**
    - Rol 'Administrador'

    **Respuestas:**
    - 200: Estructura completa del menú devuelta.
    - 403: Acceso denegado (no Admin).
    - 500: Error interno del servidor.
    """,
    dependencies=[Depends(require_admin)]
)
async def get_all_menus_admin_structured_endpoint():
    """
    Endpoint para obtener el árbol jerárquico completo de todos los ítems de menú (incluyendo inactivos).

    Args:
        None.

    Returns:
        MenuResponse: Estructura jerárquica completa del menú.

    Raises:
        HTTPException: En caso de error de servicio (CustomException) o error interno (500).
    """
    logger.info("Solicitud recibida en GET /menus/all-structured/ (Admin)")
    try:
        response = await MenuService.obtener_todos_menus_estructurados_admin()
        return response
    except CustomException as ce:
        logger.error(f"Error de servicio en GET /menus/all-structured/: {ce.detail}")
        raise HTTPException(status_code=ce.status_code, detail=ce.detail)
    except Exception as e:
        logger.exception("Error inesperado en el endpoint /menus/all-structured/")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor al obtener la estructura completa del menú."
        )


# ----------------------------------------------------------------------
# --- Endpoint: Crear Menú ---
# ----------------------------------------------------------------------
@router.post(
    "/",
    response_model=MenuReadSingle,
    status_code=status.HTTP_201_CREATED,
    summary="Crear un nuevo ítem de menú (Admin)",
    description="""
    Crea un nuevo ítem en el menú (opción, submenú, etc.).

    **Permisos requeridos:**
    - Rol 'Administrador'

    **Validaciones:**
    - Campos obligatorios (e.g., nombre, url).
    - Posible validación de unicidad o existencia de padre.

    **Respuestas:**
    - 201: Ítem de menú creado exitosamente.
    - 400: Error de validación de datos (e.g., padre no existe).
    - 403: Acceso denegado (no Admin).
    - 422: Error de validación Pydantic.
    - 500: Error interno del servidor.
    """,
    dependencies=[Depends(require_admin)]
)
async def create_menu_endpoint(
    menu_in: MenuCreate = Body(...)
):
    """
    Endpoint para crear un nuevo ítem de menú.

    Args:
        menu_in: Datos validados del ítem de menú a crear (MenuCreate).

    Returns:
        MenuReadSingle: El ítem de menú creado con su ID.

    Raises:
        HTTPException: En caso de conflicto, error de validación de negocio (CustomException) o error interno (500).
    """
    logger.info(f"Recibida solicitud POST /menus/ para crear menú: {menu_in.nombre}")
    try:
        created_menu = await MenuService.crear_menu(menu_in)
        return created_menu
    except CustomException as ce:
        logger.warning(f"Error de servicio (posible validación) al crear menú: {ce.detail}")
        # Usa el status_code de la excepción del servicio (puede ser 400 o 500)
        raise HTTPException(status_code=ce.status_code, detail=ce.detail)
    except Exception as e:
        logger.exception("Error inesperado en endpoint POST /menus/")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno al crear menú.")


# ----------------------------------------------------------------------
# --- Endpoint: Obtener Menú por ID ---
# ----------------------------------------------------------------------
@router.get(
    "/{menu_id}/",
    response_model=MenuReadSingle,
    summary="Obtener detalles de un ítem de menú por ID (Admin)",
    description="""
    Recupera los detalles completos de un ítem de menú específico por su ID. 
    Permite obtener ítems activos e inactivos (para revisión administrativa).

    **Permisos requeridos:**
    - Rol 'Administrador'

    **Respuestas:**
    - 200: Ítem de menú encontrado y devuelto.
    - 403: Acceso denegado (no Admin).
    - 404: Ítem de menú no encontrado.
    - 500: Error interno del servidor.
    """,
    dependencies=[Depends(require_admin)]
)
async def get_menu_by_id_endpoint(menu_id: int = Path(..., title="ID del Menú", description="El ID del ítem de menú a consultar")):
    """
    Endpoint para obtener los detalles completos de un ítem de menú específico.

    Args:
        menu_id: Identificador único del ítem de menú.

    Returns:
        MenuReadSingle: Detalles completos del ítem solicitado.

    Raises:
        HTTPException: Si el ítem no existe (404), error de servicio (CustomException) o hay error interno (500).
    """
    logger.debug(f"Recibida solicitud GET /menus/{menu_id}/")
    try:
        menu = await MenuService.obtener_menu_por_id(menu_id)
        if menu is None:
            # Si el servicio devuelve None, lanzamos 404 aquí
            logger.warning(f"Menú con ID {menu_id} no encontrado (servicio devolvió None).")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Menú con ID {menu_id} no encontrado.")
        logger.debug(f"Menú ID {menu_id} encontrado.")
        return menu
    except CustomException as ce: # Captura CustomException si el servicio lo lanza
        logger.error(f"Error de servicio obteniendo menú {menu_id}: {ce.detail}")
        raise HTTPException(status_code=ce.status_code, detail=ce.detail)
    except Exception as e:
        logger.exception(f"Error inesperado obteniendo menú {menu_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno al obtener menú.")


# ----------------------------------------------------------------------
# --- Endpoint: Actualizar Menú ---
# ----------------------------------------------------------------------
@router.put(
    "/{menu_id}/",
    response_model=MenuReadSingle,
    summary="Actualizar un ítem de menú existente (Admin)",
    description="""
    Actualiza la información de un ítem de menú existente mediante operación parcial.

    **Permisos requeridos:**
    - Rol 'Administrador'

    **Validaciones:**
    - Al menos un campo debe ser proporcionado.

    **Respuestas:**
    - 200: Ítem de menú actualizado exitosamente.
    - 400: Cuerpo de solicitud vacío.
    - 403: Acceso denegado (no Admin).
    - 404: Ítem de menú no encontrado.
    - 409: Conflicto (e.g., url duplicada si se validara).
    - 422: Error de validación Pydantic.
    - 500: Error interno del servidor.
    """,
    dependencies=[Depends(require_admin)]
)
async def update_menu_endpoint(
    menu_id: int = Path(..., title="ID del Menú", description="El ID del ítem de menú a actualizar"),
    menu_in: MenuUpdate = Body(...)
):
    """
    Endpoint para actualizar parcialmente un ítem de menú existente.

    Args:
        menu_id: Identificador único del ítem de menú a actualizar.
        menu_in: Campos a actualizar (actualización parcial).

    Returns:
        MenuReadSingle: Ítem de menú actualizado con los nuevos datos.

    Raises:
        HTTPException: En caso de cuerpo vacío (400), no encontrado (404),
                       error de servicio (CustomException) o error interno (500).
    """
    logger.info(f"Recibida solicitud PUT /menus/{menu_id}/")
    try:
        update_data = menu_in.model_dump(exclude_unset=True)
        if not update_data:
            logger.warning(f"Intento de actualizar menú {menu_id} sin datos")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El cuerpo de la solicitud no puede estar vacío para actualizar."
            )

        updated_menu = await MenuService.actualizar_menu(menu_id, menu_in)
        return updated_menu
    except CustomException as ce: # Captura CustomException directamente (puede ser 404, 400, 500)
        logger.warning(f"Error de servicio al actualizar menú {menu_id}: {ce.detail}")
        raise HTTPException(status_code=ce.status_code, detail=ce.detail)
    except Exception as e:
        logger.exception(f"Error inesperado en endpoint PUT /menus/{menu_id}/")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno al actualizar menú.")


# ----------------------------------------------------------------------
# --- Endpoint: Desactivar Menú (Borrado Lógico) ---
# ----------------------------------------------------------------------
@router.delete(
    "/{menu_id}/",
    status_code=status.HTTP_200_OK,
    response_model=Dict[str, Any],
    summary="Desactivar un ítem de menú (Borrado Lógico) (Admin)",
    description="""
    Desactiva un ítem de menú estableciendo su estado 'es_activo' a False (borrado lógico).

    **Permisos requeridos:**
    - Rol 'Administrador'

    **Notas:**
    - Operación reversible mediante el endpoint de reactivación.
    - No elimina físicamente el registro.

    **Respuestas:**
    - 200: Ítem de menú desactivado exitosamente (devuelve el ID y estado).
    - 400: Ítem ya está desactivado.
    - 403: Acceso denegado (no Admin).
    - 404: Ítem de menú no encontrado.
    - 500: Error interno del servidor.
    """,
    dependencies=[Depends(require_admin)]
)
async def deactivate_menu_endpoint(menu_id: int = Path(..., title="ID del Menú", description="El ID del ítem de menú a desactivar")):
    """
    Endpoint para desactivar un ítem de menú (borrado lógico).

    Args:
        menu_id: Identificador único del ítem de menú a desactivar.

    Returns:
        Dict[str, Any]: Mensaje de confirmación y el estado `es_activo=False`.

    Raises:
        HTTPException: Si no existe (404), error de servicio (CustomException) o error interno (500).
    """
    logger.info(f"Solicitud DELETE /menus/{menu_id}/ recibida (desactivar)")
    try:
        result = await MenuService.desactivar_menu(menu_id)
        logger.info(f"Menú ID {menu_id} desactivado exitosamente")
        return {"message": f"Menú ID {result.get('menu_id')} desactivado exitosamente.", "menu_id": result.get('menu_id'), "es_activo": result.get('es_activo')}
    except CustomException as ce: # Captura CustomException directamente (puede ser 404, 400, 500)
        logger.warning(f"No se pudo desactivar menú {menu_id}: {ce.detail}")
        raise HTTPException(status_code=ce.status_code, detail=ce.detail)
    except Exception as e:
        logger.exception(f"Error inesperado en endpoint DELETE /menus/{menu_id}/")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno al desactivar menú.")


# ----------------------------------------------------------------------
# --- Endpoint: Reactivar Menú ---
# ----------------------------------------------------------------------
@router.put(
    "/{menu_id}/reactivate/",
    response_model=Dict[str, Any],
    summary="Reactivar un ítem de menú desactivado (Admin)",
    description="""
    Reactiva un ítem de menú previamente desactivado estableciendo 'es_activo' a True.

    **Permisos requeridos:**
    - Rol 'Administrador'

    **Respuestas:**
    - 200: Ítem de menú reactivado exitosamente (devuelve el ID y estado).
    - 400: Ítem ya está activo.
    - 403: Acceso denegado (no Admin).
    - 404: Ítem de menú no encontrado.
    - 500: Error interno del servidor.
    """,
    dependencies=[Depends(require_admin)]
)
async def reactivate_menu_endpoint(menu_id: int = Path(..., title="ID del Menú", description="El ID del ítem de menú a reactivar")):
    """
    Endpoint para reactivar un ítem de menú inactivo.

    Args:
        menu_id: Identificador único del ítem de menú a reactivar.

    Returns:
        Dict[str, Any]: Mensaje de confirmación y el estado `es_activo=True`.

    Raises:
        HTTPException: Si no existe (404), error de servicio (CustomException) o error interno (500).
    """
    logger.info(f"Solicitud PUT /menus/{menu_id}/reactivate/ recibida")
    try:
        result = await MenuService.reactivar_menu(menu_id)
        logger.info(f"Menú ID {menu_id} reactivado exitosamente")
        return {"message": f"Menú ID {result.get('menu_id')} reactivado exitosamente.", "menu_id": result.get('menu_id'), "es_activo": result.get('es_activo')}
    except CustomException as ce: # Captura CustomException directamente (puede ser 404, 500)
        logger.warning(f"No se pudo reactivar menú {menu_id}: {ce.detail}")
        raise HTTPException(status_code=ce.status_code, detail=ce.detail)
    except Exception as e:
        logger.exception(f"Error inesperado en endpoint PUT /menus/{menu_id}/reactivate/")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno al reactivar menú.")


# ----------------------------------------------------------------------
# --- Endpoint: Obtener Árbol de Menú por Área (Admin) ---
# ----------------------------------------------------------------------
@router.get(
    "/area/{area_id}/tree/",
    response_model=MenuResponse,
    summary="Obtener árbol de menú para un Área específica (Admin)",
    description="""
    Obtiene la estructura jerárquica completa (activos e inactivos) de los menús 
    pertenecientes a un área específica (módulo, sistema, etc.).

    **Permisos requeridos:**
    - Rol 'Administrador'

    **Respuestas:**
    - 200: Estructura del menú por área devuelta.
    - 403: Acceso denegado (no Admin).
    - 404: Área no encontrada (si el servicio lo valida).
    - 500: Error interno del servidor.
    """,
    dependencies=[Depends(require_admin)]
)
async def get_menu_tree_by_area_endpoint(area_id: int = Path(..., title="ID del Área", description="El ID del área a la que pertenece el menú")):
    """
    Endpoint para obtener el árbol de menú filtrado por el ID del área proporcionado.

    Args:
        area_id: Identificador único del área.

    Returns:
        MenuResponse: Estructura jerárquica del menú del área.

    Raises:
        HTTPException: En caso de error de servicio (CustomException) o error interno (500).
    """
    logger.info(f"Solicitud GET /menus/area/{area_id}/tree/ recibida.")
    try:
        menu_response = await MenuService.obtener_arbol_menu_por_area(area_id)
        # El servicio ya devuelve MenuResponse(menu=[]) si no hay menús
        return menu_response
    except CustomException as ce:
        logger.error(f"Error de servicio al obtener árbol de menú para área {area_id}: {ce.detail}")
        raise HTTPException(status_code=ce.status_code, detail=ce.detail)
    except Exception as e:
        logger.exception(f"Error inesperado en endpoint GET /menus/area/{area_id}/tree/")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno al obtener el árbol de menú del área.")