# app/schemas/menu.py
"""
Esquemas Pydantic para la gestión de menús del sistema.

Este módulo define todos los esquemas de validación, creación, actualización 
y lectura de menús, que representan la estructura de navegación del sistema.

Los menús organizan las funcionalidades del sistema en una estructura jerárquica
que se presenta a los usuarios según sus roles y permisos.

Características principales:
- Validaciones robustas con mensajes de error en español
- Gestión completa de la jerarquía de menús
- Validación de relaciones con áreas y menús padres
- Documentación clara para desarrolladores
"""

from __future__ import annotations
from pydantic import BaseModel, Field, field_validator, model_validator
from typing import List, Optional, Dict, Any
from datetime import datetime
import re

class MenuBase(BaseModel):
    """
    Schema base para menús con validaciones fundamentales.
    
    Define la estructura básica de un ítem de menú y establece las reglas 
    de validación esenciales para mantener la organización del sistema.
    """
    
    nombre: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Nombre único del menú para identificación en el sistema",
        examples=["Dashboard", "Gestión de Usuarios", "Reportes", "Configuración"]
    )
    
    icono: Optional[str] = Field(
        None,
        max_length=50,
        description="Nombre del icono para representar el menú en la interfaz",
        examples=["dashboard", "users", "reports", "settings", "folder"]
    )
    
    ruta: Optional[str] = Field(
        None,
        max_length=255,
        description="Ruta o URL a la que dirige el menú",
        examples=["/dashboard", "/usuarios", "/reportes/ventas"]
    )
    
    padre_menu_id: Optional[int] = Field(
        None,
        description="ID del menú padre para crear estructuras jerárquicas",
        examples=[1, 2, 3]
    )
    
    orden: Optional[int] = Field(
        None,
        ge=0,
        description="Orden de visualización dentro del mismo nivel",
        examples=[1, 2, 3, 10, 20]
    )
    
    area_id: Optional[int] = Field(
        None,
        description="ID del área a la que pertenece el menú",
        examples=[1, 2, 3]
    )
    
    es_activo: bool = Field(
        True,
        description="Indica si el menú está activo y disponible para uso"
    )

    @field_validator('nombre')
    @classmethod
    def validar_formato_nombre_menu(cls, valor: str) -> str:
        """
        Valida que el nombre del menú tenga un formato válido.
        
        Reglas:
        - Solo permite letras, números, espacios y caracteres especiales comunes
        - No permite caracteres especiales potencialmente peligrosos
        - Convierte a formato de título para consistencia
        
        Args:
            valor: El nombre del menú a validar
            
        Returns:
            str: Nombre del menú validado y normalizado
            
        Raises:
            ValueError: Cuando el formato no es válido
        """
        if not valor:
            raise ValueError('El nombre del menú no puede estar vacío')
        
        # Eliminar espacios en blanco al inicio y final
        valor = valor.strip()
        
        if not valor:
            raise ValueError('El nombre del menú no puede contener solo espacios')
        
        # Validar longitud después del trim
        if len(valor) < 1:
            raise ValueError('El nombre del menú debe tener al menos 1 carácter')
        
        if len(valor) > 100:
            raise ValueError('El nombre del menú no puede exceder los 100 caracteres')
        
        # Patrón de caracteres permitidos: letras, números, espacios y caracteres especiales comunes
        patron_permitido = r"^[a-zA-Z0-9áéíóúÁÉÍÓÚñÑ\s\.,\-_()/!?@#$%&*+:=;'\"»«]+$"
        
        if not re.match(patron_permitido, valor):
            raise ValueError(
                'El nombre del menú contiene caracteres no permitidos. '
                'Solo se permiten letras, números, espacios y los siguientes caracteres especiales: '
                '.,-_()/!?@#$%&*+:=;\'"»«'
            )
        
        # Validar que no sea solo caracteres especiales
        if re.match(r"^[\s\.,\-_()/!?@#$%&*+:=;'\"]+$", valor):
            raise ValueError('El nombre del menú debe contener texto significativo, no solo caracteres especiales')
        
        # Formatear con capitalización adecuada
        return valor.title()

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
        
        valor = valor.strip()
        
        if not valor:
            return None
        
        # Validar longitud
        if len(valor) > 50:
            raise ValueError('El nombre del icono no puede exceder los 50 caracteres')
        
        # Validar formato: solo letras, números, guiones y guiones bajos
        if not re.match(r'^[a-zA-Z0-9_\-]+$', valor):
            raise ValueError(
                'El nombre del icono solo puede contener letras minúsculas/mayusculas, números, '
                'guiones y guiones bajos. Ejemplos: "dashboard", "user-cog", "file-text"'
            )
        
        return valor

    @field_validator('ruta')
    @classmethod
    def validar_formato_ruta(cls, valor: Optional[str]) -> Optional[str]:
        """
        Valida el formato de la ruta del menú.
        
        Las rutas deben seguir convenciones de URL y ser seguras para
        la navegación en el sistema.
        
        Args:
            valor: La ruta a validar
            
        Returns:
            Optional[str]: Ruta validada y normalizada
            
        Raises:
            ValueError: Cuando el formato de la ruta no es válido
        """
        if valor is None:
            return None
        
        valor = valor.strip()
        
        if not valor:
            return None
        
        # Validar longitud
        if len(valor) > 255:
            raise ValueError('La ruta no puede exceder los 255 caracteres')
        
        # Validar que comience con slash
        if not valor.startswith('/'):
            raise ValueError('La ruta debe comenzar con "/"')
        
        # Validar caracteres permitidos en rutas
        patron_ruta = r"^[/a-zA-Z0-9\-_\.~!$&'()*+,;=:@%]+$"
        if not re.match(patron_ruta, valor):
            raise ValueError(
                'La ruta contiene caracteres no permitidos. '
                'Solo se permiten letras, números, guiones y caracteres seguros para URLs.'
            )
        
        # Validar que no tenga espacios
        if ' ' in valor:
            raise ValueError('La ruta no puede contener espacios')
        
        return valor

    @field_validator('orden')
    @classmethod
    def validar_orden_menu(cls, valor: Optional[int]) -> Optional[int]:
        """
        Valida que el orden sea un valor positivo.
        
        Args:
            valor: El orden a validar
            
        Returns:
            Optional[int]: Orden validado
            
        Raises:
            ValueError: Cuando el orden es negativo
        """
        if valor is not None and valor < 0:
            raise ValueError('El orden no puede ser negativo')
        
        return valor

    @model_validator(mode='after')
    def validar_consistencia_menu(self) -> MenuBase:
        """
        Valida consistencias adicionales después de procesar todos los campos.
        
        Realiza validaciones que requieren múltiples campos o que dependen
        de transformaciones realizadas en validadores individuales.
        """
        # Validar que menús con ruta no tengan hijos (esto se validaría en el servicio)
        # Aquí solo podemos hacer validaciones básicas
        
        # Validar que el nombre no sea demasiado genérico
        nombres_genericos = ['menú', 'menu', 'nuevo menú', 'nuevo menu', 'test', 'prueba']
        if hasattr(self, 'nombre') and self.nombre.lower() in nombres_genericos:
            # Esto no es un error, pero podría ser una advertencia en logs
            pass
        
        return self

class MenuCreate(MenuBase):
    """
    Schema para la creación de nuevos menús.
    
    Extiende MenuBase sin agregar campos adicionales, pero se utiliza
    para documentar específicamente la operación de creación.
    """
    pass

class MenuUpdate(BaseModel):
    """
    Schema para actualización parcial de menús.
    
    Todos los campos son opcionales y solo se validan los que se proporcionen.
    Diseñado específicamente para operaciones PATCH que actualizan solo
    algunos campos del menú.
    """
    
    nombre: Optional[str] = Field(
        None,
        min_length=1,
        max_length=100,
        description="Nuevo nombre del menú (opcional)"
    )
    
    icono: Optional[str] = Field(
        None,
        max_length=50,
        description="Nuevo icono del menú (opcional)"
    )
    
    ruta: Optional[str] = Field(
        None,
        max_length=255,
        description="Nueva ruta del menú (opcional)"
    )
    
    padre_menu_id: Optional[int] = Field(
        None,
        description="Nuevo ID del menú padre (opcional)"
    )
    
    orden: Optional[int] = Field(
        None,
        ge=0,
        description="Nuevo orden de visualización (opcional)"
    )
    
    area_id: Optional[int] = Field(
        None,
        description="Nuevo ID del área (opcional)"
    )
    
    es_activo: Optional[bool] = Field(
        None,
        description="Nuevo estado activo/inactivo del menú (opcional)"
    )

    # Reutilizar validadores específicos para campos opcionales
    _validar_nombre_menu = field_validator('nombre')(MenuBase.validar_formato_nombre_menu.__func__)
    _validar_icono = field_validator('icono')(MenuBase.validar_formato_icono.__func__)
    _validar_ruta = field_validator('ruta')(MenuBase.validar_formato_ruta.__func__)
    _validar_orden = field_validator('orden')(MenuBase.validar_orden_menu.__func__)

class MenuItem(BaseModel):
    """
    Schema para ítems de menú en estructuras jerárquicas.
    
    Utilizado para representar la estructura completa del menú
    con relaciones padre-hijo para el frontend.
    """
    
    menu_id: int = Field(
        ...,
        description="Identificador único del menú en el sistema",
        examples=[1, 2, 3]
    )
    
    nombre: str = Field(
        ...,
        description="Nombre del menú para mostrar en la interfaz",
        examples=["Dashboard", "Usuarios", "Configuración"]
    )
    
    icono: Optional[str] = Field(
        None,
        description="Icono asociado al menú",
        examples=["dashboard", "users", "settings"]
    )
    
    ruta: Optional[str] = Field(
        None,
        description="Ruta de navegación del menú",
        examples=["/dashboard", "/usuarios", "/configuracion"]
    )
    
    orden: Optional[int] = Field(
        None,
        description="Orden de visualización",
        examples=[1, 2, 3]
    )
    
    es_activo: bool = Field(
        ...,
        description="Indica si el menú está activo",
        examples=[True, False]
    )
    
    area_id: Optional[int] = Field(
        None,
        description="ID del área a la que pertenece el menú",
        examples=[1, 2, 3]
    )
    
    area_nombre: Optional[str] = Field(
        None,
        description="Nombre del área a la que pertenece el menú",
        examples=["Administración", "Operaciones", "Reportes"]
    )
    
    level: Optional[int] = Field(
        None,
        description="Nivel en la jerarquía del menú",
        examples=[1, 2, 3]
    )
    
    children: List[MenuItem] = Field(
        default_factory=list,
        description="Lista de menús hijos (estructura jerárquica)"
    )

    class Config:
        """Configuración de Pydantic para el schema jerárquico."""
        from_attributes = True

class MenuResponse(BaseModel):
    """
    Schema para respuestas de estructuras completas de menú.
    
    Utilizado en endpoints que devuelven la estructura jerárquica completa
    del menú para un usuario o para administración.
    """
    
    menu: List[MenuItem] = Field(
        ...,
        description="Lista de menús raíz con su estructura jerárquica completa"
    )

    class Config:
        """Configuración para respuestas de menú."""
        from_attributes = True

class MenuReadSingle(MenuBase):
    """
    Schema para lectura de datos completos de un menú individual.
    
    Incluye todos los campos de MenuBase más metadatos del sistema
    y relaciones expandidas para operaciones CRUD.
    """
    
    menu_id: int = Field(
        ...,
        description="Identificador único del menú en el sistema",
        examples=[1, 2, 3]
    )
    
    area_nombre: Optional[str] = Field(
        None,
        description="Nombre del área a la que pertenece el menú",
        examples=["Administración", "Operaciones", "Reportes"]
    )
    
    fecha_creacion: datetime = Field(
        ...,
        description="Fecha y hora en que se creó el registro del menú"
    )
    
    fecha_actualizacion: Optional[datetime] = Field(
        None,
        description="Fecha y hora de la última actualización del menú"
    )

    class Config:
        """Configuración de Pydantic para el schema individual."""
        from_attributes = True
        str_strip_whitespace = True
        validate_assignment = True

# Actualizar referencias forward para la recursividad
MenuItem.model_rebuild()