# src/storage/migrations/seed_permissions.py

from src.storage.database import get_session
from src.storage.models import Permission
from src.utils.logger import get_logger
from src.utils.permissions import ROLE_PERMISSIONS, Role

logger = get_logger(__name__)


def seed_permissions():
    """
    Создает базовые разрешения для всех ролей в системе.
    """
    session = get_session()
    try:
        # Удаляем все существующие разрешения
        session.query(Permission).delete()
        session.commit()

        # Создаем разрешения на основе маппинга из централизованной системы
        permissions = []
        for role, role_perms in ROLE_PERMISSIONS.items():
            for permission in role_perms:
                permissions.append(
                    Permission(role=role.value, permission=permission.value)
                )

        # Добавляем все разрешения
        session.bulk_save_objects(permissions)
        session.commit()

        logger.info("✅ Базовые разрешения успешно созданы")

    except Exception as e:
        session.rollback()
        logger.error(f"❌ Ошибка при создании базовых разрешений: {str(e)}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    seed_permissions()
