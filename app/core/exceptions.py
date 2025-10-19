# app/core/exceptions.py
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import logging

logger = logging.getLogger(__name__)

class CustomException(Exception):
    """
    Excepción base personalizada para toda la aplicación.
    
    ATENCIÓN: Esta es la clase base de la que heredan todas nuestras excepciones personalizadas.
    Permite un manejo consistente de errores en toda la aplicación.
    """
    def __init__(self, status_code: int, detail: str, internal_code: str = None):
        self.status_code = status_code
        self.detail = detail
        self.internal_code = internal_code  # Código interno para tracking y debugging
        super().__init__(self.detail)

class DatabaseError(CustomException):
    """
    Errores específicos de base de datos.
    
    IMPORTANTE: Se usa para errores relacionados directamente con operaciones de BD.
    Ej: conexiones fallidas, timeouts, errores de consultas SQL.
    """
    def __init__(self, detail: str, internal_code: str = "DB_ERROR"):
        super().__init__(status_code=500, detail=detail, internal_code=internal_code)

class ValidationError(CustomException):
    """
    Errores de validación de datos de entrada del cliente.
    
    USO: Cuando los datos enviados por el cliente no cumplen con las validaciones.
    Ej: campos requeridos faltantes, formatos inválidos, valores fuera de rango.
    """
    def __init__(self, detail: str, internal_code: str = "VALIDATION_ERROR"):
        super().__init__(status_code=400, detail=detail, internal_code=internal_code)

class NotFoundError(CustomException):
    """
    Recursos no encontrados.
    
    USO: Cuando un recurso específico (usuario, área, menú) no existe en la BD.
    Ej: GET /areas/999 donde 999 no existe.
    """
    def __init__(self, detail: str, internal_code: str = "NOT_FOUND"):
        super().__init__(status_code=404, detail=detail, internal_code=internal_code)

class ServiceError(CustomException):
    """
    Errores de lógica de negocio y servicios.
    
    USO: Para errores específicos de la lógica de negocio que no son de validación.
    Ej: operaciones que fallan por reglas de negocio, estados inconsistentes.
    """
    def __init__(self, status_code: int, detail: str, internal_code: str = "SERVICE_ERROR"):
        super().__init__(status_code=status_code, detail=detail, internal_code=internal_code)

class AuthenticationError(CustomException):
    """
    Errores de autenticación y autorización.
    
    USO: Problemas con credenciales, tokens inválidos o expirados.
    """
    def __init__(self, detail: str, internal_code: str = "AUTH_ERROR"):
        super().__init__(status_code=401, detail=detail, internal_code=internal_code)

class AuthorizationError(CustomException):
    """
    Errores de permisos y acceso.
    
    USO: Cuando un usuario autenticado no tiene permisos para una operación.
    Ej: usuario regular intentando acceder a endpoint de administrador.
    """
    def __init__(self, detail: str, internal_code: str = "AUTHZ_ERROR"):
        super().__init__(status_code=403, detail=detail, internal_code=internal_code)

class ConflictError(CustomException):
    """
    Conflictos de datos (ej: duplicados).
    
    USO: Cuando hay conflictos con el estado actual de los datos.
    Ej: crear un área con nombre que ya existe, email duplicado.
    """
    def __init__(self, detail: str, internal_code: str = "CONFLICT_ERROR"):
        super().__init__(status_code=409, detail=detail, internal_code=internal_code)

def configure_exception_handlers(app: FastAPI):
    """
    Configura los manejadores de excepciones globales para FastAPI.
    
    NOTA: Esto asegura que todas nuestras excepciones personalizadas se conviertan
    en respuestas HTTP consistentes con el formato correcto.
    """
    @app.exception_handler(CustomException)
    async def custom_exception_handler(request: Request, exc: CustomException):
        # Loggear el error con contexto para debugging
        logger.error(
            f"CustomException: {exc.internal_code} - {exc.detail} | "
            f"Path: {request.url.path} | Method: {request.method}"
        )
        
        # 🔒 SEGURIDAD: En producción, no exponer detalles internos de errores 5xx
        response_detail = exc.detail
        if exc.status_code >= 500:
            response_detail = "Error interno del servidor"
            
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "detail": response_detail,
                "error_code": exc.internal_code  # 🎯 Útil para el frontend
            }
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        """
        Manejador de último recurso para cualquier error no capturado.
        
        IMPORTANTE: Esto previene que se filtren detalles internos del servidor
        y asegura una respuesta consistente incluso para errores inesperados.
        """
        logger.exception(f"Error no manejado: {str(exc)}")
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Error interno del servidor",
                "error_code": "INTERNAL_ERROR"
            }
        )