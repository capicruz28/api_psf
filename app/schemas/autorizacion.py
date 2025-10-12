# app/schemas/autorizacion.py
from pydantic import BaseModel, Field
from datetime import datetime, time
from typing import Optional

class PendienteAutorizacionRead(BaseModel):
    """Schema para la respuesta del SP sp_pendiente_autorizacion"""
    fecha_destajo: datetime = Field(..., description="Fecha del destajo")
    cod_producto: str = Field(..., description="Código del producto")
    producto: str = Field(..., description="Nombre del producto")
    cod_subproceso: Optional[str] = Field(None, description="Código del subproceso")
    subproceso: Optional[str] = Field(None, description="Nombre del subproceso")
    cod_cliente: str = Field(..., description="Código del cliente")
    cliente: str = Field(..., description="Nombre del cliente")
    lote: str = Field(..., description="Lote")
    cod_proceso: str = Field(..., description="Código del proceso")
    proceso: str = Field(..., description="Nombre del proceso")
    cod_servicio: str = Field(..., description="Código del servicio")
    servicio: str = Field(..., description="Nombre del servicio")
    cos_costeo: str = Field(..., description="Código de costeo")
    costeo: str = Field(..., description="Nombre del costeo")
    cod_categoria: str = Field(..., description="Código de categoría")
    categoria: str = Field(..., description="Nombre de la categoría")
    cod_area: str = Field(..., description="Código del área")
    area: Optional[str] = Field(..., description="Nombre del área")
    cuadrilla: str = Field(..., description="Cuadrilla")
    inicio_proceso: Optional[datetime] = Field(None, description="Hora de inicio del proceso")
    hora_cierre: Optional[datetime] = Field(None, description="Hora de cierre")
    turno: str = Field(..., description="Turno")
    hora_inicio: Optional[datetime] = Field(None, description="Hora de inicio")
    hora_fin: Optional[datetime] = Field(None, description="Hora de fin")
    cod_trabajador: str = Field(..., description="Código del trabajador")
    trabajador: str = Field(..., description="Nombre completo del trabajador")
    horas: float = Field(..., description="Horas trabajadas")
    kilos: float = Field(..., description="Kilos procesados")
    tarifa: float = Field(..., description="Tarifa por hora/kilo")
    importe_total: float = Field(..., description="Importe total")
    estado_autorizado: str = Field(..., description="Estado de autorización (P=Pendiente, A=Autorizado, R=Rechazado)")
    observacion: Optional[str]  = Field(..., description="Observacion general")
    detalle_observacion: Optional[str]  = Field(..., description="Observacion por trabajador")
    fecha_autorizacion: Optional[datetime] = Field(..., description="Fecha del autorizacion")
    observacion_autorizacion: Optional[str]  = Field(..., description="Observacion de autorizacion")

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            time: lambda v: v.strftime("%H:%M:%S") if v else None
        }

class AutorizacionUpdate(BaseModel):
    """Schema para actualizar el estado de autorización"""
    lote: str = Field(..., description="Código del lote")
    fecha_destajo: datetime = Field(..., description="Fecha del destajo")
    cod_proceso: str = Field(..., description="Código del proceso")
    cod_subproceso: str = Field(..., description="Código del subproceso")
    nuevo_estado: str = Field(..., description="Nuevo estado de autorización (P=Pendiente, A=Autorizado, R=Rechazado)")
    observacion_autorizacion: str = Field(..., description="Observacion de la autorización")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class AutorizacionResponse(BaseModel):
    """Schema para la respuesta de autorización"""
    message: str = Field(..., description="Mensaje de confirmación")
    lote: str = Field(..., description="Código del lote autorizado")
    fecha_destajo: datetime = Field(..., description="Fecha del destajo")
    cod_proceso: str = Field(..., description="Código del proceso autorizado")
    cod_subproceso: str = Field(..., description="Código del subproceso autorizado")
    nuevo_estado: str = Field(..., description="Nuevo estado aplicado")
    observacion_autorizacion: str = Field(..., description="Observacion de la autorización")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class FinalizarTareoRequest(BaseModel):
    """Schema para actualizar el detalle de un tareo (cierre)"""
    fecha_destajo: datetime = Field(..., description="Fecha del destajo")
    lote: str = Field(..., description="Código del lote")
    cod_proceso: str = Field(..., description="Código del proceso")
    cod_subproceso: Optional[str] = Field(None, description="Código del subproceso")
    cod_trabajador: str = Field(..., description="Código del trabajador")
    hora_inicio: Optional[time] = Field(None, description="Hora de inicio")
    hora_fin: Optional[time] = Field(None, description="Hora de fin")
    horas: Optional[float] = Field(None, description="Cantidad de horas trabajadas")
    kilos: Optional[float] = Field(None, description="Cantidad de kilos procesados")
    observacion: Optional[str] = Field(None, description="Observación general")
    detalle_observacion: Optional[str] = Field(None, description="Observación específica del trabajador")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            time: lambda v: v.strftime("%H:%M:%S") if v else None
        }


class FinalizarTareoResponse(BaseModel):
    message: str = Field(..., description="Mensaje de confirmación")
    lote: str
    fecha_destajo: datetime
    cod_proceso: str
    cod_subproceso: Optional[str]
    cod_trabajador: str

class ReporteAutorizacionParams(BaseModel):
    """Parámetros para el SP sp_reporte_autorizacion_destajo"""
    fecha_inicio: datetime = Field(..., description="Fecha de inicio del rango")
    fecha_fin: datetime = Field(..., description="Fecha de fin del rango")