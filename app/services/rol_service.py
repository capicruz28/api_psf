# app/services/rol_service.py
from typing import Dict, List, Optional, Any
import math
import logging
import pyodbc

# 🗄️ IMPORTACIONES DE BASE DE DATOS
from app.db.queries import (
    execute_query, execute_insert, execute_update, execute_transaction,
    COUNT_ROLES_PAGINATED, SELECT_ROLES_PAGINATED,
    DEACTIVATE_ROL, REACTIVATE_ROL,
    SELECT_PERMISOS_POR_ROL, DELETE_PERMISOS_POR_ROL, INSERT_PERMISO_ROL
)

# 📋 SCHEMAS
from app.schemas.rol import (
    RolRead, PaginatedRolResponse, PermisoRead, PermisoUpdatePayload, PermisoBase
)

# 🚨 EXCEPCIONES - Nuevo sistema de manejo de errores
from app.core.exceptions import (
    ValidationError, NotFoundError, ConflictError, ServiceError, DatabaseError
)

# 🏗️ BASE SERVICE - Clase base para manejo consistente de errores
from app.services.base_service import BaseService

logger = logging.getLogger(__name__)

class RolService(BaseService):
    """
    Servicio para gestión completa de roles del sistema.
    
    ⚠️ IMPORTANTE: Este servicio maneja operaciones críticas relacionadas con:
    - Creación, actualización y desactivación de roles
    - Gestión de permisos de roles sobre menús
    - Asignación de roles a usuarios
    
    CARACTERÍSTICAS PRINCIPALES:
    - Herencia de BaseService para manejo automático de errores
    - Validaciones robustas de nombres únicos y relaciones
    - Manejo de transacciones para operaciones críticas
    - Logging detallado para auditoría de seguridad
    """

    @staticmethod
    @BaseService.handle_service_errors
    async def _verificar_nombre_rol_unico(nombre: str, rol_id_excluir: Optional[int] = None) -> None:
        """
        Verifica que el nombre del rol sea único (case-insensitive).
        
        🛡️ PREVENCIÓN DE DUPLICADOS:
        - Evita violaciones de constraints únicos en la base de datos
        - Comparación insensible a mayúsculas/minúsculas
        - Soporte para exclusiones en actualizaciones
        
        Args:
            nombre: Nombre del rol a verificar
            rol_id_excluir: ID del rol a excluir (para actualizaciones)
            
        Raises:
            ConflictError: Si ya existe un rol con el mismo nombre
        """
        try:
            query = "SELECT rol_id FROM rol WHERE LOWER(nombre) = LOWER(?)"
            params = [nombre]
            
            if rol_id_excluir is not None:
                query += " AND rol_id != ?"
                params.append(rol_id_excluir)

            resultados = execute_query(query, tuple(params))

            if resultados:
                raise ConflictError(
                    detail=f"El nombre de rol '{nombre}' ya está en uso.",
                    internal_code="ROLE_NAME_CONFLICT"
                )
                
        except ConflictError:
            raise
        except DatabaseError as db_err:
            logger.error(f"Error de BD en _verificar_nombre_rol_unico: {db_err.detail}")
            raise ServiceError(
                status_code=500,
                detail="Error de base de datos al verificar nombre de rol",
                internal_code="ROLE_NAME_VERIFICATION_DB_ERROR"
            )
        except Exception as e:
            logger.exception(f"Error inesperado en _verificar_nombre_rol_unico: {str(e)}")
            raise ServiceError(
                status_code=500,
                detail="Error interno al verificar nombre de rol",
                internal_code="ROLE_NAME_VERIFICATION_UNEXPECTED_ERROR"
            )

    @staticmethod
    @BaseService.handle_service_errors
    async def crear_rol(rol_data: Dict) -> Dict:
        """
        Crea un nuevo rol en el sistema con validaciones completas.
        
        🆕 CREACIÓN SEGURA:
        - Valida nombre único
        - Aplica valores por defecto seguros
        - Registra la creación para auditoría
        
        Args:
            rol_data: Datos del rol a crear
            
        Returns:
            Dict: Rol creado con todos sus datos
            
        Raises:
            ConflictError: Si el nombre ya existe
            ServiceError: Si la creación falla
        """
        logger.info(f"Intentando crear rol: {rol_data.get('nombre')}")
        
        try:
            nombre_rol = rol_data.get('nombre')
            
            # 🚫 VALIDAR NOMBRE OBLIGATORIO
            if not nombre_rol:
                raise ValidationError(
                    detail="El nombre del rol es requerido.",
                    internal_code="ROLE_NAME_REQUIRED"
                )

            # 🛡️ VERIFICAR NOMBRE ÚNICO
            await RolService._verificar_nombre_rol_unico(nombre_rol)

            # 💾 EJECUTAR INSERCIÓN
            insert_query = """
            INSERT INTO rol (nombre, descripcion, es_activo)
            OUTPUT INSERTED.rol_id, INSERTED.nombre, INSERTED.descripcion,
                   INSERTED.es_activo, INSERTED.fecha_creacion
            VALUES (?, ?, ?)
            """
            
            params = (
                nombre_rol,
                rol_data.get('descripcion'),
                rol_data.get('es_activo', True)  # ✅ Valor por defecto seguro
            )

            result = execute_insert(insert_query, params)

            if not result:
                raise ServiceError(
                    status_code=500,
                    detail="La creación del rol no devolvió resultados.",
                    internal_code="ROLE_CREATION_FAILED"
                )

            logger.info(f"Rol '{result.get('nombre')}' creado con ID: {result.get('rol_id')}")
            return result

        except (ValidationError, ConflictError):
            raise
        except DatabaseError as db_err:
            logger.error(f"Error de BD al crear rol: {db_err.detail}")
            raise ServiceError(
                status_code=500,
                detail="Error de base de datos al crear rol",
                internal_code="ROLE_CREATION_DB_ERROR"
            )
        except Exception as e:
            logger.exception(f"Error inesperado creando rol: {str(e)}")
            raise ServiceError(
                status_code=500,
                detail="Error interno al crear rol",
                internal_code="ROLE_CREATION_UNEXPECTED_ERROR"
            )

    @staticmethod
    @BaseService.handle_service_errors
    async def obtener_rol_por_id(rol_id: int, incluir_inactivos: bool = False) -> Optional[Dict]:
        """
        Obtiene un rol por su ID con opción de incluir inactivos.
        
        🔍 BÚSQUEDA FLEXIBLE:
        - Por defecto solo retorna roles activos
        - Opción para incluir roles inactivos (admin)
        - Conversión automática de tipos de datos
        
        Args:
            rol_id: ID del rol a buscar
            incluir_inactivos: Si incluir roles inactivos
            
        Returns:
            Optional[Dict]: Datos del rol o None si no existe
        """
        try:
            query = """
            SELECT rol_id, nombre, descripcion, es_activo, fecha_creacion
            FROM rol
            WHERE rol_id = ?
            """
            params = [rol_id]
            
            if not incluir_inactivos:
                query += " AND es_activo = 1"

            resultados = execute_query(query, tuple(params))

            if not resultados:
                logger.debug(f"Rol con ID {rol_id} no encontrado")
                return None

            # 🔄 CONVERTIR TIPOS DE DATOS
            rol = resultados[0]
            if 'es_activo' in rol and isinstance(rol['es_activo'], int):
                rol['es_activo'] = bool(rol['es_activo'])
                
            return rol

        except DatabaseError as db_err:
            logger.error(f"Error de BD al obtener rol {rol_id}: {db_err.detail}")
            raise ServiceError(
                status_code=500,
                detail="Error de base de datos al obtener rol",
                internal_code="ROLE_RETRIEVAL_DB_ERROR"
            )
        except Exception as e:
            logger.exception(f"Error inesperado obteniendo rol {rol_id}: {str(e)}")
            raise ServiceError(
                status_code=500,
                detail="Error interno al obtener rol",
                internal_code="ROLE_RETRIEVAL_UNEXPECTED_ERROR"
            )

    @staticmethod
    @BaseService.handle_service_errors
    async def obtener_roles_paginados(
        page: int = 1,
        limit: int = 10,
        search: Optional[str] = None
    ) -> Dict:
        """
        Obtiene una lista paginada de roles con búsqueda.
        
        📊 PAGINACIÓN EFICIENTE:
        - Búsqueda insensible en nombre y descripción
        - Metadatos completos de paginación
        - Ordenamiento consistente
        
        Args:
            page: Número de página (comienza en 1)
            limit: Límite de resultados por página
            search: Término de búsqueda opcional
            
        Returns:
            Dict: Respuesta paginada con roles y metadatos
            
        Raises:
            ValidationError: Si los parámetros son inválidos
            ServiceError: Si hay errores en la consulta
        """
        logger.info(f"Obteniendo roles paginados: page={page}, limit={limit}, search='{search}'")

        # 🚫 VALIDAR PARÁMETROS
        if page < 1:
            raise ValidationError(
                detail="El número de página debe ser mayor o igual a 1.",
                internal_code="INVALID_PAGE_NUMBER"
            )
        if limit < 1:
            raise ValidationError(
                detail="El límite por página debe ser mayor o igual a 0.",
                internal_code="INVALID_LIMIT"
            )

        offset = (page - 1) * limit
        search_param = f"%{search}%" if search else None
        
        count_params = (search_param, search_param, search_param)
        select_params = (search_param, search_param, search_param, offset, limit)

        try:
            # 📊 CONTAR TOTAL DE ROLES
            logger.debug(f"Contando roles con parámetros: {count_params}")
            count_result = execute_query(COUNT_ROLES_PAGINATED, count_params)

            if not count_result or not isinstance(count_result, list) or len(count_result) == 0:
                logger.error(f"Error al contar roles: resultado inesperado: {count_result}")
                raise ServiceError(
                    status_code=500,
                    detail="Error al obtener el total de roles",
                    internal_code="ROLE_COUNT_ERROR"
                )

            total_roles = count_result[0]['total']
            logger.debug(f"Total de roles encontrados: {total_roles}")

            # 📋 OBTENER ROLES PAGINADOS
            lista_roles = []
            if total_roles > 0 and limit > 0:
                logger.debug(f"Obteniendo roles con parámetros: {select_params}")
                lista_roles = execute_query(SELECT_ROLES_PAGINATED, select_params)
                logger.debug(f"Obtenidos {len(lista_roles)} roles para la página {page}")

            # 🔄 PROCESAR Y CONVERTIR DATOS
            roles_procesados = []
            for rol_dict in lista_roles:
                if 'es_activo' in rol_dict and isinstance(rol_dict['es_activo'], int):
                    rol_dict['es_activo'] = bool(rol_dict['es_activo'])
                roles_procesados.append(rol_dict)

            # 🧮 CALCULAR METADATOS
            total_paginas = math.ceil(total_roles / limit) if limit > 0 else 0

            response_data = {
                "roles": roles_procesados,
                "total_roles": total_roles,
                "pagina_actual": page,
                "total_paginas": total_paginas
            }

            logger.info(f"Obtención paginada de roles completada exitosamente")
            return response_data

        except (ValidationError, ServiceError):
            raise
        except DatabaseError as db_err:
            logger.error(f"Error de BD en obtener_roles_paginados: {db_err.detail}")
            raise ServiceError(
                status_code=500,
                detail="Error de base de datos al obtener roles paginados",
                internal_code="ROLE_PAGINATION_DB_ERROR"
            )
        except Exception as e:
            logger.exception(f"Error inesperado en obtener_roles_paginados: {str(e)}")
            raise ServiceError(
                status_code=500,
                detail="Error interno al obtener roles paginados",
                internal_code="ROLE_PAGINATION_UNEXPECTED_ERROR"
            )

    @staticmethod
    @BaseService.handle_service_errors
    async def actualizar_rol(rol_id: int, rol_data: Dict) -> Dict:
        """
        Actualiza un rol existente con validaciones de integridad.
        
        🔄 ACTUALIZACIÓN PARCIAL:
        - Solo actualiza campos proporcionados
        - Valida nombre único (si se cambia)
        - Mantiene la integridad de los datos
        
        Args:
            rol_id: ID del rol a actualizar
            rol_data: Campos a actualizar (parcial)
            
        Returns:
            Dict: Rol actualizado
            
        Raises:
            NotFoundError: Si el rol no existe
            ConflictError: Si el nuevo nombre ya existe
            ServiceError: Si la actualización falla
        """
        logger.info(f"Intentando actualizar rol ID: {rol_id}")

        try:
            # 🔍 VERIFICAR EXISTENCIA DEL ROL
            rol_actual = await RolService.obtener_rol_por_id(rol_id, incluir_inactivos=True)
            if not rol_actual:
                raise NotFoundError(
                    detail=f"Rol con ID {rol_id} no encontrado.",
                    internal_code="ROLE_NOT_FOUND"
                )

            # 🛡️ VALIDAR NOMBRE ÚNICO (si se cambia)
            nuevo_nombre = rol_data.get('nombre')
            if nuevo_nombre and nuevo_nombre != rol_actual.get('nombre'):
                await RolService._verificar_nombre_rol_unico(nuevo_nombre, rol_id)

            # 🛠️ CONSTRUIR ACTUALIZACIÓN DINÁMICA
            update_parts = []
            params = []
            campos_actualizados = False

            campos_permitidos = {
                'nombre': 'nombre', 
                'descripcion': 'descripcion', 
                'es_activo': 'es_activo'
            }

            for field, db_field in campos_permitidos.items():
                if field in rol_data and rol_data[field] is not None:
                    # 🔄 Solo actualizar si es diferente (excepto para es_activo)
                    if field != 'es_activo' or rol_data[field] != rol_actual.get(field):
                        update_parts.append(f"{db_field} = ?")
                        params.append(rol_data[field])
                        campos_actualizados = True

            if not campos_actualizados:
                logger.info(f"No hay cambios detectados para el rol ID {rol_id}")
                return rol_actual

            params.append(rol_id)

            # 💾 EJECUTAR ACTUALIZACIÓN
            update_query = f"""
            UPDATE rol
            SET {', '.join(update_parts)}
            OUTPUT INSERTED.rol_id, INSERTED.nombre, INSERTED.descripcion,
                   INSERTED.es_activo, INSERTED.fecha_creacion
            WHERE rol_id = ?
            """

            result = execute_update(update_query, tuple(params))

            if not result:
                logger.error(f"La actualización del rol ID {rol_id} no devolvió resultados")
                raise ServiceError(
                    status_code=500,
                    detail="Error al actualizar el rol",
                    internal_code="ROLE_UPDATE_FAILED"
                )

            # 🔄 CONVERTIR TIPOS DE DATOS
            if 'es_activo' in result and isinstance(result['es_activo'], int):
                result['es_activo'] = bool(result['es_activo'])
                
            logger.info(f"Rol '{result.get('nombre')}' actualizado exitosamente")
            return result

        except (ValidationError, NotFoundError, ConflictError):
            raise
        except DatabaseError as db_err:
            logger.error(f"Error de BD al actualizar rol {rol_id}: {db_err.detail}")
            raise ServiceError(
                status_code=500,
                detail="Error de base de datos al actualizar rol",
                internal_code="ROLE_UPDATE_DB_ERROR"
            )
        except Exception as e:
            logger.exception(f"Error inesperado actualizando rol {rol_id}: {str(e)}")
            raise ServiceError(
                status_code=500,
                detail="Error interno al actualizar rol",
                internal_code="ROLE_UPDATE_UNEXPECTED_ERROR"
            )

    @staticmethod
    @BaseService.handle_service_errors
    async def desactivar_rol(rol_id: int) -> Dict:
        """
        Desactiva un rol (borrado lógico).
        
        🚫 DESACTIVACIÓN SEGURA:
        - Verifica que el rol exista y esté activo
        - Evita operaciones redundantes
        - Mantiene integridad referencial
        
        Args:
            rol_id: ID del rol a desactivar
            
        Returns:
            Dict: Rol desactivado
            
        Raises:
            NotFoundError: Si el rol no existe
            ValidationError: Si el rol ya está inactivo
            ServiceError: Si la desactivación falla
        """
        logger.info(f"Intentando desactivar rol ID: {rol_id}")

        try:
            # 🔍 VERIFICAR EXISTENCIA Y ESTADO
            rol_actual = await RolService.obtener_rol_por_id(rol_id, incluir_inactivos=True)
            if not rol_actual:
                raise NotFoundError(
                    detail=f"Rol con ID {rol_id} no encontrado.",
                    internal_code="ROLE_NOT_FOUND"
                )
                
            if not rol_actual.get('es_activo', False):
                logger.info(f"Rol ID {rol_id} ya se encontraba inactivo")
                return rol_actual

            # 💾 EJECUTAR DESACTIVACIÓN
            result = execute_update(DEACTIVATE_ROL, (rol_id,))

            if not result:
                logger.warning(f"No se pudo desactivar el rol ID {rol_id}")
                # 🔄 VERIFICAR ESTADO ACTUAL
                rol_revisado = await RolService.obtener_rol_por_id(rol_id, incluir_inactivos=True)
                if rol_revisado and not rol_revisado.get('es_activo'):
                    return rol_revisado
                    
                raise ServiceError(
                    status_code=500,
                    detail="Error al desactivar el rol",
                    internal_code="ROLE_DEACTIVATION_FAILED"
                )

            # 🔄 CONVERTIR TIPOS DE DATOS
            if 'es_activo' in result and isinstance(result['es_activo'], int):
                result['es_activo'] = bool(result['es_activo'])
                
            logger.info(f"Rol ID {rol_id} desactivado exitosamente")
            return result

        except (ValidationError, NotFoundError):
            raise
        except DatabaseError as db_err:
            logger.error(f"Error de BD al desactivar rol {rol_id}: {db_err.detail}")
            raise ServiceError(
                status_code=500,
                detail="Error de base de datos al desactivar rol",
                internal_code="ROLE_DEACTIVATION_DB_ERROR"
            )
        except Exception as e:
            logger.exception(f"Error inesperado desactivando rol {rol_id}: {str(e)}")
            raise ServiceError(
                status_code=500,
                detail="Error interno al desactivar rol",
                internal_code="ROLE_DEACTIVATION_UNEXPECTED_ERROR"
            )

    @staticmethod
    @BaseService.handle_service_errors
    async def reactivar_rol(rol_id: int) -> Dict:
        """
        Reactiva un rol previamente desactivado.
        
        🔄 REACTIVACIÓN SEGURA:
        - Verifica que el rol exista y esté inactivo
        - Evita operaciones redundantes
        - Mantiene la trazabilidad
        
        Args:
            rol_id: ID del rol a reactivar
            
        Returns:
            Dict: Rol reactivado
            
        Raises:
            NotFoundError: Si el rol no existe
            ValidationError: Si el rol ya está activo
            ServiceError: Si la reactivación falla
        """
        logger.info(f"Intentando reactivar rol ID: {rol_id}")

        try:
            # 🔍 VERIFICAR EXISTENCIA Y ESTADO
            rol_actual = await RolService.obtener_rol_por_id(rol_id, incluir_inactivos=True)
            if not rol_actual:
                raise NotFoundError(
                    detail=f"Rol con ID {rol_id} no encontrado.",
                    internal_code="ROLE_NOT_FOUND"
                )
                
            if rol_actual.get('es_activo', False):
                logger.info(f"Rol ID {rol_id} ya se encontraba activo")
                return rol_actual

            # 💾 EJECUTAR REACTIVACIÓN
            result = execute_update(REACTIVATE_ROL, (rol_id,))

            if not result:
                logger.warning(f"No se pudo reactivar el rol ID {rol_id}")
                # 🔄 VERIFICAR ESTADO ACTUAL
                rol_revisado = await RolService.obtener_rol_por_id(rol_id, incluir_inactivos=True)
                if rol_revisado and rol_revisado.get('es_activo'):
                    return rol_revisado
                    
                raise ServiceError(
                    status_code=500,
                    detail="Error al reactivar el rol",
                    internal_code="ROLE_REACTIVATION_FAILED"
                )

            # 🔄 CONVERTIR TIPOS DE DATOS
            if 'es_activo' in result and isinstance(result['es_activo'], int):
                result['es_activo'] = bool(result['es_activo'])
                
            logger.info(f"Rol ID {rol_id} reactivado exitosamente")
            return result

        except (ValidationError, NotFoundError):
            raise
        except DatabaseError as db_err:
            logger.error(f"Error de BD al reactivar rol {rol_id}: {db_err.detail}")
            raise ServiceError(
                status_code=500,
                detail="Error de base de datos al reactivar rol",
                internal_code="ROLE_REACTIVATION_DB_ERROR"
            )
        except Exception as e:
            logger.exception(f"Error inesperado reactivando rol {rol_id}: {str(e)}")
            raise ServiceError(
                status_code=500,
                detail="Error interno al reactivar rol",
                internal_code="ROLE_REACTIVATION_UNEXPECTED_ERROR"
            )

    @staticmethod
    @BaseService.handle_service_errors
    async def get_all_active_roles() -> List[Dict]:
        """
        Obtiene todos los roles activos (sin paginación).
        
        📋 LISTA COMPLETA:
        - Optimizado para listas desplegables
        - Ordenado por nombre
        - Solo roles activos
        
        Returns:
            List[Dict]: Lista de roles activos
            
        Raises:
            ServiceError: Si hay errores en la consulta
        """
        logger.debug("📋 Obteniendo todos los roles activos")
        
        query = """
            SELECT rol_id, nombre, descripcion, es_activo, fecha_creacion
            FROM rol
            WHERE es_activo = 1
            ORDER BY nombre ASC;
        """
        
        try:
            resultados = execute_query(query)
            
            roles_procesados = []
            for rol_dict in resultados:
                if 'es_activo' in rol_dict and isinstance(rol_dict['es_activo'], int):
                    rol_dict['es_activo'] = bool(rol_dict['es_activo'])
                roles_procesados.append(rol_dict)

            logger.info(f"Se encontraron {len(roles_procesados)} roles activos")
            return roles_procesados

        except DatabaseError as db_err:
            logger.error(f"Error de BD en get_all_active_roles: {db_err.detail}")
            raise ServiceError(
                status_code=500,
                detail="Error de base de datos al obtener roles activos",
                internal_code="ACTIVE_ROLES_RETRIEVAL_DB_ERROR"
            )
        except Exception as e:
            logger.exception(f"Error inesperado en get_all_active_roles: {str(e)}")
            raise ServiceError(
                status_code=500,
                detail="Error interno al obtener roles activos",
                internal_code="ACTIVE_ROLES_RETRIEVAL_UNEXPECTED_ERROR"
            )

    @staticmethod
    @BaseService.handle_service_errors
    async def obtener_permisos_por_rol(rol_id: int) -> List[PermisoRead]:
        """
        Obtiene todos los permisos asignados a un rol específico.
        
        🔐 GESTIÓN DE PERMISOS:
        - Lista completa de permisos del rol
        - Incluye detalles de menús asociados
        - Validación de existencia del rol
        
        Args:
            rol_id: ID del rol cuyos permisos se quieren obtener
            
        Returns:
            List[PermisoRead]: Lista de permisos del rol
            
        Raises:
            NotFoundError: Si el rol no existe
            ServiceError: Si hay errores en la consulta
        """
        logger.info(f"Obteniendo permisos para el rol ID: {rol_id}")

        # 🔍 VERIFICAR EXISTENCIA DEL ROL
        rol_existente = await RolService.obtener_rol_por_id(rol_id)
        if not rol_existente:
            raise NotFoundError(
                detail=f"Rol con ID {rol_id} no encontrado.",
                internal_code="ROLE_NOT_FOUND"
            )

        try:
            resultados = execute_query(SELECT_PERMISOS_POR_ROL, (rol_id,))
            
            if not resultados:
                logger.info(f"El rol ID {rol_id} no tiene permisos asignados")
                return []

            permisos = [PermisoRead(**dict(row)) for row in resultados]
            logger.info(f"Se encontraron {len(permisos)} permisos para el rol ID: {rol_id}")
            
            return permisos

        except DatabaseError as db_err:
            logger.error(f"Error de BD al obtener permisos para rol {rol_id}: {db_err.detail}")
            raise ServiceError(
                status_code=500,
                detail="Error de base de datos al obtener permisos",
                internal_code="ROLE_PERMISSIONS_RETRIEVAL_DB_ERROR"
            )
        except Exception as e:
            logger.exception(f"Error inesperado al obtener permisos para rol {rol_id}: {e}")
            raise ServiceError(
                status_code=500,
                detail="Error interno al obtener permisos",
                internal_code="ROLE_PERMISSIONS_RETRIEVAL_UNEXPECTED_ERROR"
            )

    @staticmethod
    @BaseService.handle_service_errors
    async def actualizar_permisos_rol(rol_id: int, permisos_payload: PermisoUpdatePayload) -> None:
        """
        Actualiza TODOS los permisos de un rol en una transacción atómica.
        
        🔄 ACTUALIZACIÓN ATÓMICA:
        - Elimina permisos existentes
        - Inserta nuevos permisos
        - Transacción para garantizar consistencia
        
        Args:
            rol_id: ID del rol a actualizar
            permisos_payload: Payload con la nueva lista de permisos
            
        Raises:
            NotFoundError: Si el rol no existe
            ServiceError: Si la transacción falla
        """
        logger.info(f"Actualizando permisos para el rol ID: {rol_id}")

        # 🔍 VERIFICAR EXISTENCIA DEL ROL
        rol_existente = await RolService.obtener_rol_por_id(rol_id)
        if not rol_existente:
            raise NotFoundError(
                detail=f"Rol con ID {rol_id} no encontrado.",
                internal_code="ROLE_NOT_FOUND"
            )

        nuevos_permisos: List[PermisoBase] = permisos_payload.permisos
        logger.debug(f"Se actualizarán {len(nuevos_permisos)} permisos para el rol {rol_id}")

        # 🏗️ DEFINIR OPERACIONES DE TRANSACCIÓN
        def _operaciones_permisos(cursor: pyodbc.Cursor):
            # 🗑️ ELIMINAR PERMISOS EXISTENTES
            logger.debug(f"Eliminando permisos existentes para rol {rol_id}")
            cursor.execute(DELETE_PERMISOS_POR_ROL, (rol_id,))
            logger.debug(f"Permisos existentes eliminados para rol {rol_id}")

            # ➕ INSERTAR NUEVOS PERMISOS
            if nuevos_permisos:
                logger.debug(f"Insertando {len(nuevos_permisos)} nuevos permisos")
                insert_count = 0
                for permiso in nuevos_permisos:
                    params = (
                        rol_id, 
                        permiso.menu_id, 
                        permiso.puede_ver, 
                        permiso.puede_editar, 
                        permiso.puede_eliminar
                    )
                    cursor.execute(INSERT_PERMISO_ROL, params)
                    insert_count += 1
                logger.debug(f"Insertados {insert_count} permisos para rol {rol_id}")
            else:
                logger.debug(f"No hay nuevos permisos para insertar para rol {rol_id}")

        try:
            # 💾 EJECUTAR TRANSACCIÓN
            execute_transaction(_operaciones_permisos)
            logger.info(f"Permisos actualizados exitosamente para el rol ID: {rol_id}")

        except DatabaseError as db_err:
            logger.error(f"Error de BD en actualizar_permisos_rol: {db_err.detail}")
            raise ServiceError(
                status_code=500,
                detail="Error de base de datos al actualizar permisos",
                internal_code="ROLE_PERMISSIONS_UPDATE_DB_ERROR"
            )
        except Exception as e:
            logger.exception(f"Error inesperado en actualizar_permisos_rol: {e}")
            raise ServiceError(
                status_code=500,
                detail="Error interno al actualizar permisos",
                internal_code="ROLE_PERMISSIONS_UPDATE_UNEXPECTED_ERROR"
            )