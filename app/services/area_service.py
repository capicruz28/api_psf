# app/services/area_service.py
from typing import List, Optional, Dict, Any
import math
import logging

# 🗄️ IMPORTACIONES DE BASE DE DATOS - Mantener compatibilidad con queries existentes
from app.db.queries import (
    execute_query, execute_insert, execute_update,
    GET_AREAS_PAGINATED_QUERY, COUNT_AREAS_QUERY, GET_AREA_BY_ID_QUERY,
    CHECK_AREA_EXISTS_BY_NAME_QUERY, CREATE_AREA_QUERY,
    UPDATE_AREA_BASE_QUERY_TEMPLATE, TOGGLE_AREA_STATUS_QUERY, 
    GET_ACTIVE_AREAS_SIMPLE_LIST_QUERY
)

# 📋 SCHEMAS - Mantener estructura de datos existente
from app.schemas.area import AreaCreate, AreaUpdate, AreaRead, PaginatedAreaResponse, AreaSimpleList

# 🚨 EXCEPCIONES - Nuevo sistema de manejo de errores
from app.core.exceptions import ValidationError, NotFoundError, ConflictError, DatabaseError, ServiceError

# 🏗️ BASE SERVICE - Nueva clase base para manejo consistente de errores
from app.services.base_service import BaseService

logger = logging.getLogger(__name__)

class AreaService(BaseService):
    """
    Servicio para gestión de áreas del sistema.
    
    ⚠️ IMPORTANTE: Esta clase maneja todas las operaciones relacionadas con áreas
    manteniendo la integridad de los datos y aplicando las reglas de negocio.
    
    CARACTERÍSTICAS PRINCIPALES:
    - Herencia de BaseService para manejo automático de errores
    - Validaciones consistentes usando el nuevo sistema de excepciones
    - Logging detallado para auditoría y debugging
    - Mantenimiento de funcionalidad existente sin cambios
    """

    @staticmethod
    async def _verificar_nombre_existente(nombre: str, excluir_id: Optional[int] = None) -> bool:
        """
        Verifica si ya existe un área con el mismo nombre (case-insensitive).
        
        🔍 PROPÓSITO: Prevenir duplicados en la base de datos que violarían
        constraints únicos y causarían errores de integridad.
        
        Args:
            nombre: Nombre del área a verificar
            excluir_id: ID de área a excluir (útil en actualizaciones)
            
        Returns:
            bool: True si ya existe un área con ese nombre, False en caso contrario
            
        🛡️ SEGURIDAD: Este método es interno y no expone detalles de errores de BD
        """
        id_a_excluir = excluir_id if excluir_id is not None else -1
        params = (nombre.lower(), id_a_excluir)
        
        try:
            # 🗃️ CONSULTA A BD: Verificar existencia sin exponer detalles internos
            resultado_lista = execute_query(CHECK_AREA_EXISTS_BY_NAME_QUERY, params)
            
            if resultado_lista:
                return resultado_lista[0].get('count', 0) > 0
            return False
            
        except KeyError:
            # 🔧 ERROR DE ESTRUCTURA: La consulta no devolvió el campo esperado
            logger.error("Error al acceder a la clave 'count' en CHECK_AREA_EXISTS_BY_NAME_QUERY")
            raise DatabaseError(
                detail="Error interno al verificar nombre de área",
                internal_code="DB_QUERY_ERROR"
            )

    @staticmethod
    @BaseService.handle_service_errors
    async def crear_area(area_data: AreaCreate) -> AreaRead:
        """
        Crea una nueva área en el sistema.
        
        📝 FLUJO PRINCIPAL:
        1. Validar que el nombre no exista (prevenir duplicados)
        2. Insertar en base de datos
        3. Retornar el área creada
        
        Args:
            area_data: Datos validados del área a crear
            
        Returns:
            AreaRead: El área creada con todos sus datos
            
        Raises:
            ConflictError: Si ya existe un área con el mismo nombre
            ServiceError: Si la inserción falla por razones internas
        """
        logger.info(f"Iniciando creación de área: {area_data.nombre}")
        
        # 🚫 VALIDACIÓN DE NEGOCIO: Prevenir nombres duplicados
        if await AreaService._verificar_nombre_existente(area_data.nombre):
            raise ConflictError(
                detail=f"Ya existe un área con el nombre '{area_data.nombre}'.",
                internal_code="AREA_NAME_CONFLICT"
            )

        # 🗃️ PREPARAR DATOS PARA INSERCIÓN
        params = (
            area_data.nombre,
            area_data.descripcion,
            area_data.icono,
            area_data.es_activo
        )
        
        # 💾 EJECUTAR INSERCIÓN EN BD
        resultado_insert = execute_insert(CREATE_AREA_QUERY, params)
        
        # 🔍 VERIFICAR RESULTADO DE INSERCIÓN
        if not resultado_insert:
            raise ServiceError(
                status_code=500,
                detail="La inserción del área no devolvió el registro creado.",
                internal_code="AREA_CREATION_FAILED"
            )

        # ✅ CONVERSIÓN Y LOG DE ÉXITO
        created_area = AreaRead(**resultado_insert)
        logger.info(f"Área '{created_area.nombre}' creada con ID: {created_area.area_id}")
        return created_area

    @staticmethod
    @BaseService.handle_service_errors
    async def obtener_area_por_id(area_id: int) -> Optional[AreaRead]:
        """
        Obtiene un área específica por su ID.
        
        🔍 CARACTERÍSTICAS:
        - Retorna None si el área no existe (no lanza excepción)
        - Útil para verificaciones de existencia sin interrumpir flujo
        
        Args:
            area_id: ID del área a buscar
            
        Returns:
            Optional[AreaRead]: El área encontrada o None si no existe
        """
        logger.debug(f"Buscando área con ID: {area_id}")
        
        # 🗃️ CONSULTA SIMPLE POR ID
        resultado_lista = execute_query(GET_AREA_BY_ID_QUERY, (area_id,))
        
        if not resultado_lista:
            logger.debug(f"Área con ID {area_id} no encontrada.")
            return None
            
        # ✅ CONVERSIÓN A SCHEMA PYDANTIC
        return AreaRead(**resultado_lista[0])

    @staticmethod
    @BaseService.handle_service_errors
    async def obtener_areas_paginadas(
        skip: int = 0,
        limit: int = 10,
        search: Optional[str] = None
    ) -> PaginatedAreaResponse:
        """
        Obtiene una lista paginada y filtrada de áreas.
        
        📊 PAGINACIÓN EFICIENTE COMPATIBLE:
        - Maneja diferencias entre drivers SQL Server (ODBC 17 vs Native Client 10.0)
        - Consultas optimizadas sin parámetros NULL para búsquedas vacías
        - Realiza conteo y paginación eficientes
        
        Args:
            skip: Número de registros a saltar (offset)
            limit: Número máximo de registros por página
            search: Término de búsqueda opcional
            
        Returns:
            PaginatedAreaResponse: Respuesta con datos paginados y metadatos
        """
        logger.info(f"Obteniendo áreas paginadas: skip={skip}, limit={limit}, search='{search}'")
        
        # 🔍 ESTRATEGIA COMPATIBLE CON TODOS LOS DRIVERS
        # SQL Server Native Client 10.0 tiene problemas con parámetros NULL en LIKE
        if search and search.strip():
            # CASO CON BÚSQUEDA: Usar consultas con parámetros
            search = search.strip()
            search_param = f"%{search}%"
            where_params = (search, search_param, search_param)
            
            # Usar consultas originales con filtro
            count_query = COUNT_AREAS_QUERY
            paginated_query = GET_AREAS_PAGINATED_QUERY
            use_search = True
        else:
            # CASO SIN BÚSQUEDA: Usar consultas simplificadas sin filtro WHERE
            # Esto evita problemas con parámetros NULL en drivers antiguos
            where_params = ()
            count_query = """
                SELECT COUNT(*) as total_count 
                FROM area_menu
            """
            paginated_query = """
                SELECT area_id, nombre, descripcion, icono, es_activo, fecha_creacion
                FROM area_menu
                ORDER BY area_id ASC
                OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
            """
            use_search = False

        try:
            # 1. 📊 OBTENER CONTEO TOTAL
            if use_search:
                count_result_list = execute_query(count_query, where_params)
            else:
                count_result_list = execute_query(count_query)
            
            total_count = count_result_list[0].get('total_count', 0) if count_result_list else 0
            
            # 2. 📋 OBTENER DATOS PAGINADOS (solo si hay resultados)
            areas_lista: List[AreaRead] = []
            if total_count > 0 and limit > 0:
                if use_search:
                    # Con búsqueda: agregar skip y limit a los parámetros existentes
                    pagination_params = where_params + (skip, limit)
                else:
                    # Sin búsqueda: solo skip y limit
                    pagination_params = (skip, limit)
                
                rows = execute_query(paginated_query, pagination_params)
                
                # 🎯 MAPEAR RESULTADOS CON MANEJO DE ERRORES INDIVIDUALES
                for row_dict in rows:
                    try:
                        # Validar y limpiar datos antes de crear el objeto
                        cleaned_row = {
                            key: (value if value is not None else None)
                            for key, value in row_dict.items()
                        }
                        areas_lista.append(AreaRead(**cleaned_row))
                    except Exception as map_err:
                        logger.warning(f"Error mapeando área, omitiendo registro: {map_err}")
                        # 🔄 CONTINUAR: No fallar toda la operación por un registro corrupto
                        continue

            # 3. 🧮 CALCULAR METADATOS DE PAGINACIÓN
            total_pages = math.ceil(total_count / limit) if limit > 0 else 0
            current_page = (skip // limit) + 1 if limit > 0 else 1

            logger.info(
                f"Paginación completada: {len(areas_lista)} áreas de {total_count} totales, "
                f"Página {current_page} de {total_pages}"
            )
            
            return PaginatedAreaResponse(
                areas=areas_lista,
                total_areas=total_count,
                pagina_actual=current_page,
                total_paginas=total_pages
            )
            
        except Exception as e:
            logger.error(f"Error en paginación: {str(e)}", exc_info=True)
            # En caso de error, devolver respuesta vacía pero estructurada
            return PaginatedAreaResponse(
                areas=[],
                total_areas=0,
                pagina_actual=1,
                total_paginas=0
            )

    @staticmethod
    @BaseService.handle_service_errors
    async def actualizar_area(area_id: int, area_data: AreaUpdate) -> AreaRead:
        """
        Actualiza un área existente con validaciones de negocio.
        
        🔄 FLUJO DE ACTUALIZACIÓN:
        1. Verificar que el área existe
        2. Validar que el nuevo nombre no cause conflictos
        3. Aplicar actualización parcial (solo campos proporcionados)
        4. Retornar área actualizada
        
        Args:
            area_id: ID del área a actualizar
            area_data: Campos a actualizar (parcial)
            
        Returns:
            AreaRead: El área actualizada
            
        Raises:
            NotFoundError: Si el área no existe
            ConflictError: Si el nuevo nombre ya está en uso
            ValidationError: Si no se proporcionan datos para actualizar
        """
        logger.info(f"Intentando actualizar área ID: {area_id}")

        # 🚫 VALIDACIÓN: Debe haber datos para actualizar
        update_payload = area_data.model_dump(exclude_unset=True)
        if not update_payload:
            raise ValidationError(
                detail="No se proporcionaron datos para actualizar el área.",
                internal_code="NO_UPDATE_DATA"
            )

        # 🔍 VERIFICAR EXISTENCIA DEL ÁREA
        area_existente = await AreaService.obtener_area_por_id(area_id)
        if not area_existente:
            raise NotFoundError(
                detail=f"Área con ID {area_id} no encontrada para actualizar.",
                internal_code="AREA_NOT_FOUND"
            )

        # 🚫 VALIDACIÓN DE NOMBRE ÚNICO (si se está cambiando)
        if 'nombre' in update_payload and update_payload['nombre'].lower() != area_existente.nombre.lower():
            if await AreaService._verificar_nombre_existente(update_payload['nombre'], excluir_id=area_id):
                raise ConflictError(
                    detail=f"Ya existe otra área con el nombre '{update_payload['nombre']}'.",
                    internal_code="AREA_NAME_CONFLICT"
                )

        # 🛠️ CONSTRUIR QUERY DINÁMICA (solo campos proporcionados)
        fields_to_update = []
        params_list = []
        for key, value in update_payload.items():
            fields_to_update.append(f"{key} = ?")
            params_list.append(value)

        # 💾 EJECUTAR ACTUALIZACIÓN
        params_list.append(area_id)
        update_query = UPDATE_AREA_BASE_QUERY_TEMPLATE.format(fields=", ".join(fields_to_update))
        resultado_update = execute_update(update_query, tuple(params_list))
        
        # 🔄 FALLBACK: Si no retorna datos, obtener el área actualizada
        if not resultado_update:
            logger.warning(f"execute_update no devolvió datos para área {area_id}. Usando fallback.")
            updated_area = await AreaService.obtener_area_por_id(area_id)
            if not updated_area:
                raise ServiceError(
                    status_code=500,
                    detail="Error crítico: Área actualizada pero no se pudo recuperar.",
                    internal_code="AREA_UPDATE_RETRIEVAL_FAILED"
                )
            logger.info(f"Área ID: {area_id} actualizada (verificada post-actualización)")
            return updated_area
            
        # ✅ ÉXITO: Retornar datos de la actualización
        logger.info(f"Área ID: {area_id} actualizada exitosamente")
        return AreaRead(**resultado_update)

    @staticmethod
    @BaseService.handle_service_errors
    async def cambiar_estado_area(area_id: int, activar: bool) -> AreaRead:
        """
        Activa o desactiva un área (borrado lógico).
        
        🔄 CAMBIO DE ESTADO:
        - activar=True: Reactiva un área desactivada
        - activar=False: Desactiva un área activa
        
        Args:
            area_id: ID del área a modificar
            activar: True para activar, False para desactivar
            
        Returns:
            AreaRead: El área con el nuevo estado
            
        Raises:
            NotFoundError: Si el área no existe
            ValidationError: Si el área ya está en el estado deseado
        """
        accion = "reactivar" if activar else "desactivar"
        logger.info(f"Intentando {accion} área ID: {area_id}")

        # 🔍 VERIFICAR EXISTENCIA Y ESTADO ACTUAL
        area_existente = await AreaService.obtener_area_por_id(area_id)
        if not area_existente:
            raise NotFoundError(
                detail=f"Área con ID {area_id} no encontrada para {accion}.",
                internal_code="AREA_NOT_FOUND"
            )
            
        # 🚫 VALIDACIÓN: No realizar operación redundante
        if area_existente.es_activo == activar:
            estado_str = "activa" if activar else "inactiva"
            raise ValidationError(
                detail=f"Área con ID {area_id} ya está {estado_str}.",
                internal_code="AREA_ALREADY_IN_STATE"
            )

        # 💾 EJECUTAR CAMBIO DE ESTADO
        resultado_toggle = execute_update(TOGGLE_AREA_STATUS_QUERY, (activar, area_id))
        
        # 🔄 FALLBACK: Verificar cambio si no retorna datos
        if not resultado_toggle:
            logger.warning(f"execute_update no devolvió datos al {accion} área {area_id}")
            toggled_area = await AreaService.obtener_area_por_id(area_id)
            if not toggled_area or toggled_area.es_activo != activar:
                raise ServiceError(
                    status_code=500,
                    detail=f"Error crítico: Área {accion}da pero no se pudo verificar el estado.",
                    internal_code="AREA_STATE_VERIFICATION_FAILED"
                )
            logger.info(f"Área ID: {area_id} {accion}da (verificada post-actualización)")
            return toggled_area
            
        # ✅ ÉXITO: Retornar datos del cambio
        logger.info(f"Área ID: {area_id} {accion}da exitosamente")
        return AreaRead(**resultado_toggle)

    @staticmethod
    @BaseService.handle_service_errors
    async def obtener_lista_simple_areas_activas() -> List[AreaSimpleList]:
        """
        Obtiene una lista simplificada de áreas activas.
        
        🎯 PROPÓSITO: Optimizado para listas desplegables y selectores
        donde solo se necesitan ID y nombre.
        
        Returns:
            List[AreaSimpleList]: Lista de áreas activas simplificadas
        """
        logger.info("Obteniendo lista simple de áreas activas")
        
        rows = execute_query(GET_ACTIVE_AREAS_SIMPLE_LIST_QUERY)
        if not rows:
            logger.info("No se encontraron áreas activas para la lista simple")
            return []

        # 🎯 MAPEO SEGURO: Continuar incluso si algún registro falla
        areas_list = []
        for row in rows:
            try:
                areas_list.append(AreaSimpleList(**row))
            except Exception as map_err:
                logger.error(f"Error mapeando área simple: {map_err}")
                continue

        logger.info(f"Lista simple obtenida: {len(areas_list)} áreas activas")
        return areas_list