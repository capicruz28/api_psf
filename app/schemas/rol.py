# app/schemas/rol.py
"""
Esquemas Pydantic para la gestión de roles y permisos del sistema.

Este módulo define todos los esquemas de validación, creación, actualización 
y lectura de roles y sus permisos asociados sobre menús.

Los roles permiten agrupar permisos y asignarlos a usuarios de manera eficiente,
facilitando la gestión de accesos en el sistema.

Características principales:
- Validaciones robustas con mensajes de error en español
- Gestión completa de roles y permisos
- Validación de nombres únicos y reglas de negocio
- Documentación clara para desarrolladores
"""

from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict
from typing import Optional, List
from datetime import datetime
import re

class RolBase(BaseModel):
    """
    Schema base para roles con validaciones fundamentales.
    
    Define la estructura básica de un rol y establece las reglas de validación
    esenciales para mantener la seguridad del sistema.
    """
    
    nombre: str = Field(
        ...,
        min_length=3,
        max_length=50,
        description="Nombre único del rol para identificación en el sistema",
        examples=["Administrador", "Usuario", "Supervisor", "Reportes"]
    )
    
    descripcion: Optional[str] = Field(
        None,
        max_length=255,
        description="Descripción detallada del propósito y permisos del rol",
        examples=["Acceso completo al sistema", "Usuario estándar con permisos básicos"]
    )
    
    es_activo: bool = Field(
        True,
        description="Indica si el rol está activo y disponible para asignación"
    )

    @field_validator('nombre')
    @classmethod
    def validar_formato_nombre_rol(cls, valor: str) -> str:
        """
        Valida que el nombre del rol tenga un formato válido.
        
        Reglas:
        - Solo permite letras, números, espacios y caracteres especiales comunes
        - No permite caracteres especiales potencialmente peligrosos
        - Convierte a formato de título para consistencia
        
        Args:
            valor: El nombre del rol a validar
            
        Returns:
            str: Nombre del rol validado y normalizado
            
        Raises:
            ValueError: Cuando el formato no es válido
        """
        if not valor:
            raise ValueError('El nombre del rol no puede estar vacío')
        
        # Eliminar espacios en blanco al inicio y final
        valor = valor.strip()
        
        if not valor:
            raise ValueError('El nombre del rol no puede contener solo espacios')
        
        # Validar longitud después del trim
        if len(valor) < 3:
            raise ValueError('El nombre del rol debe tener al menos 3 caracteres')
        
        if len(valor) > 50:
            raise ValueError('El nombre del rol no puede exceder los 50 caracteres')
        
        # Patrón de caracteres permitidos: letras, números, espacios y caracteres especiales comunes
        patron_permitido = r"^[a-zA-Z0-9áéíóúÁÉÍÓÚñÑ\s\.,\-_()/!?@#$%&*+:=;'\"»«]+$"
        
        if not re.match(patron_permitido, valor):
            raise ValueError(
                'El nombre del rol contiene caracteres no permitidos. '
                'Solo se permiten letras, números, espacios y los siguientes caracteres especiales: '
                '.,-_()/!?@#$%&*+:=;\'"»«'
            )
        
        # Validar que no sea solo caracteres especiales
        if re.match(r"^[\s\.,\-_()/!?@#$%&*+:=;'\"]+$", valor):
            raise ValueError('El nombre del rol debe contener texto significativo, no solo caracteres especiales')
        
        # Formatear con capitalización adecuada
        return valor.title()

    @field_validator('descripcion')
    @classmethod
    def validar_descripcion_rol(cls, valor: Optional[str]) -> Optional[str]:
        """
        Valida el formato y contenido de la descripción del rol.
        
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

    @model_validator(mode='after')
    def validar_consistencia_nombre_rol(self) -> 'RolBase':  # 🔥 CORRECCIÓN: Usar string para forward reference
        """
        Valida consistencias adicionales después de procesar todos los campos.
        
        Realiza validaciones que requieren múltiples campos o que dependen
        de transformaciones realizadas en validadores individuales.
        """
        # Validar que el nombre no sea demasiado genérico
        nombres_genericos = ['rol', 'role', 'nuevo rol', 'nuevo role', 'test', 'prueba']
        if hasattr(self, 'nombre') and self.nombre.lower() in nombres_genericos:
            # Esto no es un error, pero podría ser una advertencia en logs
            pass
        
        return self

class RolCreate(RolBase):
    """
    Schema para la creación de nuevos roles.
    
    Extiende RolBase sin agregar campos adicionales, pero se utiliza
    para documentar específicamente la operación de creación.
    """
    pass

class RolUpdate(BaseModel):
    """
    Schema para actualización parcial de roles.
    
    Todos los campos son opcionales y solo se validan los que se proporcionen.
    Diseñado específicamente para operaciones PATCH que actualizan solo
    algunos campos del rol.
    """
    
    nombre: Optional[str] = Field(
        None,
        min_length=3,
        max_length=50,
        description="Nuevo nombre del rol (opcional)"
    )
    
    descripcion: Optional[str] = Field(
        None,
        max_length=255,
        description="Nueva descripción del rol (opcional)"
    )
    
    es_activo: Optional[bool] = Field(
        None,
        description="Nuevo estado activo/inactivo del rol (opcional)"
    )

    # Reutilizar validadores específicos para campos opcionales
    _validar_nombre_rol = field_validator('nombre')(RolBase.validar_formato_nombre_rol.__func__)
    _validar_descripcion = field_validator('descripcion')(RolBase.validar_descripcion_rol.__func__)

class RolRead(RolBase):
    """
    Schema para lectura de datos básicos de un rol.
    
    Incluye todos los campos de RolBase más metadatos del sistema
    que se generan automáticamente durante la creación del rol.
    """
    
    rol_id: int = Field(
        ...,
        description="Identificador único del rol en el sistema",
        examples=[1, 2, 3]
    )
    
    fecha_creacion: datetime = Field(
        ...,
        description="Fecha y hora en que se creó el registro del rol"
    )

    class Config:
        """Configuración de Pydantic para el schema."""
        from_attributes = True
        str_strip_whitespace = True
        validate_assignment = True

class PaginatedRolResponse(BaseModel):
    """
    Schema para respuestas paginadas de listas de roles.
    
    Utilizado en endpoints que devuelven listas paginadas de roles
    con metadatos de paginación para la navegación en interfaces.
    """
    
    roles: List[RolRead] = Field(
        ...,
        description="Lista de roles para la página actual"
    )
    
    total_roles: int = Field(
        ...,
        ge=0,
        description="Número total de roles que coinciden con los filtros aplicados"
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

class PermisoBase(BaseModel):
    """
    Schema base para permisos de roles sobre menús.
    
    Define los permisos básicos que un rol puede tener sobre un menú
    específico en el sistema.
    """
    
    menu_id: int = Field(
        ...,
        description="ID del menú al que aplican los permisos",
        examples=[1, 2, 3]
    )
    
    puede_ver: bool = Field(
        default=True,
        description="Permiso para ver/acceder al menú",
        examples=[True, False]
    )
    
    puede_editar: bool = Field(
        default=False,
        description="Permiso para editar contenido asociado al menú",
        examples=[True, False]
    )
    
    puede_eliminar: bool = Field(
        default=False,
        description="Permiso para eliminar contenido asociado al menú",
        examples=[True, False]
    )

    @field_validator('menu_id')
    @classmethod
    def validar_menu_id(cls, valor: int) -> int:
        """
        Valida que el ID del menú sea un valor positivo.
        
        Args:
            valor: ID del menú a validar
            
        Returns:
            int: ID del menú validado
            
        Raises:
            ValueError: Cuando el ID no es positivo
        """
        if valor < 1:
            raise ValueError('El ID del menú debe ser un número positivo')
        
        return valor

    model_config = ConfigDict(
        from_attributes=True,
        str_strip_whitespace=True,
        validate_assignment=True
    )

class PermisoRead(PermisoBase):
    """
    Schema para lectura de permisos existentes.
    
    Incluye todos los campos de PermisoBase más los identificadores
    de la relación rol-menú y el rol asociado.
    """
    
    rol_menu_id: int = Field(
        ...,
        description="ID único del registro de permiso en la tabla de relación",
        examples=[1, 2, 3]
    )
    
    rol_id: int = Field(
        ...,
        description="ID del rol al que pertenece el permiso",
        examples=[1, 2, 3]
    )

class PermisoUpdatePayload(BaseModel):
    """
    Schema para actualización masiva de permisos de un rol.
    
    Utilizado en operaciones que reemplazan todos los permisos
    de un rol con una nueva configuración.
    """
    
    permisos: List[PermisoBase] = Field(
        ...,
        description="Lista completa de permisos para asignar al rol",
        examples=[[
            {"menu_id": 1, "puede_ver": True, "puede_editar": False, "puede_eliminar": False},
            {"menu_id": 2, "puede_ver": True, "puede_editar": True, "puede_eliminar": False}
        ]]
    )

    @field_validator('permisos')
    @classmethod
    def validar_permisos_no_vacios(cls, valor: List[PermisoBase]) -> List[PermisoBase]:
        """
        Valida que la lista de permisos no esté vacía cuando se proporciona.
        
        Args:
            valor: Lista de permisos a validar
            
        Returns:
            List[PermisoBase]: Lista de permisos validada
            
        Raises:
            ValueError: Cuando la lista está vacía
        """
        if not valor:
            raise ValueError('La lista de permisos no puede estar vacía')
        
        return valor

    model_config = ConfigDict(
        from_attributes=True,
        str_strip_whitespace=True,
        validate_assignment=True
    )