"""
Централизованная система управления разрешениями.
"""
from enum import Enum
from typing import Dict, List, Set

class Role(str, Enum):
    """Все доступные роли в системе."""
    OWNER = "owner"
    ADMIN = "admin"
    TARGETOLOGIST = "targetologist"
    PARTNER = "partner"

class Permission(str, Enum):
    """Все доступные разрешения в системе."""
    MANAGE_USERS = "manage_users"
    MANAGE_ACCOUNTS = "manage_accounts"
    VIEW_STATISTICS = "view_statistics"
    EXPORT_DATA = "export_data"
    MANAGE_NOTIFICATIONS = "manage_notifications"
    VIEW_ADMIN_PANEL = "view_admin_panel"

# Маппинг ролей к разрешениям
ROLE_PERMISSIONS: Dict[Role, Set[Permission]] = {
    Role.OWNER: {
        Permission.MANAGE_USERS,
        Permission.MANAGE_ACCOUNTS,
        Permission.VIEW_STATISTICS,
        Permission.EXPORT_DATA,
        Permission.MANAGE_NOTIFICATIONS,
        Permission.VIEW_ADMIN_PANEL
    },
    Role.ADMIN: {
        Permission.MANAGE_USERS,
        Permission.VIEW_STATISTICS,
        Permission.EXPORT_DATA,
        Permission.VIEW_ADMIN_PANEL,
        Permission.MANAGE_NOTIFICATIONS
    },
    Role.TARGETOLOGIST: {
        Permission.VIEW_STATISTICS,
        Permission.EXPORT_DATA,
        Permission.MANAGE_NOTIFICATIONS
    },
    Role.PARTNER: {
        Permission.VIEW_STATISTICS,
        Permission.MANAGE_NOTIFICATIONS
    }
}

def get_role_permissions(role: str) -> Set[str]:
    """
    Получить все разрешения для указанной роли.
    
    Args:
        role: Название роли
        
    Returns:
        Множество разрешений для роли
    """
    try:
        role_enum = Role(role)
        return {perm.value for perm in ROLE_PERMISSIONS.get(role_enum, set())}
    except ValueError:
        return set()

def is_valid_role(role: str) -> bool:
    """
    Проверить, является ли роль допустимой.
    
    Args:
        role: Название роли
        
    Returns:
        True если роль допустима, False иначе
    """
    return role in [r.value for r in Role]

def get_available_roles(exclude_owner: bool = True) -> List[str]:
    """
    Получить список доступных ролей.
    
    Args:
        exclude_owner: Исключить роль owner из списка
        
    Returns:
        Список доступных ролей
    """
    roles = [r.value for r in Role]
    if exclude_owner:
        roles.remove(Role.OWNER.value)
    return roles

def has_permission(role: str, permission: str) -> bool:
    """
    Проверить, имеет ли роль указанное разрешение.
    
    Args:
        role: Название роли
        permission: Название разрешения
        
    Returns:
        True если роль имеет разрешение, False иначе
    """
    try:
        role_enum = Role(role)
        perm_enum = Permission(permission)
        return perm_enum in ROLE_PERMISSIONS.get(role_enum, set())
    except ValueError:
        return False

def get_all_permissions() -> List[str]:
    """
    Получить список всех возможных разрешений.
    
    Returns:
        Список всех разрешений
    """
    return [p.value for p in Permission] 