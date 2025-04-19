"""
Перечисления для работы с данными в хранилище.
"""
from enum import Enum
from typing import List, Set


class UserRole(str, Enum):
    """
    Перечисление ролей пользователей в системе.
    
    Роли определяют права доступа к различным функциям бота:
    - ADMIN: Полный доступ ко всем функциям, управление пользователями и их ролями.
    - TARGETOLOGIST: Доступ к управлению кампаниями, но без финансовой информации.
    - PARTNER: Базовый уровень доступа, просмотр только разрешенной информации.
    """
    ADMIN = "admin"
    TARGETOLOGIST = "targetologist"
    PARTNER = "partner"
    
    @classmethod
    def values(cls) -> List[str]:
        """
        Возвращает список всех возможных значений ролей.
        
        Returns:
            Список строковых значений ролей.
        """
        return [role.value for role in cls]
    
    @classmethod
    def has_value(cls, value: str) -> bool:
        """
        Проверяет, существует ли роль с указанным значением.
        
        Args:
            value: Строковое значение роли для проверки.
            
        Returns:
            True, если роль существует, иначе False.
        """
        return value in cls.values()
    
    def has_permission(self, required_role: 'UserRole') -> bool:
        """
        Проверяет, имеет ли текущая роль разрешения роли required_role.
        
        Args:
            required_role: Требуемая роль для сравнения.
            
        Returns:
            True, если текущая роль имеет такие же или более высокие права, иначе False.
        """
        # Админ имеет доступ ко всему
        if self == UserRole.ADMIN:
            return True
        
        # Таргетолог имеет доступ к функциям таргетолога и партнера
        if self == UserRole.TARGETOLOGIST:
            return required_role in [UserRole.TARGETOLOGIST, UserRole.PARTNER]
        
        # Партнер имеет доступ только к функциям партнера
        if self == UserRole.PARTNER:
            return required_role == UserRole.PARTNER
        
        return False 