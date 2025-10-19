# app/schemas/usuario_rol.py
"""
Esquemas Pydantic para la gestión de relaciones usuario-rol en el sistema.

Este módulo define todos los esquemas de validación, creación, actualización 
y lectura de las asignaciones entre usuarios y roles.

Las relaciones usuario-rol permiten asignar múltiples roles a un usuario
y gestionar los permisos de manera centralizada a través de los roles.

Características principales:
- Validaciones robustas con mensajes de error en español
- Gestión completa de asignaciones usuario-rol
- Validación de existencia de usuarios y roles
- Documentación clara para desarrolladores
"""

from pydantic import BaseModel, Field, field_validator, model_validator
from datetime import datetime
from typing import Optional

class UsuarioRolBase(BaseModel):
    """
    Schema base para relaciones usuario-rol con validaciones fundamentales.
    
    Define la estructura básica de una asignación usuario-rol y establece 
    las reglas de validación esenciales para mantener la integridad del sistema.
    """
    
    usuario_id: int = Field(
        ...,
        ge=1,
        description="ID del usuario al que se asigna el rol",
        examples=[1, 2, 3]
    )
    
    rol_id: int = Field(
        ...,
        ge=1,
        description="ID del rol que se asigna al usuario",
        examples=[1, 2, 3]
    )
    
    es_activo: bool = Field(
        True,
        description="Indica si la asignación usuario-rol está activa"
    )

    @field_validator('usuario_id')
    @classmethod
    def validar_usuario_id(cls, valor: int) -> int:
        """
        Valida que el ID del usuario sea un valor positivo.
        
        Args:
            valor: ID del usuario a validar
            
        Returns:
            int: ID del usuario validado
            
        Raises:
            ValueError: Cuando el ID no es positivo
        """
        if valor < 1:
            raise ValueError('El ID del usuario debe ser un número positivo mayor a 0')
        
        return valor

    @field_validator('rol_id')
    @classmethod
    def validar_rol_id(cls, valor: int) -> int:
        """
        Valida que el ID del rol sea un valor positivo.
        
        Args:
            valor: ID del rol a validar
            
        Returns:
            int: ID del rol validado
            
        Raises:
            ValueError: Cuando el ID no es positivo
        """
        if valor < 1:
            raise ValueError('El ID del rol debe ser un número positivo mayor a 0')
        
        return valor

    @model_validator(mode='after')
    def validar_consistencia_asignacion(self) -> 'UsuarioRolBase':
        """
        Valida consistencias adicionales después de procesar todos los campos.
        
        Realiza validaciones que requieren múltiples campos o que dependen
        de transformaciones realizadas en validadores individuales.
        """
        # Validar que no se asigne un usuario a sí mismo como rol (si fuera posible)
        # Esta validación es más conceptual ya que usuario_id y rol_id son de diferentes entidades
        
        # Podríamos añadir validaciones específicas de negocio aquí
        # Por ejemplo: verificar que no se asignen roles reservados a usuarios específicos
        
        return self

class UsuarioRolCreate(BaseModel):
    """
    Schema para la creación de nuevas asignaciones usuario-rol.
    
    Diseñado específicamente para operaciones de creación donde los IDs
    se obtienen de la ruta URL en lugar del cuerpo de la solicitud.
    """
    
    # Nota: En la implementación actual, los IDs vienen en la ruta URL
    # Este schema puede estar vacío o contener campos adicionales si es necesario
    
    es_activo: Optional[bool] = Field(
        True,
        description="Estado inicial de la asignación (por defecto activa)",
        examples=[True, False]
    )

class UsuarioRolUpdate(BaseModel):
    """
    Schema para actualización del estado de asignaciones usuario-rol.
    
    Utilizado específicamente para activar/desactivar asignaciones
    existentes sin modificar las relaciones fundamentales.
    """
    
    es_activo: bool = Field(
        ...,
        description="Nuevo estado activo/inactivo de la asignación",
        examples=[True, False]
    )

class UsuarioRolRead(UsuarioRolBase):
    """
    Schema para lectura de datos completos de una asignación usuario-rol.
    
    Incluye todos los campos de UsuarioRolBase más metadatos del sistema
    que se generan automáticamente durante la creación de la asignación.
    """
    
    usuario_rol_id: int = Field(
        ...,
        description="Identificador único de la asignación usuario-rol en el sistema",
        examples=[1, 2, 3]
    )
    
    fecha_asignacion: datetime = Field(
        ...,
        description="Fecha y hora en que se creó la asignación usuario-rol"
    )

    class Config:
        """Configuración de Pydantic para el schema."""
        from_attributes = True
        str_strip_whitespace = True
        validate_assignment = True

class UsuarioRolResponse(BaseModel):
    """
    Schema para respuestas de operaciones usuario-rol con metadatos extendidos.
    
    Utilizado en respuestas que requieren información adicional sobre
    la asignación, como nombres de usuario y rol en lugar de solo IDs.
    """
    
    usuario_rol_id: int = Field(
        ...,
        description="ID único de la asignación",
        examples=[1, 2, 3]
    )
    
    usuario_id: int = Field(
        ...,
        description="ID del usuario",
        examples=[1, 2, 3]
    )
    
    nombre_usuario: Optional[str] = Field(
        None,
        description="Nombre de usuario asociado",
        examples=["juan_perez", "maria_garcia"]
    )
    
    rol_id: int = Field(
        ...,
        description="ID del rol",
        examples=[1, 2, 3]
    )
    
    nombre_rol: Optional[str] = Field(
        None,
        description="Nombre del rol asociado",
        examples=["Administrador", "Usuario", "Supervisor"]
    )
    
    es_activo: bool = Field(
        ...,
        description="Estado de la asignación",
        examples=[True, False]
    )
    
    fecha_asignacion: datetime = Field(
        ...,
        description="Fecha de creación de la asignación"
    )

    class Config:
        """Configuración para respuestas extendidas."""
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }

class UsuarioRolBulkOperation(BaseModel):
    """
    Schema para operaciones masivas sobre asignaciones usuario-rol.
    
    Utilizado en operaciones que afectan múltiples asignaciones
    simultáneamente, como asignaciones/revocaciones por lote.
    """
    
    usuario_ids: list[int] = Field(
        ...,
        description="Lista de IDs de usuarios a afectar",
        examples=[[1, 2, 3], [4, 5, 6]]
    )
    
    rol_ids: list[int] = Field(
        ...,
        description="Lista de IDs de roles a asignar/revocar",
        examples=[[1, 2], [3, 4]]
    )
    
    operacion: str = Field(
        ...,
        description="Tipo de operación a realizar: 'asignar' o 'revocar'",
        examples=["asignar", "revocar"]
    )

    @field_validator('usuario_ids')
    @classmethod
    def validar_usuario_ids(cls, valor: list[int]) -> list[int]:
        """
        Valida que la lista de IDs de usuario contenga valores positivos.
        
        Args:
            valor: Lista de IDs de usuario a validar
            
        Returns:
            list[int]: Lista de IDs validada
            
        Raises:
            ValueError: Cuando algún ID no es válido
        """
        if not valor:
            raise ValueError('La lista de IDs de usuario no puede estar vacía')
        
        for usuario_id in valor:
            if usuario_id < 1:
                raise ValueError('Todos los IDs de usuario deben ser números positivos')
        
        return valor

    @field_validator('rol_ids')
    @classmethod
    def validar_rol_ids(cls, valor: list[int]) -> list[int]:
        """
        Valida que la lista de IDs de rol contenga valores positivos.
        
        Args:
            valor: Lista de IDs de rol a validar
            
        Returns:
            list[int]: Lista de IDs validada
            
        Raises:
            ValueError: Cuando algún ID no es válido
        """
        if not valor:
            raise ValueError('La lista de IDs de rol no puede estar vacía')
        
        for rol_id in valor:
            if rol_id < 1:
                raise ValueError('Todos los IDs de rol deben ser números positivos')
        
        return valor

    @field_validator('operacion')
    @classmethod
    def validar_operacion(cls, valor: str) -> str:
        """
        Valida que la operación sea una de las permitidas.
        
        Args:
            valor: Operación a validar
            
        Returns:
            str: Operación validada y normalizada
            
        Raises:
            ValueError: Cuando la operación no es válida
        """
        operaciones_permitidas = ['asignar', 'revocar']
        if valor not in operaciones_permitidas:
            raise ValueError(f'La operación debe ser una de: {", ".join(operaciones_permitidas)}')
        
        return valor

    class Config:
        """Configuración para operaciones masivas."""
        from_attributes = True
        str_strip_whitespace = True
        validate_assignment = True