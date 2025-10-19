# app/schemas/area.py
"""
Esquemas Pydantic para la gestión de áreas de menú en el sistema.

Este módulo define todos los esquemas de validación, creación, actualización 
y lectura de áreas, que representan las secciones principales del sistema
a las que pertenecen los diferentes menús.

Las áreas organizan los menús en grupos lógicos y facilitan la navegación
y administración del sistema de menús.

Características principales:
- Validaciones robustas con mensajes de error en español
- Gestión completa de áreas y su relación con menús
- Validación de nombres únicos y reglas de negocio
- Documentación clara para desarrolladores
"""

from pydantic import BaseModel, Field, field_validator, model_validator
from typing import List, Optional
from datetime import datetime
import re

class AreaBase(BaseModel):
    """
    Schema base para áreas con validaciones fundamentales.
    
    Define la estructura básica de un área y establece las reglas de validación
    esenciales para mantener la organización del sistema de menús.
    """
    
    nombre: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Nombre único del área para identificación en el sistema",
        examples=["Administración", "Procesos", "Reportes", "Configuración"]
    )
    
    descripcion: Optional[str] = Field(
        None,
        max_length=255,
        description="Descripción detallada del propósito y contenido del área",
        examples=["Gestión de usuarios, roles y permisos del sistema",
                 "Procesos operativos y flujos de trabajo principales"]
    )
    
    icono: Optional[str] = Field(
        None,
        max_length=50,
        description="Nombre del icono para representar el área en la interfaz",
        examples=["settings", "dashboard", "reports", "users"]
    )
    
    es_activo: bool = Field(
        True,
        description="Indica si el área está activa y disponible para uso"
    )

    @field_validator('nombre')
    @classmethod
    def validar_formato_nombre_area(cls, valor: str) -> str:
        """
        Valida que el nombre del área tenga un formato válido.
        
        Reglas:
        - Solo permite letras, números, espacios y caracteres especiales comunes
        - No permite caracteres especiales potencialmente peligrosos
        - Convierte a formato de título para consistencia
        
        Args:
            valor: El nombre del área a validar
            
        Returns:
            str: Nombre del área validado y normalizado
            
        Raises:
            ValueError: Cuando el formato no es válido
        """
        if not valor:
            raise ValueError('El nombre del área no puede estar vacío')
        
        # Eliminar espacios en blanco al inicio y final
        valor = valor.strip()
        
        if not valor:
            raise ValueError('El nombre del área no puede contener solo espacios')
        
        # Validar longitud después del trim
        if len(valor) < 1:
            raise ValueError('El nombre del área debe tener al menos 1 carácter')
        
        if len(valor) > 100:
            raise ValueError('El nombre del área no puede exceder los 100 caracteres')
        
        # Patrón de caracteres permitidos: letras, números, espacios y caracteres especiales comunes
        # CORREGIDO: Usamos comillas dobles para la cadena y escapamos las comillas simples internas
        patron_permitido = r"^[a-zA-Z0-9áéíóúÁÉÍÓÚñÑ\s\.,\-_()/!?@#$%&*+:=;'\"»«]+$"
        
        if not re.match(patron_permitido, valor):
            raise ValueError(
                'El nombre del área contiene caracteres no permitidos. '
                'Solo se permiten letras, números, espacios y los siguientes caracteres especiales: '
                '.,-_()/!?@#$%&*+:=;\'"»«'
            )
        
        # Validar que no sea solo caracteres especiales
        if re.match(r"^[\s\.,\-_()/!?@#$%&*+:=;'\"]+$", valor):
            raise ValueError('El nombre del área debe contener texto significativo, no solo caracteres especiales')
        
        # Formatear con capitalización adecuada
        return valor.title()

    @field_validator('descripcion')
    @classmethod
    def validar_descripcion_area(cls, valor: Optional[str]) -> Optional[str]:
        """
        Valida el formato y contenido de la descripción del área.
        
        Permite una amplia gama de caracteres para descripciones detalladas
        pero previene contenido potencialmente peligroso.
        
        Args:
            valor: La descripción a validar
            
        Returns:
            Optional[str]: Descripción validada y normalizada
            
        Raises:
            ValueError: Cuando la descripción contiene caracteres no permitidos
        """
        if valor is None:
            return None
        
        valor = valor.strip()
        
        if not valor:
            return None
        
        # Validar longitud máxima
        if len(valor) > 255:
            raise ValueError('La descripción no puede exceder los 255 caracteres')
        
        # Patrón más flexible para descripciones
        patron_descripcion = r"^[a-zA-Z0-9áéíóúÁÉÍÓÚñÑ\s\.,;:\-\_\(\)\!\?\@\#\$\%\&\*\+\=\[\]\{\}\"\'»«]+$"
        
        if not re.match(patron_descripcion, valor):
            raise ValueError(
                'La descripción contiene caracteres no permitidos. '
                'Solo se permiten letras, números, espacios y signos de puntuación comunes.'
            )
        
        return valor

    @field_validator('icono')
    @classmethod
    def validar_formato_icono(cls, valor: Optional[str]) -> Optional[str]:
        """
        Valida el formato del nombre del icono.
        
        Los iconos típicamente son nombres de clases CSS o identificadores
        de sistemas de iconos como FontAwesome, Material Icons, etc.
        
        Args:
            valor: El nombre del icono a validar
            
        Returns:
            Optional[str]: Nombre del icono validado y normalizado
            
        Raises:
            ValueError: Cuando el formato del icono no es válido
        """
        if valor is None:
            return None
        
        valor = valor.strip().lower()
        
        if not valor:
            return None
        
        # Validar longitud
        if len(valor) > 50:
            raise ValueError('El nombre del icono no puede exceder los 50 caracteres')
        
        # Validar formato: solo letras, números, guiones y guiones bajos
        if not re.match(r'^[a-z0-9_\-]+$', valor):
            raise ValueError(
                'El nombre del icono solo puede contener letras minúsculas, números, '
                'guiones y guiones bajos. Ejemplos: "settings", "user-profile", "dashboard"'
            )
        
        return valor

    @model_validator(mode='after')
    def validar_consistencia_nombre_area(self) -> 'AreaBase':
        """
        Valida consistencias adicionales después de procesar todos los campos.
        
        Realiza validaciones que requieren múltiples campos o que dependen
        de transformaciones realizadas en validadores individuales.
        """
        # Validar que el nombre no sea demasiado genérico
        nombres_genericos = ['área', 'area', 'nueva área', 'nuevo área', 'test', 'prueba']
        if hasattr(self, 'nombre') and self.nombre.lower() in nombres_genericos:
            # Esto no es un error, pero podría ser una advertencia en logs
            pass
        
        return self

class AreaCreate(AreaBase):
    """
    Schema para la creación de nuevas áreas.
    
    Extiende AreaBase sin agregar campos adicionales, pero se utiliza
    para documentar específicamente la operación de creación.
    """
    pass

class AreaUpdate(BaseModel):
    """
    Schema para actualización parcial de áreas.
    
    Todos los campos son opcionales y solo se validan los que se proporcionen.
    Diseñado específicamente para operaciones PATCH que actualizan solo
    algunos campos del área.
    """
    
    nombre: Optional[str] = Field(
        None,
        min_length=1,
        max_length=100,
        description="Nuevo nombre del área (opcional)"
    )
    
    descripcion: Optional[str] = Field(
        None,
        max_length=255,
        description="Nueva descripción del área (opcional)"
    )
    
    icono: Optional[str] = Field(
        None,
        max_length=50,
        description="Nuevo icono del área (opcional)"
    )
    
    es_activo: Optional[bool] = Field(
        None,
        description="Nuevo estado activo/inactivo del área (opcional)"
    )

    # Reutilizar validadores específicos para campos opcionales
    _validar_nombre_area = field_validator('nombre')(AreaBase.validar_formato_nombre_area.__func__)
    _validar_descripcion = field_validator('descripcion')(AreaBase.validar_descripcion_area.__func__)
    _validar_icono = field_validator('icono')(AreaBase.validar_formato_icono.__func__)

class AreaRead(AreaBase):
    """
    Schema para lectura de datos básicos de un área.
    
    Incluye todos los campos de AreaBase más metadatos del sistema
    que se generan automáticamente durante la creación del área.
    """
    
    area_id: int = Field(
        ...,
        ge=1,
        description="Identificador único del área en el sistema"
    )
    
    fecha_creacion: datetime = Field(
        ...,
        description="Fecha y hora en que se creó el registro del área"
    )

    class Config:
        """Configuración de Pydantic para el schema."""
        from_attributes = True
        str_strip_whitespace = True
        validate_assignment = True

class AreaSimpleList(BaseModel):
    """
    Schema simplificado para listas de áreas activas.
    
    Utilizado en endpoints que requieren listas desplegables o selectores
    donde solo se necesitan los datos básicos de identificación.
    """
    
    area_id: int = Field(
        ...,
        description="Identificador único del área"
    )
    
    nombre: str = Field(
        ...,
        description="Nombre del área para mostrar en interfaces"
    )

    class Config:
        """Configuración para el schema simplificado."""
        from_attributes = True

class PaginatedAreaResponse(BaseModel):
    """
    Schema para respuestas paginadas de listas de áreas.
    
    Utilizado en endpoints que devuelven listas paginadas de áreas
    con metadatos de paginación para la navegación en interfaces.
    """
    
    areas: List[AreaRead] = Field(
        ...,
        description="Lista de áreas para la página actual"
    )
    
    total_areas: int = Field(
        ...,
        ge=0,
        description="Número total de áreas que coinciden con los filtros aplicados"
    )
    
    pagina_actual: int = Field(
        ...,
        ge=1,
        description="Número de la página actual siendo visualizada"
    )
    
    total_paginas: int = Field(
        ...,
        ge=0,
        description="Número total de páginas disponibles con los filtros actuales"
    )

    class Config:
        """Configuración para respuestas paginadas."""
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }