# app/api/v1/endpoints/autorizacion.py
from fastapi import APIRouter, HTTPException, Depends, status
from typing import List, Dict, Any

# Importar Schemas
from app.schemas.autorizacion import (
    PendienteAutorizacionRead,
    AutorizacionUpdate,
    AutorizacionResponse,
    FinalizarTareoRequest, 
    FinalizarTareoResponse,
    ReporteAutorizacionParams
)

# Importar Servicios
from app.services.autorizacion_service import AutorizacionService

# Importar Excepciones personalizadas
from app.core.exceptions import ServiceError, ValidationError

# Importar Dependencias de Autorización
from app.api.deps import get_current_active_user, RoleChecker

# Logging
from app.core.logging_config import get_logger
logger = get_logger(__name__)

router = APIRouter()

# Dependencia para requerir rol admin (ajusta según tus roles)
require_admin = RoleChecker(["Administrador"])

@router.get(
    "/pendientes/{codigo_trabajador_externo}/",  # ✅ CAMBIO: Agregado /
    response_model=List[PendienteAutorizacionRead],
    summary="Obtener procesos pendientes de autorización",
    description="Ejecuta el SP sp_pendiente_autorizacion y devuelve todos los registros pendientes. **Requiere rol 'Administrador'.**"
)
async def obtener_pendientes_autorizacion(codigo_trabajador_externo: str):
    """
    Obtiene todos los registros pendientes de autorización ejecutando el SP sp_pendiente_autorizacion.
    
    - Filtra registros con sautor = 0 (pendientes)
    - Incluye información completa del trabajador, proceso, cliente, etc.
    - Útil para generar reportes y mostrar en interfaces de autorización
    """
    try:
        logger.debug("Endpoint obtener_pendientes_autorizacion llamado")
        pendientes = await AutorizacionService.get_pendientes_autorizacion(codigo_trabajador_externo)
        
        # Los datos ya vienen como lista de diccionarios desde el service
        # FastAPI + Pydantic se encargan de validar contra PendienteAutorizacionRead
        return pendientes
        
    except ValidationError as e:
        logger.warning(f"Error de validación en obtener_pendientes_autorizacion: {e.detail}")
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except ServiceError as e:
        logger.error(f"Error de servicio en obtener_pendientes_autorizacion: {e.detail}")
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        logger.exception(f"Error inesperado en endpoint obtener_pendientes_autorizacion: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Error interno del servidor al obtener pendientes de autorización."
        )

@router.put(
    "/autorizar/",  # ✅ CAMBIO: Agregado /
    response_model=AutorizacionResponse,
    summary="Autorizar un proceso específico",
    description="Actualiza el campo sautor de un registro específico para autorizarlo. **Requiere rol 'Administrador'.**"
    
)
async def autorizar_proceso(
    autorizacion_data: AutorizacionUpdate
):
    """
    Autoriza un proceso específico actualizando el campo sautor en pdespe_supervisor00.
    
    - **lote**: lote del proceso a autorizar
    - **fecha_destajo**: Fecha del destajo (formato ISO)
    - **nuevo_estado**: Estado a aplicar (A = autorizado, R=rechazado, P=pendiente)
    """
    try:
        logger.debug(f"Endpoint autorizar_proceso llamado para el lote {autorizacion_data.lote}")
        
        resultado = await AutorizacionService.autorizar_proceso(
            lote=autorizacion_data.lote,
            fecha_destajo=autorizacion_data.fecha_destajo.isoformat(),
            cod_proceso=autorizacion_data.cod_proceso,
            cod_subproceso=autorizacion_data.cod_subproceso,
            nuevo_estado=autorizacion_data.nuevo_estado
        )
        
        # Construir respuesta estructurada
        response_data = {
            "message": resultado["message"],
            "lote": autorizacion_data.lote,
            "fecha_destajo": autorizacion_data.fecha_destajo,
            "cod_proceso": autorizacion_data.cod_proceso,
            "cod_subproceso": autorizacion_data.cod_subproceso,
            "nuevo_estado": autorizacion_data.nuevo_estado
        }
        
        return response_data
        
    except ValidationError as e:
        logger.warning(f"Error de validación en autorizar_proceso: {e.detail}")
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except ServiceError as e:
        logger.error(f"Error de servicio en autorizar_proceso: {e.detail}")
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        logger.exception(f"Error inesperado en endpoint autorizar_proceso: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Error interno del servidor al autorizar el proceso."
        )

@router.get(
    "/pendientes/count/",  # ✅ CAMBIO: Agregado /
    response_model=Dict[str, Any],
    summary="Obtener conteo de procesos pendientes",
    description="Devuelve solo el número total de registros pendientes de autorización. **Requiere autenticación.**",
    dependencies=[Depends(get_current_active_user)]
)
async def contar_pendientes():
    """
    Obtiene únicamente el conteo de registros pendientes de autorización.
    
    Útil para dashboards y widgets que solo necesitan mostrar números sin cargar todos los datos.
    """
    try:
        logger.debug("Endpoint contar_pendientes llamado")
        conteo = await AutorizacionService.get_conteo_pendientes()
        return conteo
        
    except ServiceError as e:
        logger.error(f"Error de servicio en contar_pendientes: {e.detail}")
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        logger.exception(f"Error inesperado en endpoint contar_pendientes: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Error interno del servidor al contar pendientes."
        )

@router.put(
    "/autorizar-multiple/",  # ✅ CAMBIO: Agregado /
    response_model=Dict[str, Any],
    summary="Autorizar múltiples procesos",
    description="Autoriza varios procesos en una sola operación. **Requiere rol 'Administrador'.**"
)
async def autorizar_procesos_multiple(
    autorizaciones: List[AutorizacionUpdate]
):
    """
    Autoriza múltiples procesos en una sola operación.
    
    - Recibe una lista de objetos AutorizacionUpdate
    - Procesa cada uno individualmente
    - Devuelve un resumen con exitosos, fallidos y errores
    """
    try:
        logger.debug(f"Endpoint autorizar_procesos_multiple llamado con {len(autorizaciones)} registros")
        
        if not autorizaciones:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La lista de autorizaciones no puede estar vacía"
            )
        
        # Convertir a lista de diccionarios para el service
        autorizaciones_dict = [auth.model_dump() for auth in autorizaciones]
        
        resultado = await AutorizacionService.autorizar_multiple(autorizaciones_dict)
        return resultado
        
    except ValidationError as e:
        logger.warning(f"Error de validación en autorizar_procesos_multiple: {e.detail}")
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except ServiceError as e:
        logger.error(f"Error de servicio en autorizar_procesos_multiple: {e.detail}")
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        logger.exception(f"Error inesperado en endpoint autorizar_procesos_multiple: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Error interno del servidor al autorizar múltiples procesos."
        )

@router.put(
    "/finalizar-tareo/",  # ✅ CAMBIO: Agregado /
    response_model=FinalizarTareoResponse,
    summary="Finalizar un tareo",
    description="Actualiza hora_inicio, hora_fin, horas, kilos, observaciones de un trabajador en un lote/proceso/subproceso/fecha."
)
async def finalizar_tareo(data: FinalizarTareoRequest):
    try:
        resultado = await AutorizacionService.finalizar_tareo(data.model_dump())
        return resultado
    except ValidationError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except ServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        logger.exception(f"Error inesperado en endpoint finalizar_tareo: {e}")
        raise HTTPException(
            status_code=500,
            detail="Error interno del servidor al finalizar el tareo."
        )

@router.post(
    "/reporte/",  # ✅ CAMBIO: Agregado /
    response_model=List[PendienteAutorizacionRead],
    summary="Obtener reporte de autorización",
    description="Ejecuta el SP sp_reporte_autorizacion_destajo con rango de fechas. **Requiere rol 'Administrador'.**"
)
async def obtener_reporte_autorizacion(params: ReporteAutorizacionParams):
    """
    Obtiene todos los registros del reporte de autorización en un rango de fechas especificado.
    - **fecha_inicio**: Fecha inicial del rango
    - **fecha_fin**: Fecha final del rango
    """
    try:
        logger.debug(f"Endpoint obtener_reporte_autorizacion llamado")
        reporte = await AutorizacionService.get_reporte_autorizacion(
            fecha_inicio=params.fecha_inicio.isoformat(),
            fecha_fin=params.fecha_fin.isoformat(),
            codigo_trabajador_externo=params.codigo_trabajador_externo
        )
        return reporte
    except ValidationError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except ServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        logger.exception(f"Error inesperado en endpoint obtener_reporte_autorizacion: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor al obtener reporte de autorización."
        )