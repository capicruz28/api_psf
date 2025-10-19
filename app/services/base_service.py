# app/services/base_service.py
from typing import Any, Dict, Optional
import logging
from functools import wraps

from app.core.exceptions import (
    DatabaseError, ValidationError, NotFoundError, 
    ServiceError, ConflictError
)

logger = logging.getLogger(__name__)

class BaseService:
    """
    Clase base para todos los servicios con manejo estandarizado de errores.
    
    IMPORTANTE: Todos los servicios deben heredar de esta clase para garantizar
    consistencia en el manejo de errores y validaciones.
    """
    
    @staticmethod
    def handle_service_errors(func):
        """
        Decorator para manejo consistente de errores en métodos de servicio.
        
        🎯 PROPÓSITO: Evitar la repetición de bloques try-catch en cada método
        y garantizar que todos los errores se manejen de manera consistente.
        
        USO: Colocar @handle_service_errors encima de cada método de servicio
        que realice operaciones que puedan fallar.
        """
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                # 🔄 Ejecutar el método original
                return await func(*args, **kwargs)
                
            except (ValidationError, NotFoundError, ConflictError, ServiceError):
                # ✅ RE-LANZAR EXCEPCIONES CONOCIDAS: 
                # Estas ya están bien definidas y tienen el contexto apropiado
                raise
                
            except DatabaseError as db_err:
                # 🗄️ ERRORES DE BD: Loggear y relanzar sin cambios
                # Estos son errores específicos que queremos trackear separadamente
                logger.error(f"DatabaseError en {func.__name__}: {db_err.detail}", exc_info=True)
                raise
                
            except Exception as e:
                # 🚨 CAPTURA DE SEGURIDAD: Cualquier error inesperado
                # Esto previene que excepciones no manejadas lleguen al usuario final
                logger.exception(f"ERROR INESPERADO en {func.__name__}: {str(e)}")
                raise ServiceError(
                    status_code=500, 
                    detail=f"Error interno del servidor en {func.__name__}",
                    internal_code="INTERNAL_SERVICE_ERROR"
                )
        return wrapper
    
    @staticmethod
    def validate_required_fields(data: Dict, required_fields: list, context: str = ""):
        """
        Valida que los campos requeridos estén presentes.
        
        🛡️ SEGURIDAD: Previene operaciones con datos incompletos que podrían
        causar errores de base de datos o comportamientos inesperados.
        
        Ejemplo de uso:
        BaseService.validate_required_fields(
            usuario_data, 
            ['nombre', 'email'], 
            'creación de usuario'
        )
        """
        missing_fields = [field for field in required_fields if field not in data or data[field] is None]
        if missing_fields:
            raise ValidationError(
                detail=f"Campos requeridos faltantes en {context}: {', '.join(missing_fields)}",
                internal_code="MISSING_REQUIRED_FIELDS"
            )
    
    @staticmethod
    def validate_string_length(value: str, max_length: int, field_name: str):
        """
        Valida la longitud máxima de un string.
        
        📏 PREVENCIÓN: Evita que se inserten datos que excedan los límites
        de la base de datos, previniendo errores de truncamiento.
        """
        if value and len(value) > max_length:
            raise ValidationError(
                detail=f"El campo {field_name} excede la longitud máxima de {max_length} caracteres",
                internal_code="FIELD_TOO_LONG"
            )
    
    @staticmethod
    def validate_numeric_range(value: Optional[float], min_val: float, max_val: float, field_name: str):
        """
        Valida que un valor numérico esté dentro de un rango permitido.
        
        📊 VALIDACIÓN DE DOMINIO: Útil para valores como precios, cantidades, 
        porcentajes, etc., que deben estar en rangos específicos.
        """
        if value is not None and (value < min_val or value > max_val):
            raise ValidationError(
                detail=f"El campo {field_name} debe estar entre {min_val} y {max_val}",
                internal_code="VALUE_OUT_OF_RANGE"
            )

    @staticmethod
    def log_operation_success(operation: str, resource_id: Any, additional_info: str = ""):
        """
        Log estandarizado para operaciones exitosas.
        
        📝 AUDITORÍA: Proporciona trazabilidad de las operaciones realizadas
        en el sistema para debugging y monitoreo.
        """
        logger.info(f"{operation} exitoso - ID: {resource_id} {additional_info}".strip())

    @staticmethod
    def log_operation_failure(operation: str, resource_id: Any, error: str):
        """
        Log estandarizado para operaciones fallidas.
        
        🐛 DEBUGGING: Ayuda a identificar rápidamente problemas sin exponer
        detalles sensibles al usuario final.
        """
        logger.warning(f"{operation} fallido - ID: {resource_id} - Error: {error}")