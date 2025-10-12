# app/services/autorizacion_service.py
import asyncio
from typing import List, Dict, Optional
from app.db.queries import execute_query, execute_update, execute_procedure_params
from app.core.exceptions import ServiceError, ValidationError
from app.core.logging_config import get_logger

logger = get_logger(__name__)

class AutorizacionService:
    
    @staticmethod
    async def get_pendientes_autorizacion() -> List[Dict]:
        """
        Ejecuta el SP sp_pendiente_autorizacion y retorna la lista de registros pendientes.
        """
        try:
            logger.info("Ejecutando SP sp_pendiente_autorizacion")
            
            # Ejecutar el stored procedure
            query = "EXEC dbo.sp_pendiente_autorizacion"
            results = execute_query(query, ())
            
            if not results:
                logger.info("No se encontraron registros pendientes de autorización")
                return []
            
            logger.info(f"Se obtuvieron {len(results)} registros pendientes de autorización")
            return results
            
        except Exception as e:
            logger.exception(f"Error ejecutando SP sp_pendiente_autorizacion: {str(e)}")
            raise ServiceError(status_code=500, detail=f"Error obteniendo pendientes de autorización: {str(e)}")
    
    @staticmethod
    async def autorizar_proceso(lote: str, fecha_destajo: str, cod_proceso: str, cod_subproceso: str, nuevo_estado: str, observacion_autorizacion: str = "") -> Dict:
        """
        Actualiza el estado de autorización de un registro específico en pdespe_supervisor00.
        """
        try:
            logger.info(f"Autorizando proceso para el lote {lote}, fecha {fecha_destajo}")
            
            # Verificar que el registro existe y está pendiente
            check_query = """
            SELECT sautor, dlotes, fdesta 
            FROM dbo.pdespe_supervisor00 
            WHERE dlotes = ? AND fdesta = ? and cproce = ? and csubpr = ?
            """
            existing_record = execute_query(check_query, (lote, fecha_destajo, cod_proceso, cod_subproceso))
            
            if not existing_record:
                logger.warning(f"No se encontró registro para el lote {lote}, fecha {fecha_destajo}")
                raise ValidationError(
                    status_code=404, 
                    detail=f"No se encontró registro para el lote {lote} en la fecha {fecha_destajo}"
                )
            
            current_status = existing_record[0]['sautor']
            if current_status == nuevo_estado:
                logger.info(f"El registro ya tiene el estado {nuevo_estado}")
                return {
                    "message": f"El proceso ya estaba en estado {nuevo_estado}",
                    "lote": lote,
                    "fecha_destajo": fecha_destajo,
                    "cod_proceso": cod_proceso,
                    "cod_subproceso": cod_subproceso,
                    "estado_anterior": current_status,
                    "nuevo_estado": nuevo_estado
                }
            
            # Actualizar el estado de autorización y la observación
            update_query = """
            UPDATE dbo.pdespe_supervisor00 
            SET sautor = ?, fautor = GETDATE(), obsaut = ?
            WHERE dlotes = ? AND fdesta = ? and cproce = ? and csubpr = ?
            """
            
            result = execute_update(update_query, (nuevo_estado, observacion_autorizacion, lote, fecha_destajo, cod_proceso, cod_subproceso))

            # ✅ Ahora chequear rows_affected
            if result.get('rows_affected', 0) > 0:
                logger.info(f"Proceso autorizado exitosamente para el lote {lote}")
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
                logger.warning(f"No se encontró registro para actualizar: {lote}")
                raise ValidationError(
                    status_code=404, 
                    detail=f"No se encontró registro para el lote {lote} en la fecha {fecha_destajo}"
                )
                
        except ValidationError as e:
            logger.warning(f"Error de validación en autorizar_proceso: {e.detail}")
            raise e
        except Exception as e:
            logger.exception(f"Error inesperado en autorizar_proceso: {str(e)}")
            raise ServiceError(status_code=500, detail=f"Error autorizando proceso: {str(e)}")
    
    @staticmethod
    async def get_conteo_pendientes() -> Dict:
        """
        Obtiene solo el conteo de registros pendientes (más rápido para dashboards).
        """
        try:
            logger.debug("Obteniendo conteo de pendientes de autorización")
            
            query = """
            SELECT COUNT(*) as total_pendientes
            FROM dbo.pdespe_supervisor00 
            WHERE sautor = 0 AND fdesta > '2025-09-01'
            """
            
            result = execute_query(query, ())
            
            if not result:
                logger.warning("No se pudo obtener el conteo de pendientes")
                return {"total_pendientes": 0}
            
            # Manejar el resultado del COUNT (puede venir sin nombre de columna)
            total_pendientes = result[0].get('total_pendientes') or result[0].get('') or list(result[0].values())[0]
            
            logger.debug(f"Total de pendientes: {total_pendientes}")
            return {
                "total_pendientes": total_pendientes,
                "fecha_consulta": "2025-09-20"
            }
            
        except Exception as e:
            logger.exception(f"Error obteniendo conteo de pendientes: {str(e)}")
            raise ServiceError(status_code=500, detail=f"Error obteniendo conteo: {str(e)}")
    
    @staticmethod
    async def autorizar_multiple(autorizaciones: List[Dict]) -> Dict:
        """
        Autoriza múltiples registros en una sola operación.
        """
        try:
            logger.info(f"Iniciando autorización múltiple de {len(autorizaciones)} registros")
            
            if not autorizaciones:
                raise ValidationError(status_code=400, detail="La lista de autorizaciones no puede estar vacía")
            
            exitosos = 0
            fallidos = 0
            errores = []
            
            for auth_data in autorizaciones:
                try:
                    lote = auth_data.get('lote')
                    fecha_destajo = auth_data.get('fecha_destajo')
                    cod_proceso = auth_data.get('cod_proceso')
                    cod_subproceso = auth_data.get('cod_subproceso')
                    nuevo_estado = auth_data.get('nuevo_estado', 1)
                    observacion_autorizacion = auth_data.get('observacion_autorizacion', '')
                    
                    if not lote or not fecha_destajo:
                        fallidos += 1
                        errores.append(f"Datos incompletos: {auth_data}")
                        continue
                    
                    # Usar el método individual para cada autorización
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
            
            resultado = {
                "message": "Autorización múltiple completada",
                "exitosos": exitosos,
                "fallidos": fallidos,
                "total_procesados": len(autorizaciones),
                "errores": errores[:10]  # Limitar errores mostrados
            }
            
            logger.info(f"Autorización múltiple completada: {exitosos} exitosos, {fallidos} fallidos")
            return resultado
            
        except ValidationError as e:
            logger.warning(f"Error de validación en autorización múltiple: {e.detail}")
            raise e
        except Exception as e:
            logger.exception(f"Error inesperado en autorización múltiple: {str(e)}")
            raise ServiceError(status_code=500, detail=f"Error en autorización múltiple: {str(e)}")

    @staticmethod
    async def finalizar_tareo(data: Dict) -> Dict:
        """
        Actualiza los campos de hora_inicio, hora_fin, horas, kilos, observacion y detalle_observacion
        de un registro en pdespe_supervisor00 basado en la clave compuesta:
        fecha_destajo, lote, cod_proceso, cod_subproceso, cod_trabajador.
        """
        try:
            lote = data.get("lote")
            fecha_destajo = data.get("fecha_destajo")
            cod_trabajador = data.get("cod_trabajador")
            cod_proceso = data.get("cod_proceso")
            cod_subproceso = data.get("cod_subproceso") or ""

            logger.info(f"Finalizando tareo para Lote={lote}, Trabajador={cod_trabajador}, "
                        f"Fecha={fecha_destajo}, Proceso={cod_proceso}, Subproceso={cod_subproceso}")

            # Validar existencia
            check_query = """
            SELECT TOP 1 1
            FROM dbo.pdespe_supervisor00
            WHERE dlotes = ? AND fdesta = ? AND ctraba = ? AND cproce = ? AND csubpr = ?
            """
            existing = execute_query(check_query, (lote, fecha_destajo, cod_trabajador, cod_proceso, cod_subproceso))
            if not existing:
                raise ValidationError(
                    status_code=404,
                    detail=f"No se encontró registro para lote={lote}, fecha={fecha_destajo}, "
                           f"trabajador={cod_trabajador}, proceso={cod_proceso}, subproceso={cod_subproceso}"
                )

            # Actualizar
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

            if result.get("rows_affected", 0) == 0:
                raise ValidationError(
                    status_code=404,
                    detail=f"No se pudo actualizar el registro para Lote={lote}, Trabajador={cod_trabajador}, "
                           f"Fecha={fecha_destajo}, Proceso={cod_proceso}, Subproceso={cod_subproceso}"
                )

            logger.info(f"Tareo finalizado correctamente para Lote={lote}, Trabajador={cod_trabajador}")
            return {
                "message": "Tareo finalizado exitosamente",
                "lote": lote,
                "fecha_destajo": fecha_destajo,
                "cod_proceso": cod_proceso,
                "cod_subproceso": cod_subproceso,
                "cod_trabajador": cod_trabajador
            }

        except ValidationError as e:
            raise e
        except Exception as e:
            logger.exception(f"Error inesperado en finalizar_tareo: {str(e)}")
            raise ServiceError(status_code=500, detail=f"Error al finalizar el tareo: {str(e)}")
        
    @staticmethod
    async def get_reporte_autorizacion(fecha_inicio: str, fecha_fin: str) -> List[Dict]:
        """
        Ejecuta el SP sp_reporte_autorizacion_destajo con parámetros de rango de fechas.
        Usa execute_procedure_params para mejor performance.
        """
        try:
            # ✅ EXTRAER SOLO LA PARTE DE LA FECHA (YYYY-MM-DD)
            # Esto elimina la parte 'T00:00:00' si existe.
            fecha_inicio_solo_fecha = fecha_inicio.split('T')[0]
            fecha_fin_solo_fecha = fecha_fin.split('T')[0]
            logger.info(f"Ejecutando SP sp_reporte_autorizacion_destajo con rango {fecha_inicio_solo_fecha} a {fecha_fin_solo_fecha}")

            # ✅ Usar execute_procedure_params en lugar de execute_query
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

        except Exception as e:
            logger.exception(f"Error ejecutando SP sp_reporte_autorizacion_destajo: {str(e)}")
            raise ServiceError(status_code=500, detail=f"Error obteniendo reporte de autorización: {str(e)}")