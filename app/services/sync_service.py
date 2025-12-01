# app/services/sync_service.py
"""
Servicio para sincronización de perfiles de usuario con sistemas externos.
"""
import logging
from typing import Dict, Optional
from app.db.queries import (
    execute_query, execute_update,
    SELECT_PERFIL_EXTERNO_QUERY,
    UPDATE_USUARIO_PERFIL_EXTERNO_QUERY
)
from app.db.connection import DatabaseConnection
from app.core.exceptions import (
    NotFoundError, ValidationError, ServiceError, DatabaseError
)
from app.services.base_service import BaseService

logger = logging.getLogger(__name__)

class SyncService(BaseService):
    """
    Servicio para sincronizar datos de perfil desde sistemas externos.
    """

    @staticmethod
    @BaseService.handle_service_errors
    async def obtener_perfil_externo(codigo_trabajador: str) -> Optional[Dict]:
        """
        Obtiene el perfil de un trabajador desde la base de datos externa del cliente.
        
        Args:
            codigo_trabajador: Código del trabajador en el sistema externo
            
        Returns:
            Dict con nombre y apellido del trabajador, o None si no existe
            
        Raises:
            ServiceError: Si hay error al consultar la BD externa
        """
        logger.info(f"Consultando perfil externo para código trabajador: {codigo_trabajador}")
        
        try:
            resultados = execute_query(SELECT_PERFIL_EXTERNO_QUERY, (codigo_trabajador,))
            
            if not resultados:
                logger.warning(f"No se encontró trabajador con código: {codigo_trabajador}")
                return None
            
            perfil = resultados[0]
            logger.info(f"Perfil externo encontrado: {perfil.get('nombre')} {perfil.get('apellido')}")
            return perfil
            
        except DatabaseError as db_err:
            logger.error(f"Error BD externa al obtener perfil: {db_err.detail}")
            raise ServiceError(
                status_code=503,
                detail="Error al conectar con el sistema externo de personal",
                internal_code="EXTERNAL_DB_CONNECTION_ERROR"
            )
        except Exception as e:
            logger.exception(f"Error inesperado obteniendo perfil externo: {str(e)}")
            raise ServiceError(
                status_code=500,
                detail="Error interno al consultar perfil externo",
                internal_code="EXTERNAL_PROFILE_RETRIEVAL_ERROR"
            )

    @staticmethod
    @BaseService.handle_service_errors
    async def sincronizar_perfil_usuario(usuario_id: int) -> Dict:
        """
        Sincroniza el perfil de un usuario con origen_datos='externo' 
        consultando la BD externa del cliente.
        
        Flujo:
        1. Verifica que el usuario existe y tiene origen_datos='externo'
        2. Obtiene codigo_trabajador_externo del usuario
        3. Consulta la BD externa del cliente
        4. Actualiza nombre y apellido en la BD local
        
        Args:
            usuario_id: ID del usuario a sincronizar
            
        Returns:
            Dict con los datos actualizados del usuario
            
        Raises:
            NotFoundError: Si el usuario no existe
            ValidationError: Si el usuario no es de origen externo o falta código
            ServiceError: Si hay errores en la sincronización
        """
        logger.info(f"Iniciando sincronización de perfil para usuario ID: {usuario_id}")
        
        try:
            # 1️⃣ VERIFICAR USUARIO Y ORIGEN
            query_usuario = """
                SELECT usuario_id, nombre_usuario, origen_datos, codigo_trabajador_externo,
                       nombre, apellido
                FROM usuario
                WHERE usuario_id = ? AND es_eliminado = 0
            """
            usuario_result = execute_query(query_usuario, (usuario_id,))
            
            if not usuario_result:
                raise NotFoundError(
                    detail=f"Usuario con ID {usuario_id} no encontrado",
                    internal_code="USER_NOT_FOUND"
                )
            
            usuario = usuario_result[0]
            
            # ✅ VALIDAR QUE SEA USUARIO EXTERNO
            if usuario['origen_datos'] != 'externo':
                raise ValidationError(
                    detail="Solo se pueden sincronizar usuarios con origen_datos='externo'",
                    internal_code="USER_NOT_EXTERNAL"
                )
            
            # ✅ VALIDAR QUE TENGA CÓDIGO DE TRABAJADOR
            codigo_trabajador = usuario.get('codigo_trabajador_externo')
            if not codigo_trabajador or codigo_trabajador.strip() == '':
                raise ValidationError(
                    detail="El usuario no tiene código de trabajador externo configurado",
                    internal_code="MISSING_EXTERNAL_CODE"
                )
            
            logger.info(f"Usuario válido para sincronización. Código trabajador: {codigo_trabajador}")
            
            # 2️⃣ CONSULTAR PERFIL EXTERNO
            perfil_externo = await SyncService.obtener_perfil_externo(codigo_trabajador)
            
            if not perfil_externo:
                raise NotFoundError(
                    detail=f"No se encontró información del trabajador con código {codigo_trabajador} en el sistema externo",
                    internal_code="EXTERNAL_WORKER_NOT_FOUND"
                )
            
            # 3️⃣ EXTRAER DATOS DEL PERFIL EXTERNO
            nuevo_nombre = perfil_externo.get('nombre', '').strip()
            nuevo_apellido = perfil_externo.get('apellido', '').strip()
            
            if not nuevo_nombre and not nuevo_apellido:
                raise ValidationError(
                    detail="El perfil externo no contiene nombre ni apellido válidos",
                    internal_code="INVALID_EXTERNAL_PROFILE_DATA"
                )
            
            # 4️⃣ ACTUALIZAR EN BD LOCAL
            logger.info(f"Actualizando perfil local con: nombre='{nuevo_nombre}', apellido='{nuevo_apellido}'")
            
            resultado_update = execute_update(
                UPDATE_USUARIO_PERFIL_EXTERNO_QUERY,
                (nuevo_nombre, nuevo_apellido, usuario_id),
                connection_type=DatabaseConnection.DEFAULT
            )
            
            if not resultado_update or resultado_update.get('rows_affected', 0) == 0:
                raise ServiceError(
                    status_code=500,
                    detail="No se pudo actualizar el perfil del usuario",
                    internal_code="PROFILE_UPDATE_FAILED"
                )
            
            logger.info(f"✅ Perfil sincronizado exitosamente para usuario ID {usuario_id}")
            
            # 5️⃣ RETORNAR DATOS ACTUALIZADOS
            return {
                "usuario_id": resultado_update['usuario_id'],
                "nombre": resultado_update['nombre'],
                "apellido": resultado_update['apellido'],
                "fecha_actualizacion": resultado_update['fecha_actualizacion'],
                "sincronizado_desde": "sistema_externo",
                "codigo_trabajador": codigo_trabajador
            }
            
        except (NotFoundError, ValidationError):
            raise
        except ServiceError as se:
            # Re-lanzar ServiceErrors ya manejados
            raise
        except DatabaseError as db_err:
            logger.error(f"Error de BD al sincronizar perfil: {db_err.detail}")
            raise ServiceError(
                status_code=500,
                detail="Error de base de datos durante la sincronización",
                internal_code="SYNC_DB_ERROR"
            )
        except Exception as e:
            logger.exception(f"Error inesperado al sincronizar perfil: {str(e)}")
            raise ServiceError(
                status_code=500,
                detail="Error interno durante la sincronización de perfil",
                internal_code="SYNC_UNEXPECTED_ERROR"
            )