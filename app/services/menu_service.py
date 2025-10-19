# app/services/menu_service.py

from typing import List, Dict, Optional, Any
import logging

# 🗄️ IMPORTACIONES DE BASE DE DATOS
from app.db.queries import (
    execute_procedure, execute_procedure_params, execute_query, 
    execute_insert, execute_update,
    GET_ALL_MENUS_ADMIN, INSERT_MENU, SELECT_MENU_BY_ID, UPDATE_MENU_TEMPLATE,
    DEACTIVATE_MENU, REACTIVATE_MENU, CHECK_MENU_EXISTS, CHECK_AREA_EXISTS,
    GET_MENUS_BY_AREA_FOR_TREE_QUERY, GET_MAX_ORDEN_FOR_SIBLINGS, GET_MAX_ORDEN_FOR_ROOT
)

# 🚨 EXCEPCIONES - Nuevo sistema de manejo de errores
from app.core.exceptions import (
    ValidationError, NotFoundError, ServiceError, DatabaseError
)

# 🏗️ BASE SERVICE - Clase base para manejo consistente de errores
from app.services.base_service import BaseService

# 📋 SCHEMAS
from app.schemas.menu import (
    MenuResponse, MenuItem, MenuCreate, MenuUpdate, MenuReadSingle
)

# 🔧 UTILIDADES
from app.utils.menu_helper import build_menu_tree

logger = logging.getLogger(__name__)

class MenuService(BaseService):
    """
    Servicio para gestión completa de menús del sistema.
    
    ⚠️ IMPORTANTE: Este servicio maneja operaciones críticas relacionadas con:
    - Estructura jerárquica de menús
    - Permisos y accesos basados en roles
    - Gestión de áreas y su relación con menús
    
    CARACTERÍSTICAS PRINCIPALES:
    - Herencia de BaseService para manejo automático de errores
    - Validaciones de integridad referencial y reglas de negocio
    - Construcción eficiente de árboles de menús
    - Mantenimiento de funcionalidad existente sin cambios
    """

    @staticmethod
    @BaseService.handle_service_errors
    async def get_menu_for_user(usuario_id: int) -> MenuResponse:
        """
        Obtiene la estructura de menú filtrada según los roles y permisos del usuario.
        
        🔐 SEGURIDAD: 
        - Filtra menús basado en los roles y permisos del usuario
        - Construye una estructura jerárquica para el frontend
        - Optimizado para rendimiento con stored procedures
        
        Args:
            usuario_id: ID del usuario autenticado
            
        Returns:
            MenuResponse: Estructura de menú permitida para el usuario
            
        Raises:
            ServiceError: Si hay errores al obtener o procesar el menú
        """
        procedure_name = "sp_GetMenuForUser"
        params_dict = {'UsuarioID': usuario_id}

        logger.info(f"Obteniendo menú filtrado para usuario_id: {usuario_id}")
        
        try:
            # 🗄️ EJECUTAR STORED PROCEDURE
            resultado_sp = execute_procedure_params(procedure_name, params_dict)

            if not resultado_sp:
                logger.info(f"No se encontraron menús permitidos para el usuario ID: {usuario_id}.")
                return MenuResponse(menu=[])

            # 🌳 CONSTRUIR ESTRUCTURA JERÁRQUICA
            menu_tree: List[MenuItem] = build_menu_tree(resultado_sp)
            logger.info(f"Árbol de menú construido para usuario {usuario_id} con {len(menu_tree)} items raíz.")

            return MenuResponse(menu=menu_tree)

        except DatabaseError as db_err:
            logger.error(f"Error de BD al obtener menú para usuario {usuario_id}: {db_err.detail}")
            raise ServiceError(
                status_code=500,
                detail="Error de base de datos al obtener menú del usuario",
                internal_code="MENU_USER_RETRIEVAL_DB_ERROR"
            )
        except Exception as e:
            logger.exception(f"Error inesperado al obtener menú para usuario {usuario_id}: {str(e)}")
            raise ServiceError(
                status_code=500,
                detail="Error interno al procesar el menú del usuario",
                internal_code="MENU_USER_RETRIEVAL_UNEXPECTED_ERROR"
            )

    @staticmethod
    @BaseService.handle_service_errors
    async def obtener_todos_menus_estructurados_admin() -> MenuResponse:
        """
        Obtiene la estructura completa de menús para administración.
        
        📊 VISIÓN COMPLETA:
        - Incluye todos los menús (activos e inactivos)
        - Estructura jerárquica completa
        - Ideal para interfaces de administración
        
        Returns:
            MenuResponse: Estructura completa de menús
            
        Raises:
            ServiceError: Si hay errores al obtener la estructura
        """
        logger.info("Obteniendo estructura completa de menús para admin")
        
        try:
            resultado_sp = execute_procedure(GET_ALL_MENUS_ADMIN)
            
            if not resultado_sp:
                logger.warning(f"{GET_ALL_MENUS_ADMIN} no devolvió resultados.")
                return MenuResponse(menu=[])
            
            menu_tree: List[MenuItem] = build_menu_tree(resultado_sp)
            logger.info(f"Estructura de menú admin construida con {len(menu_tree)} items raíz.")
            
            return MenuResponse(menu=menu_tree)

        except DatabaseError as db_err:
            logger.error(f"Error de BD al obtener estructura admin: {db_err.detail}")
            raise ServiceError(
                status_code=500,
                detail="Error de base de datos al obtener estructura de menús",
                internal_code="MENU_ADMIN_RETRIEVAL_DB_ERROR"
            )
        except Exception as e:
            logger.exception(f"Error inesperado al obtener menús admin: {str(e)}")
            raise ServiceError(
                status_code=500,
                detail="Error interno al procesar estructura de menús",
                internal_code="MENU_ADMIN_RETRIEVAL_UNEXPECTED_ERROR"
            )

    @staticmethod
    @BaseService.handle_service_errors
    async def obtener_menu_por_id(menu_id: int) -> Optional[MenuReadSingle]:
        """
        Obtiene los detalles de un menú específico por su ID.
        
        🔍 DETALLES COMPLETOS:
        - Incluye información del área asociada
        - Valida que el menú exista
        - Útil para operaciones de edición
        
        Args:
            menu_id: ID del menú a buscar
            
        Returns:
            Optional[MenuReadSingle]: Detalles del menú o None si no existe
            
        Raises:
            ServiceError: Si hay errores en la consulta
        """
        logger.debug(f"🔍 Buscando menú con ID: {menu_id}")
        
        try:
            resultado = execute_query(SELECT_MENU_BY_ID, (menu_id,))
            
            if not resultado:
                logger.debug(f"Menú con ID {menu_id} no encontrado.")
                return None

            menu_data = resultado[0]
            return MenuReadSingle(**menu_data)
            
        except DatabaseError as db_err:
            logger.error(f"Error de BD al obtener menú {menu_id}: {db_err.detail}")
            raise ServiceError(
                status_code=500,
                detail="Error de base de datos al obtener menú",
                internal_code="MENU_RETRIEVAL_DB_ERROR"
            )
        except Exception as e:
            logger.exception(f"Error inesperado al obtener menú {menu_id}: {str(e)}")
            raise ServiceError(
                status_code=500,
                detail="Error interno al obtener menú",
                internal_code="MENU_RETRIEVAL_UNEXPECTED_ERROR"
            )

    @staticmethod
    @BaseService.handle_service_errors
    async def crear_menu(menu_data: MenuCreate) -> MenuReadSingle:
        """
        Crea un nuevo menú en el sistema con validaciones completas.
        
        🆕 CREACIÓN SEGURA:
        - Valida existencia del área y menú padre
        - Calcula automáticamente el orden
        - Aplica reglas de negocio para la jerarquía
        
        Args:
            menu_data: Datos validados del menú a crear
            
        Returns:
            MenuReadSingle: Menú creado con todos sus datos
            
        Raises:
            ValidationError: Si los datos son inválidos
            ServiceError: Si la creación falla
        """
        logger.info(f"Intentando crear menú: {menu_data.nombre}")
        
        try:
            # 🚫 VALIDACIONES PREVIAS
            if menu_data.padre_menu_id:
                padre_exists = execute_query(CHECK_MENU_EXISTS, (menu_data.padre_menu_id,))
                if not padre_exists:
                    raise ValidationError(
                        detail=f"El menú padre con ID {menu_data.padre_menu_id} no existe.",
                        internal_code="MENU_PARENT_NOT_FOUND"
                    )
                    
            if not menu_data.area_id:
                raise ValidationError(
                    detail="El ID del área es obligatorio para crear un menú.",
                    internal_code="MENU_AREA_REQUIRED"
                )
            else:
                area_exists = execute_query(CHECK_AREA_EXISTS, (menu_data.area_id,))
                if not area_exists:
                    raise ValidationError(
                        detail=f"El área con ID {menu_data.area_id} no existe.",
                        internal_code="MENU_AREA_NOT_FOUND"
                    )

            # 🧮 CALCULAR ORDEN AUTOMÁTICAMENTE
            max_orden_result = None
            if menu_data.padre_menu_id:
                max_orden_result = execute_query(
                    GET_MAX_ORDEN_FOR_SIBLINGS, 
                    (menu_data.area_id, menu_data.padre_menu_id)
                )
            else:
                max_orden_result = execute_query(
                    GET_MAX_ORDEN_FOR_ROOT, 
                    (menu_data.area_id,)
                )

            max_orden = 0
            if max_orden_result and max_orden_result[0]['max_orden'] is not None:
                max_orden = max_orden_result[0]['max_orden']

            next_orden = max_orden + 1
            logger.debug(f"Calculado next_orden: {next_orden}")

            # 💾 EJECUTAR INSERCIÓN
            params = (
                menu_data.nombre,
                menu_data.icono,
                menu_data.ruta,
                menu_data.padre_menu_id,
                next_orden,
                menu_data.area_id,
                menu_data.es_activo
            )

            resultado = execute_insert(INSERT_MENU, params)
            
            if not resultado or 'menu_id' not in resultado:
                raise ServiceError(
                    status_code=500,
                    detail="La inserción no devolvió el registro creado correctamente.",
                    internal_code="MENU_CREATION_FAILED"
                )

            # 📍 OBTENER NOMBRE DEL ÁREA PARA LA RESPUESTA
            area_nombre = None
            if resultado.get('area_id'):
                area_info = execute_query(
                    "SELECT nombre FROM area_menu WHERE area_id = ?", 
                    (resultado['area_id'],)
                )
                if area_info: 
                    area_nombre = area_info[0]['nombre']

            created_menu = MenuReadSingle(**resultado, area_nombre=area_nombre)
            logger.info(f"Menú '{created_menu.nombre}' creado con ID: {created_menu.menu_id}")
            
            return created_menu

        except (ValidationError, ServiceError):
            raise
        except DatabaseError as db_err:
            logger.error(f"Error de BD al crear menú: {db_err.detail}")
            raise ServiceError(
                status_code=500,
                detail="Error de base de datos al crear menú",
                internal_code="MENU_CREATION_DB_ERROR"
            )
        except Exception as e:
            logger.exception(f"Error inesperado al crear menú: {str(e)}")
            raise ServiceError(
                status_code=500,
                detail="Error interno al crear menú",
                internal_code="MENU_CREATION_UNEXPECTED_ERROR"
            )

    @staticmethod
    @BaseService.handle_service_errors
    async def actualizar_menu(menu_id: int, menu_data: MenuUpdate) -> MenuReadSingle:
        """
        Actualiza un menú existente con validaciones de integridad.
        
        🔄 ACTUALIZACIÓN PARCIAL:
        - Solo actualiza los campos proporcionados
        - Valida relaciones (padre, área)
        - Mantiene la integridad jerárquica
        
        Args:
            menu_id: ID del menú a actualizar
            menu_data: Campos a actualizar (parcial)
            
        Returns:
            MenuReadSingle: Menú actualizado
            
        Raises:
            NotFoundError: Si el menú no existe
            ValidationError: Si los datos son inválidos
            ServiceError: Si la actualización falla
        """
        logger.info(f"Intentando actualizar menú ID: {menu_id}")

        update_payload = menu_data.model_dump(exclude_unset=True)
        
        if not update_payload:
            raise ValidationError(
                detail="No se proporcionaron datos para actualizar.",
                internal_code="MENU_UPDATE_NO_DATA"
            )

        # 🔍 VERIFICAR EXISTENCIA DEL MENÚ
        menu_existente = await MenuService.obtener_menu_por_id(menu_id)
        if not menu_existente:
            raise NotFoundError(
                detail=f"Menú con ID {menu_id} no encontrado para actualizar.",
                internal_code="MENU_NOT_FOUND"
            )

        try:
            # 🚫 VALIDACIONES DE INTEGRIDAD
            if 'padre_menu_id' in update_payload and update_payload['padre_menu_id'] is not None:
                if menu_id == update_payload['padre_menu_id']:
                    raise ValidationError(
                        detail="Un menú no puede ser su propio padre.",
                        internal_code="MENU_SELF_REFERENCE"
                    )
                    
                padre_exists = execute_query(CHECK_MENU_EXISTS, (update_payload['padre_menu_id'],))
                if not padre_exists:
                    raise ValidationError(
                        detail=f"El menú padre con ID {update_payload['padre_menu_id']} no existe.",
                        internal_code="MENU_PARENT_NOT_FOUND"
                    )
                    
            if 'area_id' in update_payload and update_payload['area_id'] is not None:
                area_exists = execute_query(CHECK_AREA_EXISTS, (update_payload['area_id'],))
                if not area_exists:
                    raise ValidationError(
                        detail=f"El área con ID {update_payload['area_id']} no existe.",
                        internal_code="MENU_AREA_NOT_FOUND"
                    )

            # 💾 EJECUTAR ACTUALIZACIÓN
            params = (
                update_payload.get('nombre'),
                update_payload.get('icono'),
                update_payload.get('ruta'),
                update_payload.get('padre_menu_id'),
                update_payload.get('orden'),
                update_payload.get('area_id'),
                update_payload.get('es_activo'),
                menu_id
            )
            
            resultado = execute_update(UPDATE_MENU_TEMPLATE, params)
            
            if not resultado:
                raise ServiceError(
                    status_code=500,
                    detail="La actualización no devolvió el registro actualizado.",
                    internal_code="MENU_UPDATE_FAILED"
                )

            # 📍 OBTENER NOMBRE DEL ÁREA ACTUALIZADO
            area_nombre = None
            if resultado.get('area_id'):
                area_info = execute_query(
                    "SELECT nombre FROM area_menu WHERE area_id = ?", 
                    (resultado['area_id'],)
                )
                if area_info: 
                    area_nombre = area_info[0]['nombre']

            updated_menu = MenuReadSingle(**resultado, area_nombre=area_nombre)
            logger.info(f"Menú ID: {menu_id} actualizado exitosamente.")
            
            return updated_menu

        except (ValidationError, NotFoundError, ServiceError):
            raise
        except DatabaseError as db_err:
            logger.error(f"Error de BD al actualizar menú {menu_id}: {db_err.detail}")
            raise ServiceError(
                status_code=500,
                detail="Error de base de datos al actualizar menú",
                internal_code="MENU_UPDATE_DB_ERROR"
            )
        except Exception as e:
            logger.exception(f"Error inesperado al actualizar menú {menu_id}: {str(e)}")
            raise ServiceError(
                status_code=500,
                detail="Error interno al actualizar menú",
                internal_code="MENU_UPDATE_UNEXPECTED_ERROR"
            )

    @staticmethod
    @BaseService.handle_service_errors
    async def desactivar_menu(menu_id: int) -> Dict[str, Any]:
        """
        Desactiva un menú (borrado lógico).
        
        🚫 DESACTIVACIÓN SEGURA:
        - Verifica que el menú exista y esté activo
        - Realiza desactivación lógica
        - Mantiene integridad referencial
        
        Args:
            menu_id: ID del menú a desactivar
            
        Returns:
            Dict: Resultado de la operación con metadatos
            
        Raises:
            NotFoundError: Si el menú no existe
            ServiceError: Si la desactivación falla
        """
        logger.info(f"Intentando desactivar menú ID: {menu_id}")
        
        try:
            resultado = execute_update(DEACTIVATE_MENU, (menu_id,))
            
            if not resultado:
                # 🔍 VERIFICAR SI EXISTE O YA ESTÁ INACTIVO
                menu_existente = execute_query(CHECK_MENU_EXISTS, (menu_id,))
                if not menu_existente:
                    raise NotFoundError(
                        detail=f"Menú con ID {menu_id} no encontrado para desactivar.",
                        internal_code="MENU_NOT_FOUND"
                    )
                else:
                    raise ValidationError(
                        detail=f"Menú con ID {menu_id} ya estaba inactivo.",
                        internal_code="MENU_ALREADY_INACTIVE"
                    )

            logger.info(f"Menú ID: {menu_id} desactivado exitosamente.")
            return {
                "menu_id": resultado.get('menu_id'), 
                "es_activo": resultado.get('es_activo')
            }

        except (ValidationError, NotFoundError):
            raise
        except DatabaseError as db_err:
            logger.error(f"Error de BD al desactivar menú {menu_id}: {db_err.detail}")
            raise ServiceError(
                status_code=500,
                detail="Error de base de datos al desactivar menú",
                internal_code="MENU_DEACTIVATION_DB_ERROR"
            )
        except Exception as e:
            logger.exception(f"Error inesperado al desactivar menú {menu_id}: {str(e)}")
            raise ServiceError(
                status_code=500,
                detail="Error interno al desactivar menú",
                internal_code="MENU_DEACTIVATION_UNEXPECTED_ERROR"
            )

    @staticmethod
    @BaseService.handle_service_errors
    async def reactivar_menu(menu_id: int) -> Dict[str, Any]:
        """
        Reactiva un menú previamente desactivado.
        
        🔄 REACTIVACIÓN:
        - Verifica que el menú exista y esté inactivo
        - Realiza reactivación lógica
        - Valida estado previo
        
        Args:
            menu_id: ID del menú a reactivar
            
        Returns:
            Dict: Resultado de la operación con metadatos
            
        Raises:
            NotFoundError: Si el menú no existe
            ServiceError: Si la reactivación falla
        """
        logger.info(f"Intentando reactivar menú ID: {menu_id}")
        
        try:
            resultado = execute_update(REACTIVATE_MENU, (menu_id,))
            
            if not resultado:
                raise NotFoundError(
                    detail=f"Menú con ID {menu_id} no encontrado o ya estaba activo.",
                    internal_code="MENU_NOT_FOUND_OR_ACTIVE"
                )

            logger.info(f"Menú ID: {menu_id} reactivado exitosamente.")
            return {
                "menu_id": resultado.get('menu_id'), 
                "es_activo": resultado.get('es_activo')
            }
            
        except (ValidationError, NotFoundError):
            raise
        except DatabaseError as db_err:
            logger.error(f"Error de BD al reactivar menú {menu_id}: {db_err.detail}")
            raise ServiceError(
                status_code=500,
                detail="Error de base de datos al reactivar menú",
                internal_code="MENU_REACTIVATION_DB_ERROR"
            )
        except Exception as e:
            logger.exception(f"Error inesperado al reactivar menú {menu_id}: {str(e)}")
            raise ServiceError(
                status_code=500,
                detail="Error interno al reactivar menú",
                internal_code="MENU_REACTIVATION_UNEXPECTED_ERROR"
            )

    @staticmethod
    @BaseService.handle_service_errors
    async def obtener_arbol_menu_por_area(area_id: int) -> MenuResponse:
        """
        Obtiene la estructura jerárquica de menús para un área específica.
        
        🌳 ÁRBOL POR ÁREA:
        - Filtra menús por área específica
        - Construye estructura jerárquica completa
        - Útil para administración por áreas
        
        Args:
            area_id: ID del área a filtrar
            
        Returns:
            MenuResponse: Estructura de menú del área especificada
            
        Raises:
            ServiceError: Si hay errores al obtener el árbol
        """
        logger.info(f"Obteniendo árbol de menú para area_id: {area_id}")
        
        try:
            params = (area_id,)
            menu_items_raw_list = execute_query(GET_MENUS_BY_AREA_FOR_TREE_QUERY, params)

            if not menu_items_raw_list:
                logger.info(f"No se encontraron menús para el área ID: {area_id}.")
                return MenuResponse(menu=[])

            menu_tree = build_menu_tree(menu_items_raw_list)
            logger.info(f"Árbol de menú del área {area_id} construido con {len(menu_tree)} items raíz.")
            
            return MenuResponse(menu=menu_tree)

        except DatabaseError as db_err:
            logger.error(f"Error de BD al obtener árbol de menú para área {area_id}: {db_err.detail}")
            raise ServiceError(
                status_code=500,
                detail="Error de base de datos al obtener menú del área",
                internal_code="MENU_AREA_RETRIEVAL_DB_ERROR"
            )
        except Exception as e:
            logger.exception(f"Error inesperado al obtener menú del área {area_id}: {str(e)}")
            raise ServiceError(
                status_code=500,
                detail="Error interno al procesar el menú del área",
                internal_code="MENU_AREA_RETRIEVAL_UNEXPECTED_ERROR"
            )