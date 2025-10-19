# app/services/autorizacion_service.py
import asyncio
from typing import List, Dict, Optional, Any
import logging

# 🗄️ IMPORTACIONES DE BASE DE DATOS
from app.db.queries import (
    execute_query, execute_update, execute_procedure_params
)

# 🚨 EXCEPCIONES - Nuevo sistema de manejo de errores
from app.core.exceptions import (
    ValidationError, NotFoundError, ServiceError, DatabaseError
)

# 🏗️ BASE SERVICE - Clase base para manejo consistente de errores
from app.services.base_service import BaseService

logger = logging.getLogger(__name__)

class AutorizacionService(BaseService):
    """
    Servicio para gestión de autorizaciones y procesos de destajo.
    
    ⚠️ IMPORTANTE: Este servicio maneja operaciones críticas relacionadas con:
    - Autorización de procesos pendientes
    - Finalización de tareos
    - Generación de reportes de autorización
    
    CARACTERÍSTICAS PRINCIPALES:
    - Herencia de BaseService para manejo automático de errores
    - Validaciones robustas de datos de procesos
    - Manejo de transacciones implícitas en consultas
    - Logging detallado para auditoría de procesos
    """

    @staticmethod
    @BaseService.handle_service_errors
    async def get_pendientes_autorizacion() -> List[Dict]:
        """
        Ejecuta el SP sp_pendiente_autorizacion y retorna la lista de registros pendientes.
        
        📊 PROPÓSITO: Obtiene todos los procesos pendientes de autorización para
        que los administradores puedan revisarlos y autorizarlos/rechazarlos.
        
        Returns:
            List[Dict]: Lista de procesos pendientes con información completa
            
        Raises:
            ServiceError: Si hay errores en la ejecución del stored procedure
        """
        logger.info("Ejecutando SP sp_pendiente_autorizacion para obtener pendientes")
        
        try:
            query = "EXEC dbo.sp_pendiente_autorizacion"
            results = execute_query(query, ())
            
            if not results:
                logger.info("No se encontraron registros pendientes de autorización")
                return []
            
            logger.info(f"Se obtuvieron {len(results)} registros pendientes de autorización")
            return results
            
        except DatabaseError as db_err:
            logger.error(f"Error de base de datos en get_pendientes_autorizacion: {db_err.detail}")
            raise ServiceError(
                status_code=500,
                detail="Error de base de datos al obtener pendientes de autorización",
                internal_code="AUTH_PENDING_RETRIEVAL_ERROR"
            )
        except Exception as e:
            logger.exception(f"Error inesperado en get_pendientes_autorizacion: {str(e)}")
            raise ServiceError(
                status_code=500,
                detail="Error interno al obtener pendientes de autorización",
                internal_code="AUTH_PENDING_UNEXPECTED_ERROR"
            )

    @staticmethod
    @BaseService.handle_service_errors
    async def autorizar_proceso(
        lote: str, 
        fecha_destajo: str, 
        cod_proceso: str, 
        cod_subproceso: str, 
        nuevo_estado: str, 
        observacion_autorizacion: str = ""
    ) -> Dict:
        """
        Actualiza el estado de autorización de un registro específico en pdespe_supervisor00.
        
        🔄 FLUJO DE AUTORIZACIÓN:
        1. Verifica que el registro exista y esté pendiente
        2. Valida que no sea una operación redundante
        3. Actualiza el estado y registra observaciones
        4. Retorna el resultado de la operación
        
        Args:
            lote: Código del lote a autorizar
            fecha_destajo: Fecha del destajo en formato ISO
            cod_proceso: Código del proceso
            cod_subproceso: Código del subproceso
            nuevo_estado: Nuevo estado (A=Autorizado, R=Rechazado, P=Pendiente)
            observacion_autorizacion: Observación opcional para la autorización
            
        Returns:
            Dict: Resultado de la operación con metadatos
            
        Raises:
            NotFoundError: Si el registro no existe
            ValidationError: Si el estado actual es igual al nuevo estado
            ServiceError: Si la actualización falla
        """
        logger.info(f"Intentando autorizar proceso - Lote: {lote}, Fecha: {fecha_destajo}")
        
        try:
            # 🔍 VERIFICAR EXISTENCIA DEL REGISTRO
            check_query = """
            SELECT sautor, dlotes, fdesta 
            FROM dbo.pdespe_supervisor00 
            WHERE dlotes = ? AND fdesta = ? and cproce = ? and csubpr = ?
            """
            
            existing_record = execute_query(
                check_query, 
                (lote, fecha_destajo, cod_proceso, cod_subproceso)
            )
            
            if not existing_record:
                logger.warning(f"Registro no encontrado - Lote: {lote}, Fecha: {fecha_destajo}")
                raise NotFoundError(
                    detail=f"No se encontró registro para el lote {lote} en la fecha {fecha_destajo}",
                    internal_code="PROCESS_RECORD_NOT_FOUND"
                )
            
            # 🚫 VALIDAR OPERACIÓN REDUNDANTE
            current_status = existing_record[0]['sautor']
            if current_status == nuevo_estado:
                logger.info(f"Estado ya actualizado - Lote: {lote}, Estado: {nuevo_estado}")
                return {
                    "message": f"El proceso ya estaba en estado {nuevo_estado}",
                    "lote": lote,
                    "fecha_destajo": fecha_destajo,
                    "cod_proceso": cod_proceso,
                    "cod_subproceso": cod_subproceso,
                    "estado_anterior": current_status,
                    "nuevo_estado": nuevo_estado
                }
            
            # 💾 EJECUTAR ACTUALIZACIÓN
            update_query = """
            UPDATE dbo.pdespe_supervisor00 
            SET sautor = ?, fautor = GETDATE(), obsaut = ?
            WHERE dlotes = ? AND fdesta = ? and cproce = ? and csubpr = ?
            """
            
            result = execute_update(
                update_query, 
                (nuevo_estado, observacion_autorizacion, lote, fecha_destajo, cod_proceso, cod_subproceso)
            )

            # ✅ VERIFICAR RESULTADO DE ACTUALIZACIÓN
            if result.get('rows_affected', 0) > 0:
                logger.info(f"Proceso autorizado exitosamente - Lote: {lote}")
                return {
                    "message": "Proceso autorizado exitosamente",
                    "lote": lote,
                    "fecha_destajo": fecha_destajo,
                    "cod_proceso": cod_proceso,
                    "cod_subproceso": cod_subproceso,
                    "estado_anterior": current_status,
                    "nuevo_estado": nuevo_estado,
                    "observacion_autorizacion": observacion_autorizacion
                }
            else:
                logger.warning(f"No se pudo actualizar registro - Lote: {lote}")
                raise NotFoundError(
                    detail=f"No se encontró registro para actualizar: Lote {lote}",
                    internal_code="PROCESS_UPDATE_NOT_FOUND"
                )
                
        except (ValidationError, NotFoundError):
            # 🔄 RE-LANZAR ERRORES ESPECÍFICOS
            raise
        except DatabaseError as db_err:
            logger.error(f"Error de BD en autorizar_proceso - Lote: {lote}: {db_err.detail}")
            raise ServiceError(
                status_code=500,
                detail="Error de base de datos al autorizar proceso",
                internal_code="PROCESS_AUTHORIZATION_DB_ERROR"
            )
        except Exception as e:
            logger.exception(f"Error inesperado en autorizar_proceso - Lote: {lote}: {str(e)}")
            raise ServiceError(
                status_code=500,
                detail="Error interno al autorizar proceso",
                internal_code="PROCESS_AUTHORIZATION_UNEXPECTED_ERROR"
            )

    @staticmethod
    @BaseService.handle_service_errors
    async def get_conteo_pendientes() -> Dict:
        """
        Obtiene solo el conteo de registros pendientes (optimizado para dashboards).
        
        🎯 OPTIMIZACIÓN: Consulta específica para dashboards que solo necesitan
        números sin cargar todos los datos de los registros.
        
        Returns:
            Dict: Conteo de pendientes y metadatos
            
        Raises:
            ServiceError: Si hay errores en la consulta de conteo
        """
        logger.debug("🔢 Obteniendo conteo de pendientes de autorización")
        
        try:
            query = """
            SELECT COUNT(*) as total_pendientes
            FROM dbo.pdespe_supervisor00 
            WHERE sautor = 0 AND fdesta > '2025-09-01'
            """
            
            result = execute_query(query, ())
            
            if not result:
                logger.warning("No se pudo obtener el conteo de pendientes")
                return {"total_pendientes": 0}
            
            # 🎯 EXTRAER TOTAL DE FORMA ROBUSTA
            total_pendientes = (
                result[0].get('total_pendientes') or 
                result[0].get('') or 
                list(result[0].values())[0]
            )
            
            logger.debug(f"Total de pendientes: {total_pendientes}")
            return {
                "total_pendientes": total_pendientes,
                "fecha_consulta": "2025-09-20"  # 📅 Podría ser dinámico
            }
            
        except DatabaseError as db_err:
            logger.error(f"Error de BD en get_conteo_pendientes: {db_err.detail}")
            raise ServiceError(
                status_code=500,
                detail="Error de base de datos al obtener conteo de pendientes",
                internal_code="PENDING_COUNT_DB_ERROR"
            )
        except Exception as e:
            logger.exception(f"Error inesperado en get_conteo_pendientes: {str(e)}")
            raise ServiceError(
                status_code=500,
                detail="Error interno al obtener conteo de pendientes",
                internal_code="PENDING_COUNT_UNEXPECTED_ERROR"
            )

    @staticmethod
    @BaseService.handle_service_errors
    async def autorizar_multiple(autorizaciones: List[Dict]) -> Dict:
        """
        Autoriza múltiples registros en una sola operación con manejo de errores individual.
        
        🎯 PROCESAMIENTO POR LOTES:
        - Procesa cada autorización individualmente
        - Continúa con las siguientes aunque alguna falle
        - Retorna resumen con éxitos, fallos y errores
        
        Args:
            autorizaciones: Lista de diccionarios con datos de autorización
            
        Returns:
            Dict: Resumen del procesamiento por lotes
            
        Raises:
            ValidationError: Si la lista está vacía
            ServiceError: Si hay errores en el procesamiento general
        """
        logger.info(f"Iniciando autorización múltiple de {len(autorizaciones)} registros")
        
        try:
            # 🚫 VALIDAR LISTA NO VACÍA
            if not autorizaciones:
                raise ValidationError(
                    detail="La lista de autorizaciones no puede estar vacía",
                    internal_code="EMPTY_AUTHORIZATION_LIST"
                )
            
            exitosos = 0
            fallidos = 0
            errores = []
            
            # 🔄 PROCESAR CADA AUTORIZACIÓN INDIVIDUALMENTE
            for auth_data in autorizaciones:
                try:
                    lote = auth_data.get('lote')
                    fecha_destajo = auth_data.get('fecha_destajo')
                    cod_proceso = auth_data.get('cod_proceso')
                    cod_subproceso = auth_data.get('cod_subproceso')
                    nuevo_estado = auth_data.get('nuevo_estado', 1)
                    observacion_autorizacion = auth_data.get('observacion_autorizacion', '')
                    
                    # 🚫 VALIDAR DATOS MÍNIMOS
                    if not lote or not fecha_destajo:
                        fallidos += 1
                        errores.append(f"Datos incompletos: {auth_data}")
                        continue
                    
                    # 🎯 EJECUTAR AUTORIZACIÓN INDIVIDUAL
                    await AutorizacionService.autorizar_proceso(
                        lote, 
                        fecha_destajo, 
                        cod_proceso, 
                        cod_subproceso, 
                        nuevo_estado, 
                        observacion_autorizacion
                    )
                    exitosos += 1
                    
                except Exception as e:
                    fallidos += 1
                    errores.append(f"Error en {lote}: {str(e)}")
            
            # 📊 CONSTRUIR RESPUESTA RESUMEN
            resultado = {
                "message": "Autorización múltiple completada",
                "exitosos": exitosos,
                "fallidos": fallidos,
                "total_procesados": len(autorizaciones),
                "errores": errores[:10]  # 🔒 Limitar errores mostrados
            }
            
            logger.info(f"Autorización múltiple completada: {exitosos} exitosos, {fallidos} fallidos")
            return resultado
            
        except ValidationError:
            # 🔄 RE-LANZAR ERRORES DE VALIDACIÓN
            raise
        except DatabaseError as db_err:
            logger.error(f"Error de BD en autorizar_multiple: {db_err.detail}")
            raise ServiceError(
                status_code=500,
                detail="Error de base de datos en autorización múltiple",
                internal_code="BATCH_AUTHORIZATION_DB_ERROR"
            )
        except Exception as e:
            logger.exception(f"Error inesperado en autorizar_multiple: {str(e)}")
            raise ServiceError(
                status_code=500,
                detail="Error interno en autorización múltiple",
                internal_code="BATCH_AUTHORIZATION_UNEXPECTED_ERROR"
            )

    @staticmethod
    @BaseService.handle_service_errors
    async def finalizar_tareo(data: Dict) -> Dict:
        """
        Actualiza los campos de un tareo para marcarlo como finalizado.
        
        📝 OPERACIÓN DE CIERRE:
        - Actualiza horas, kilos y observaciones
        - Valida la existencia del registro
        - Maneja campos opcionales de forma segura
        
        Args:
            data: Diccionario con datos del tareo a finalizar
            
        Returns:
            Dict: Resultado de la operación con metadatos
            
        Raises:
            NotFoundError: Si el registro no existe
            ServiceError: Si la actualización falla
        """
        try:
            lote = data.get("lote")
            fecha_destajo = data.get("fecha_destajo")
            cod_trabajador = data.get("cod_trabajador")
            cod_proceso = data.get("cod_proceso")
            cod_subproceso = data.get("cod_subproceso") or ""

            logger.info(
                f"Finalizando tareo - Lote: {lote}, Trabajador: {cod_trabajador}, "
                f"Fecha: {fecha_destajo}, Proceso: {cod_proceso}, Subproceso: {cod_subproceso}"
            )

            # 🔍 VALIDAR EXISTENCIA DEL REGISTRO
            check_query = """
            SELECT TOP 1 1
            FROM dbo.pdespe_supervisor00
            WHERE dlotes = ? AND fdesta = ? AND ctraba = ? AND cproce = ? AND csubpr = ?
            """
            
            existing = execute_query(
                check_query, 
                (lote, fecha_destajo, cod_trabajador, cod_proceso, cod_subproceso)
            )
            
            if not existing:
                raise NotFoundError(
                    detail=(
                        f"No se encontró registro para lote={lote}, fecha={fecha_destajo}, "
                        f"trabajador={cod_trabajador}, proceso={cod_proceso}, subproceso={cod_subproceso}"
                    ),
                    internal_code="TAREO_RECORD_NOT_FOUND"
                )

            # 💾 EJECUTAR ACTUALIZACIÓN
            update_query = """
            UPDATE dbo.pdespe_supervisor00
            SET hhorin = ?, hhorfi = ?, nhortr = ?, qkgtra = ?,
                dobser = ?, dobser_det = ?
            WHERE dlotes = ? AND fdesta = ? AND ctraba = ? AND cproce = ? AND csubpr = ?
            """

            result = execute_update(update_query, (
                data.get("hora_inicio"),
                data.get("hora_fin"),
                data.get("horas"),
                data.get("kilos"),
                data.get("observacion"),
                data.get("detalle_observacion"),
                lote,
                fecha_destajo,
                cod_trabajador,
                cod_proceso,
                cod_subproceso
            ))

            # ✅ VERIFICAR ACTUALIZACIÓN EXITOSA
            if result.get("rows_affected", 0) == 0:
                raise NotFoundError(
                    detail=(
                        f"No se pudo actualizar el registro para Lote={lote}, Trabajador={cod_trabajador}, "
                        f"Fecha={fecha_destajo}, Proceso={cod_proceso}, Subproceso={cod_subproceso}"
                    ),
                    internal_code="TAREO_UPDATE_FAILED"
                )

            logger.info(f"Tareo finalizado correctamente - Lote: {lote}, Trabajador: {cod_trabajador}")
            return {
                "message": "Tareo finalizado exitosamente",
                "lote": lote,
                "fecha_destajo": fecha_destajo,
                "cod_proceso": cod_proceso,
                "cod_subproceso": cod_subproceso,
                "cod_trabajador": cod_trabajador
            }

        except (ValidationError, NotFoundError):
            # 🔄 RE-LANZAR ERRORES ESPECÍFICOS
            raise
        except DatabaseError as db_err:
            logger.error(f"Error de BD en finalizar_tareo: {db_err.detail}")
            raise ServiceError(
                status_code=500,
                detail="Error de base de datos al finalizar tareo",
                internal_code="TAREO_FINALIZATION_DB_ERROR"
            )
        except Exception as e:
            logger.exception(f"Error inesperado en finalizar_tareo: {str(e)}")
            raise ServiceError(
                status_code=500,
                detail="Error interno al finalizar el tareo",
                internal_code="TAREO_FINALIZATION_UNEXPECTED_ERROR"
            )
        
    @staticmethod
    @BaseService.handle_service_errors
    async def get_reporte_autorizacion(fecha_inicio: str, fecha_fin: str) -> List[Dict]:
        """
        Ejecuta el SP sp_reporte_autorizacion_destajo con parámetros de rango de fechas.
        
        📊 GENERACIÓN DE REPORTES:
        - Filtra por rango de fechas
        - Usa execute_procedure_params para mejor performance
        - Maneja formato de fechas automáticamente
        
        Args:
            fecha_inicio: Fecha inicial en formato ISO
            fecha_fin: Fecha final en formato ISO
            
        Returns:
            List[Dict]: Lista de registros del reporte
            
        Raises:
            ServiceError: Si hay errores en la ejecución del SP
        """
        try:
            # 🎯 EXTRAER SOLO LA PARTE DE LA FECHA (YYYY-MM-DD)
            fecha_inicio_solo_fecha = fecha_inicio.split('T')[0]
            fecha_fin_solo_fecha = fecha_fin.split('T')[0]
            
            logger.info(
                f"Ejecutando SP sp_reporte_autorizacion_destajo - "
                f"Rango: {fecha_inicio_solo_fecha} a {fecha_fin_solo_fecha}"
            )

            # 🗄️ EJECUTAR STORED PROCEDURE CON PARÁMETROS
            params = {
                "fecha_inicio": fecha_inicio_solo_fecha,
                "fecha_fin": fecha_fin_solo_fecha
            }

            results = await asyncio.to_thread(
                execute_procedure_params,
                "dbo.sp_reporte_autorizacion_destajo",
                params
            )

            if not results:
                logger.info("El SP no devolvió resultados")
                return []

            logger.info(f"Se obtuvieron {len(results)} registros en el reporte")
            return results

        except DatabaseError as db_err:
            logger.error(f"Error de BD en get_reporte_autorizacion: {db_err.detail}")
            raise ServiceError(
                status_code=500,
                detail="Error de base de datos al obtener reporte de autorización",
                internal_code="REPORT_GENERATION_DB_ERROR"
            )
        except Exception as e:
            logger.exception(f"Error inesperado en get_reporte_autorizacion: {str(e)}")
            raise ServiceError(
                status_code=500,
                detail="Error interno al obtener reporte de autorización",
                internal_code="REPORT_GENERATION_UNEXPECTED_ERROR"
            )