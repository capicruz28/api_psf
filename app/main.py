from typing import Any
import logging
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.exceptions import configure_exception_handlers
from app.api.v1.api import api_router
from app.db.connection import get_db_connection
from app.core.logging_config import setup_logging

# Configurar logging
setup_logging()
logger = logging.getLogger(__name__)

def create_application() -> FastAPI:
    """
    Crea y configura la aplicación FastAPI
    """
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        description=settings.DESCRIPTION,
        docs_url="/docs",
        redoc_url="/redoc",
        redirect_slashes=False  # ✅ Deshabilitar redirecciones automáticas
    )

    # CORS: orígenes explícitos y credenciales habilitadas
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Manejadores de excepciones custom
    configure_exception_handlers(app)

    # Rutas API v1
    app.include_router(api_router, prefix=settings.API_V1_STR)

    # Middleware de logging con timing
    @app.middleware("http")
    async def log_requests(request: Request, call_next: Any):
        start = time.perf_counter()
        logger.info(f"{request.client.host} -> {request.method} {request.url.path}")
        try:
            response = await call_next(request)
        finally:
            duration_ms = (time.perf_counter() - start) * 1000
            logger.info(f"{request.client.host} <- {request.method} {request.url.path} {duration_ms:.1f}ms")
        return response

    # Middleware para añadir headers de seguridad básicos a todas las respuestas
    @app.middleware("http")
    async def security_headers(request: Request, call_next: Any):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        return response

    return app

# Instancia de la aplicación
app = create_application()

# Rutas base
@app.get("/")
async def root():
    """
    Ruta raíz que muestra información básica de la API
    """
    return {
        "message": "Service API",
        "version": settings.VERSION,
        "docs": "/docs"
    }

@app.get("/health")
async def health_check():
    """
    Endpoint para verificar el estado de la aplicación y la conexión a la BD
    """
    try:
        with get_db_connection() as conn:
            db_status = "connected" if conn else "disconnected"
    except Exception as e:
        logger.error(f"Error en health check: {str(e)}")
        db_status = "error"

    return {
        "status": "healthy",
        "version": settings.VERSION,
        "database": db_status
    }

# Compatibilidad con código existente
@app.get("/api/test")
async def test_db():
    try:
        with get_db_connection() as conn:
            if conn:
                return {"message": "Conexión exitosa"}
            else:
                return {"error": "Conexión fallida: objeto de conexión es None"}
    except Exception as e:
        import traceback
        return {
            "error": str(e),
            "traceback": traceback.format_exc()
        }

@app.get("/drivers")
async def check_drivers():
    """Endpoint para verificar drivers ODBC disponibles"""
    from app.db.connection import test_drivers
    drivers = test_drivers()
    return {
        "drivers_available": list(drivers),
        "odbc_17_found": 'ODBC Driver 17 for SQL Server' in drivers
    }

@app.get("/debug-env")
async def debug_env():
    """Endpoint para verificar variables de entorno (sin mostrar passwords)"""
    return {
        "db_server": settings.DB_SERVER,
        "db_user": settings.DB_USER,
        "db_database": settings.DB_DATABASE,
        "db_port": settings.DB_PORT,
        "db_password_set": bool(settings.DB_PASSWORD),
        "secret_key_set": bool(settings.SECRET_KEY),
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level=settings.LOG_LEVEL.lower()
    )