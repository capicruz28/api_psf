# app/models/autorizacion.py
from pydantic import BaseModel
from datetime import datetime, time
from typing import Optional

class PendienteAutorizacion(BaseModel):
    fecha_destajo: datetime
    cod_producto: str
    producto: str
    cod_subproceso: Optional[str]
    subproceso: Optional[str]
    cod_cliente: str
    cliente: str
    lote: str
    cod_proceso: str
    proceso: str
    cod_servicio: str
    servicio: str
    cos_costeo: str
    costeo: str
    cod_categoria: str
    categoria: str
    cod_area: str
    area: str
    cuadrilla: str
    inicio_proceso: Optional[time]
    hora_cierre: Optional[time]
    turno: str
    hora_inicio: Optional[time]
    hora_fin: Optional[time]
    cod_trabajador: str
    trabajador: str
    horas: float
    kilos: float
    tarifa: float
    importe_total: float
    estado_autorizado: int
    observacion: str
    detalle_observacion: str

class AutorizacionUpdate(BaseModel):
    cod_trabajador: str
    fecha_destajo: datetime
    nuevo_estado: int = 1  # Por defecto autorizado