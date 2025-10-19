# app/schemas/usuario.py
"""
Esquemas Pydantic para la gestión de usuarios en el sistema.

Este módulo define todos los esquemas de validación, creación, actualización 
y lectura de usuarios, incluyendo validaciones de negocio y seguridad.

Características principales:
- Validaciones robustas con mensajes de error en español
- Seguridad en el manejo de contraseñas
- Compatibilidad con la estructura de base de datos existente
- Documentación clara para desarrolladores
"""

from pydantic import BaseModel, Field, EmailStr, field_validator, model_validator
from typing import Optional, List
from datetime import datetime
import re

# Importar schema de roles para relaciones
from .rol import RolRead

class UsuarioBase(BaseModel):
    """
    Schema base para usuarios con validaciones fundamentales.
    
    Este schema define los campos básicos que todos los usuarios deben tener
    y establece las reglas de validación esenciales para la integridad de los datos.
    """
    
    nombre_usuario: str = Field(
        ...,
        min_length=3,
        max_length=50,
        description="Nombre único de usuario para identificación en el sistema",
        examples=["juan_perez", "maria.garcia"]
    )
    
    correo: str = Field(
        ...,
        description="Dirección de correo electrónico válida",
        examples=["usuario@empresa.com", "nombre.apellido@dominio.org"]
    )
    
    nombre: Optional[str] = Field(
        None,
        max_length=50,
        description="Nombre real del usuario (solo letras y espacios)",
        examples=["Juan", "María José"]
    )
    
    apellido: Optional[str] = Field(
        None, 
        max_length=50,
        description="Apellido del usuario (solo letras y espacios)",
        examples=["Pérez García", "López"]
    )
    
    es_activo: bool = Field(
        True,
        description="Indica si el usuario está activo en el sistema"
    )

    @field_validator('nombre_usuario')
    @classmethod
    def validar_formato_nombre_usuario(cls, valor: str) -> str:
        """
        Valida que el nombre de usuario tenga un formato válido.
        
        Reglas:
        - Solo permite letras, números y guiones bajos
        - No permite espacios ni caracteres especiales
        - Convierte a minúsculas para consistencia
        
        Args:
            valor: El nombre de usuario a validar
            
        Returns:
            str: Nombre de usuario validado y normalizado
            
        Raises:
            ValueError: Cuando el formato no es válido
        """
        if not valor:
            raise ValueError('El nombre de usuario no puede estar vacío')
        
        # Eliminar espacios en blanco al inicio y final
        valor = valor.strip()
        
        if not valor:
            raise ValueError('El nombre de usuario no puede contener solo espacios')
        
        # Validar caracteres permitidos: letras, números y guiones bajos
        if not re.match(r'^[a-zA-Z0-9_]+$', valor):
            raise ValueError(
                'El nombre de usuario solo puede contener letras, números y guiones bajos (_). '
                'No se permiten espacios ni caracteres especiales.'
            )
        
        # Validar que no sea solo números
        if valor.isdigit():
            raise ValueError(
                'El nombre de usuario no puede contener solo números. '
                'Debe incluir al menos una letra.'
            )
        
        # Convertir a minúsculas para consistencia
        return valor.lower()

    @field_validator('correo')
    @classmethod
    def validar_formato_correo(cls, valor: str) -> str:
        """
        Valida el formato del correo electrónico con regex específico.
        
        Esta validación es más estricta que la simple validación de EmailStr
        para garantizar direcciones de correo profesionales válidas.
        
        Args:
            valor: La dirección de correo a validar
            
        Returns:
            str: Correo electrónico validado y normalizado
            
        Raises:
            ValueError: Cuando el formato del correo no es válido
        """
        if not valor:
            raise ValueError('La dirección de correo electrónico no puede estar vacía')
        
        valor = valor.strip().lower()
        
        # Patrón regex para validación estricta de email
        patron_email = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        
        if not re.match(patron_email, valor):
            raise ValueError(
                'La dirección de correo electrónico no tiene un formato válido. '
                'Ejemplo de formato correcto: usuario@dominio.com'
            )
        
        # Validación adicional: dominio no puede empezar o terminar con guión
        dominio = valor.split('@')[1]
        if dominio.startswith('-') or dominio.endswith('-'):
            raise ValueError('El dominio del correo electrónico no puede empezar ni terminar con guión')
        
        return valor

    @field_validator('nombre', 'apellido')
    @classmethod
    def validar_nombre_apellido(cls, valor: Optional[str]) -> Optional[str]:
        """
        Valida que nombres y apellidos contengan solo caracteres alfabéticos válidos.
        
        Permite:
        - Letras del alfabeto español (incluyendo ñ y acentos)
        - Espacios para nombres compuestos
        - Guiones para nombres compuestos
        
        Args:
            valor: El nombre o apellido a validar
            
        Returns:
            Optional[str]: Nombre o apellido validado y formateado
            
        Raises:
            ValueError: Cuando contiene caracteres no permitidos
        """
        if valor is None or valor == "":
            return None
        
        valor = valor.strip()
        
        if not valor:
            return None
        
        # Patrón que permite letras, espacios, guiones y caracteres españoles
        if not re.match(r'^[a-zA-ZáéíóúÁÉÍÓÚñÑ\s\-]+$', valor):
            raise ValueError(
                'El nombre y apellido solo pueden contener letras, espacios y guiones. '
                'No se permiten números ni caracteres especiales.'
            )
        
        # Validar que no sea solo espacios o guiones
        if valor.replace(' ', '').replace('-', '') == '':
            raise ValueError('El nombre no puede contener solo espacios o guiones')
        
        # Formatear con capitalización adecuada
        return valor.title()

    @model_validator(mode='after')
    def validar_longitud_minima_nombre_usuario(self) -> 'UsuarioBase':
        """
        Valida la longitud mínima del nombre de usuario después de la normalización.
        
        Esta validación se ejecuta después de que todos los campos han sido procesados
        para asegurar que las normalizaciones no hayan afectado la longitud.
        """
        if hasattr(self, 'nombre_usuario') and len(self.nombre_usuario) < 3:
            raise ValueError('El nombre de usuario debe tener al menos 3 caracteres')
        
        return self

class UsuarioCreate(UsuarioBase):
    """
    Schema para la creación de nuevos usuarios.
    
    Extiende UsuarioBase agregando validaciones específicas para la creación,
    incluyendo políticas de seguridad para contraseñas.
    """
    
    contrasena: str = Field(
        ...,
        min_length=8,
        max_length=100,
        description="Contraseña segura con mínimo 8 caracteres, una mayúscula, una minúscula y un número",
        examples=["MiContraseñaSegura123", "OtraPassword123!"]
    )

    @field_validator('contrasena')
    @classmethod
    def validar_fortaleza_contrasena(cls, valor: str) -> str:
        """
        Valida que la contraseña cumpla con las políticas de seguridad.
        
        Requisitos mínimos:
        - Mínimo 8 caracteres
        - Al menos una letra mayúscula
        - Al menos una letra minúscula  
        - Al menos un número
        - Se recomiendan caracteres especiales
        
        Args:
            valor: La contraseña a validar
            
        Returns:
            str: Contraseña validada
            
        Raises:
            ValueError: Cuando la contraseña no cumple los requisitos de seguridad
        """
        if len(valor) < 8:
            raise ValueError('La contraseña debe tener al menos 8 caracteres')
        
        # Verificar complejidad
        errores = []
        
        if not any(c.isupper() for c in valor):
            errores.append('al menos una letra mayúscula')
            
        if not any(c.islower() for c in valor):
            errores.append('al menos una letra minúscula')
            
        if not any(c.isdigit() for c in valor):
            errores.append('al menos un número')
        
        if errores:
            raise ValueError(
                f'La contraseña no cumple con los requisitos de seguridad. '
                f'Debe contener: {", ".join(errores)}.'
            )
        
        # Advertencia sobre caracteres especiales (pero no requeridos)
        if not any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?/' for c in valor):
            # Solo log warning, no error
            pass
        
        return valor

    @model_validator(mode='after')
    def validar_unicidad_datos(self) -> 'UsuarioCreate':
        """
        Valida lógicas de negocio que requieren múltiples campos.
        
        En un escenario real, aquí se podrían incluir validaciones que
        requieran verificar múltiples campos simultáneamente.
        """
        # Ejemplo: Validar que nombre de usuario no sea igual al correo
        if (hasattr(self, 'nombre_usuario') and hasattr(self, 'correo') and
            self.nombre_usuario == self.correo.split('@')[0]):
            # Esto no es un error, pero podría ser una advertencia
            pass
            
        return self

class UsuarioUpdate(BaseModel):
    """
    Schema para actualización parcial de usuarios.
    
    Todos los campos son opcionales y solo se validan los que se proporcionen.
    Diseñado específicamente para operaciones PATCH.
    """
    
    nombre_usuario: Optional[str] = Field(
        None,
        min_length=3,
        max_length=50,
        description="Nuevo nombre de usuario (opcional)"
    )
    
    correo: Optional[str] = Field(
        None,
        description="Nueva dirección de correo electrónico (opcional)"
    )
    
    nombre: Optional[str] = Field(
        None,
        max_length=50,
        description="Nuevo nombre (opcional)"
    )
    
    apellido: Optional[str] = Field(
        None,
        max_length=50, 
        description="Nuevo apellido (opcional)"
    )
    
    es_activo: Optional[bool] = Field(
        None,
        description="Nuevo estado activo/inactivo (opcional)"
    )

    # Reutilizar validadores específicos para campos opcionales
    _validar_nombre_usuario = field_validator('nombre_usuario')(UsuarioBase.validar_formato_nombre_usuario.__func__)
    _validar_correo = field_validator('correo')(UsuarioBase.validar_formato_correo.__func__)
    _validar_nombre_apellido = field_validator('nombre', 'apellido')(UsuarioBase.validar_nombre_apellido.__func__)

class UsuarioRead(UsuarioBase):
    """
    Schema para lectura de datos básicos de usuario.
    
    Incluye todos los campos de UsuarioBase más metadatos del sistema
    que se generan automáticamente.
    """
    
    usuario_id: int = Field(
        ...,
        description="Identificador único del usuario en el sistema"
    )
    
    fecha_creacion: datetime = Field(
        ...,
        description="Fecha y hora en que se creó el registro del usuario"
    )
    
    fecha_ultimo_acceso: Optional[datetime] = Field(
        None,
        description="Fecha y hora del último acceso del usuario al sistema"
    )
    
    correo_confirmado: bool = Field(
        ...,
        description="Indica si el usuario ha confirmado su dirección de correo electrónico"
    )

    class Config:
        """Configuración de Pydantic para el schema."""
        from_attributes = True
        str_strip_whitespace = True
        validate_assignment = True

class UsuarioReadWithRoles(UsuarioRead):
    """
    Schema extendido para lectura de usuario que incluye sus roles.
    
    Utilizado en endpoints que requieren información completa del usuario
    incluyendo los permisos y roles asignados.
    """
    
    roles: List[RolRead] = Field(
        default_factory=list,
        description="Lista de roles activos asignados al usuario"
    )

    class Config:
        """Configuración de Pydantic para el schema extendido."""
        from_attributes = True
        str_strip_whitespace = True
        validate_assignment = True

class PaginatedUsuarioResponse(BaseModel):
    """
    Schema para respuestas paginadas de listas de usuarios.
    
    Utilizado en endpoints que devuelven listas paginadas de usuarios
    con metadatos de paginación.
    """
    
    usuarios: List[UsuarioReadWithRoles] = Field(
        ...,
        description="Lista de usuarios para la página actual"
    )
    
    total_usuarios: int = Field(
        ...,
        ge=0,
        description="Número total de usuarios que coinciden con los filtros"
    )
    
    pagina_actual: int = Field(
        ...,
        ge=1,
        description="Número de la página actual siendo visualizada"
    )
    
    total_paginas: int = Field(
        ...,
        ge=0,
        description="Número total de páginas disponibles"
    )

    class Config:
        """Configuración para respuestas paginadas."""
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }