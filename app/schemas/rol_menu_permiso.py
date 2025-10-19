# app/schemas/rol_menu_permiso.py
"""
Esquemas Pydantic para la gestión de permisos de roles sobre menús en el sistema.

Este módulo define todos los esquemas de validación, creación, actualización 
y lectura de los permisos específicos que los roles tienen sobre los menús.

Los permisos rol-menú permiten controlar granularmente qué acciones puede realizar
cada rol sobre cada menú del sistema, proporcionando un control de acceso detallado.

Características principales:
- Validaciones robustas con mensajes de error en español
- Gestión completa de permisos rol-menú
- Validación de existencia de roles y menús
- Control granular de permisos (ver, editar, eliminar)
- Documentación clara para desarrolladores
"""

from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, Dict, Any

class RolMenuPermisoBase(BaseModel):
    """
    Schema base para permisos rol-menú con validaciones fundamentales.
    
    Define la estructura básica de un permiso rol-menú y establece 
    las reglas de validación esenciales para mantener la seguridad del sistema.
    """
    
    rol_id: int = Field(
        ...,
        ge=1,
        description="ID del rol al que se asignan los permisos",
        examples=[1, 2, 3]
    )
    
    menu_id: int = Field(
        ...,
        ge=1,
        description="ID del menú sobre el que se aplican los permisos",
        examples=[1, 2, 3]
    )
    
    puede_ver: bool = Field(
        True,
        description="Permiso para visualizar/acceder al menú",
        examples=[True, False]
    )
    
    puede_editar: bool = Field(
        False,
        description="Permiso para editar contenido asociado al menú",
        examples=[True, False]
    )
    
    puede_eliminar: bool = Field(
        False,
        description="Permiso para eliminar contenido asociado al menú",
        examples=[True, False]
    )

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
            raise ValueError('El ID del menú debe ser un número positivo mayor a 0')
        
        return valor

    @model_validator(mode='after')
    def validar_consistencia_permisos(self) -> 'RolMenuPermisoBase':
        """
        Valida consistencias adicionales después de procesar todos los campos.
        
        Realiza validaciones que requieren múltiples campos o que dependen
        de transformaciones realizadas en validadores individuales.
        """
        # Validar que si puede_editar o puede_eliminar es True, entonces puede_ver debe ser True
        if (self.puede_editar or self.puede_eliminar) and not self.puede_ver:
            raise ValueError(
                'No se pueden conceder permisos de edición o eliminación sin permiso de visualización. '
                'El permiso "puede_ver" debe ser True cuando "puede_editar" o "puede_eliminar" son True.'
            )
        
        # Validar lógica de permisos: no debería poder eliminar sin poder editar
        if self.puede_eliminar and not self.puede_editar:
            raise ValueError(
                'No se puede conceder permiso de eliminación sin permiso de edición. '
                'El permiso "puede_editar" debe ser True cuando "puede_eliminar" es True.'
            )
        
        return self

class RolMenuPermisoCreate(RolMenuPermisoBase):
    """
    Schema para la creación de nuevos permisos rol-menú.
    
    Extiende RolMenuPermisoBase sin agregar campos adicionales, pero se utiliza
    para documentar específicamente la operación de creación.
    """
    pass

class RolMenuPermisoUpdate(BaseModel):
    """
    Schema para actualización parcial de permisos rol-menú.
    
    Todos los campos son opcionales y solo se validan los que se proporcionen.
    Diseñado específicamente para operaciones PATCH que actualizan solo
    algunos permisos específicos.
    """
    
    puede_ver: Optional[bool] = Field(
        None,
        description="Nuevo permiso de visualización (opcional)",
        examples=[True, False]
    )
    
    puede_editar: Optional[bool] = Field(
        None,
        description="Nuevo permiso de edición (opcional)",
        examples=[True, False]
    )
    
    puede_eliminar: Optional[bool] = Field(
        None,
        description="Nuevo permiso de eliminación (opcional)",
        examples=[True, False]
    )

    @model_validator(mode='after')
    def validar_consistencia_permisos_parciales(self) -> 'RolMenuPermisoUpdate':
        """
        Valida consistencias en actualizaciones parciales de permisos.
        
        Aplica las mismas reglas de negocio que el validador base, pero
        considerando que algunos campos pueden ser None (no actualizados).
        """
        # Solo validar si todos los campos relevantes están presentes
        puede_ver = self.puede_ver
        puede_editar = self.puede_editar
        puede_eliminar = self.puede_eliminar
        
        # Si se está actualizando editar o eliminar, verificar que ver sea True
        if (puede_editar is not None and puede_editar) or (puede_eliminar is not None and puede_eliminar):
            if puede_ver is not None and not puede_ver:
                raise ValueError(
                    'No se pueden conceder permisos de edición o eliminación sin permiso de visualización. '
                    'El permiso "puede_ver" debe ser True cuando "puede_editar" o "puede_eliminar" son True.'
                )
        
        # Si se está actualizando eliminar, verificar que editar sea True
        if puede_eliminar is not None and puede_eliminar:
            if puede_editar is not None and not puede_editar:
                raise ValueError(
                    'No se puede conceder permiso de eliminación sin permiso de edición. '
                    'El permiso "puede_editar" debe ser True cuando "puede_eliminar" es True.'
                )
        
        return self

class RolMenuPermisoRead(RolMenuPermisoBase):
    """
    Schema para lectura de datos completos de un permiso rol-menú.
    
    Incluye todos los campos de RolMenuPermisoBase más el identificador
    único del registro de permiso en el sistema.
    """
    
    rol_menu_id: int = Field(
        ...,
        description="Identificador único del permiso rol-menú en el sistema",
        examples=[1, 2, 3]
    )

    class Config:
        """Configuración de Pydantic para el schema."""
        from_attributes = True
        str_strip_whitespace = True
        validate_assignment = True

class RolMenuPermisoReadWithDetails(RolMenuPermisoRead):
    """
    Schema extendido para lectura de permisos rol-menú con detalles adicionales.
    
    Incluye información descriptiva del rol y menú para facilitar
    la comprensión en interfaces de administración.
    """
    
    rol_nombre: Optional[str] = Field(
        None,
        description="Nombre del rol asociado",
        examples=["Administrador", "Usuario", "Supervisor"]
    )
    
    rol_descripcion: Optional[str] = Field(
        None,
        description="Descripción del rol asociado",
        examples=["Acceso completo al sistema", "Usuario con permisos básicos"]
    )
    
    menu_nombre: Optional[str] = Field(
        None,
        description="Nombre del menú asociado",
        examples=["Dashboard", "Usuarios", "Configuración"]
    )
    
    menu_ruta: Optional[str] = Field(
        None,
        description="Ruta del menú asociado",
        examples=["/dashboard", "/usuarios", "/configuracion"]
    )
    
    menu_icono: Optional[str] = Field(
        None,
        description="Icono del menú asociado",
        examples=["dashboard", "users", "settings"]
    )

    class Config:
        """Configuración para respuestas extendidas."""
        from_attributes = True

class RolMenuPermisoBulkUpdate(BaseModel):
    """
    Schema para actualización masiva de permisos rol-menú.
    
    Utilizado en operaciones que actualizan múltiples permisos
    simultáneamente para un rol específico.
    """
    
    permisos: dict[int, Dict[str, bool]] = Field(
        ...,
        description="Diccionario donde las claves son menu_id y los valores son diccionarios de permisos",
        examples=[{
            1: {"puede_ver": True, "puede_editar": False, "puede_eliminar": False},
            2: {"puede_ver": True, "puede_editar": True, "puede_eliminar": False},
            3: {"puede_ver": False, "puede_editar": False, "puede_eliminar": False}
        }]
    )

    @field_validator('permisos')
    @classmethod
    def validar_permisos_masivos(cls, valor: dict[int, Dict[str, bool]]) -> dict[int, Dict[str, bool]]:
        """
        Valida la estructura y consistencia de los permisos masivos.
        
        Args:
            valor: Diccionario de permisos a validar
            
        Returns:
            dict: Diccionario de permisos validado
            
        Raises:
            ValueError: Cuando la estructura o valores no son válidos
        """
        if not valor:
            raise ValueError('El diccionario de permisos no puede estar vacío')
        
        for menu_id, permisos in valor.items():
            # Validar menu_id positivo
            if menu_id < 1:
                raise ValueError(f'El ID del menú {menu_id} debe ser un número positivo')
            
            # Validar estructura de permisos
            permisos_requeridos = {'puede_ver', 'puede_editar', 'puede_eliminar'}
            if not all(permiso in permisos for permiso in permisos_requeridos):
                raise ValueError(f'Faltan permisos requeridos para el menú {menu_id}')
            
            # Validar tipos de permisos
            for permiso_nombre, permiso_valor in permisos.items():
                if not isinstance(permiso_valor, bool):
                    raise ValueError(f'El permiso {permiso_nombre} para el menú {menu_id} debe ser booleano')
            
            # Validar lógica de permisos
            puede_ver = permisos.get('puede_ver', False)
            puede_editar = permisos.get('puede_editar', False)
            puede_eliminar = permisos.get('puede_eliminar', False)
            
            if (puede_editar or puede_eliminar) and not puede_ver:
                raise ValueError(
                    f'No se pueden conceder permisos de edición o eliminación sin permiso de '
                    f'visualización para el menú {menu_id}'
                )
            
            if puede_eliminar and not puede_editar:
                raise ValueError(
                    f'No se puede conceder permiso de eliminación sin permiso de edición '
                    f'para el menú {menu_id}'
                )
        
        return valor

    class Config:
        """Configuración para actualizaciones masivas."""
        from_attributes = True

class RolMenuPermisoSummary(BaseModel):
    """
    Schema para resumen de permisos de un rol.
    
    Utilizado en respuestas que requieren un resumen rápido de los permisos
    de un rol específico sin todos los detalles.
    """
    
    rol_id: int = Field(
        ...,
        description="ID del rol",
        examples=[1, 2, 3]
    )
    
    rol_nombre: str = Field(
        ...,
        description="Nombre del rol",
        examples=["Administrador", "Usuario", "Supervisor"]
    )
    
    total_permisos: int = Field(
        ...,
        description="Número total de permisos asignados al rol",
        examples=[5, 10, 15]
    )
    
    permisos_activos: int = Field(
        ...,
        description="Número de permisos con al menos puede_ver=True",
        examples=[3, 8, 12]
    )
    
    puede_editar_count: int = Field(
        ...,
        description="Número de permisos con puede_editar=True",
        examples=[2, 5, 8]
    )
    
    puede_eliminar_count: int = Field(
        ...,
        description="Número de permisos con puede_eliminar=True",
        examples=[1, 3, 5]
    )

    class Config:
        """Configuración para resúmenes."""
        from_attributes = True