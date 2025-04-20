"""
Сервис для управления доступом и запросами на доступ.

Этот сервис объединяет логику из контроллера и репозитория доступа,
обеспечивая единый интерфейс для работы с доступом пользователей и запросами.
"""
from typing import List, Optional, Tuple, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import or_, desc, and_

from src.db.models.access_request import AccessRequest, AccessRequestStatus
from src.db.models.user import User, UserRole
from src.storage.models import AccessControl
from src.db.session import session_scope
from src.utils.logger import get_logger

logger = get_logger(__name__)


class AccessService:
    """
    Сервис для управления доступом пользователей и запросами на доступ.
    
    Объединяет функциональность AccessController и AccessControlRepository
    для централизованного управления доступом.
    """
    
    # --------- Методы для работы с запросами доступа ---------
    
    @staticmethod
    async def create_access_request(
        telegram_id: int,
        username: Optional[str],
        first_name: str,
        last_name: Optional[str],
        email: str,
        reason: str
    ) -> Tuple[bool, Optional[int], Optional[str]]:
        """
        Создать новый запрос на доступ.
        
        Args:
            telegram_id: Telegram ID пользователя
            username: Имя пользователя в Telegram
            first_name: Имя пользователя
            last_name: Фамилия пользователя
            email: Email пользователя
            reason: Причина запроса доступа
            
        Returns:
            Tuple[bool, Optional[int], Optional[str]]: (успех, id запроса, сообщение об ошибке)
        """
        try:
            with session_scope() as session:
                # Проверяем, есть ли уже активный запрос от этого пользователя
                existing_request = session.query(AccessRequest).filter(
                    AccessRequest.telegram_id == telegram_id,
                    AccessRequest.status == AccessRequestStatus.PENDING
                ).first()
                
                if existing_request:
                    return False, None, "У вас уже есть активный запрос на доступ."
                
                # Проверяем, имеет ли пользователь уже доступ
                existing_user = session.query(User).filter(User.telegram_id == telegram_id).first()
                if existing_user and existing_user.is_active:
                    return False, None, "У вас уже есть доступ к боту."
                
                # Создаем новый запрос на доступ
                new_request = AccessRequest(
                    telegram_id=telegram_id,
                    username=username,
                    first_name=first_name,
                    last_name=last_name,
                    email=email,
                    reason=reason,
                    status=AccessRequestStatus.PENDING
                )
                
                session.add(new_request)
                session.flush()
                request_id = new_request.id
                
                return True, request_id, None
                
        except SQLAlchemyError as e:
            logger.error(f"Ошибка создания запроса на доступ: {e}")
            return False, None, f"Произошла ошибка при создании запроса на доступ: {str(e)}"
    
    @staticmethod
    async def get_access_request(request_id: int) -> Optional[Dict[str, Any]]:
        """
        Получить запрос на доступ по ID.
        
        Args:
            request_id: ID запроса
            
        Returns:
            Optional[Dict[str, Any]]: Данные запроса или None
        """
        try:
            with session_scope() as session:
                request = session.query(AccessRequest).filter(AccessRequest.id == request_id).first()
                
                if not request:
                    return None
                
                return {
                    "id": request.id,
                    "telegram_id": request.telegram_id,
                    "username": request.username,
                    "first_name": request.first_name,
                    "last_name": request.last_name,
                    "email": request.email,
                    "reason": request.reason,
                    "status": request.status.value,
                    "created_at": request.created_at,
                    "updated_at": request.updated_at,
                    "admin_id": request.admin_id,
                    "admin_notes": request.admin_notes
                }
                
        except SQLAlchemyError as e:
            logger.error(f"Ошибка получения запроса на доступ: {e}")
            return None
    
    @staticmethod
    async def get_pending_requests(limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Получить список ожидающих запросов на доступ.
        
        Args:
            limit: Лимит запросов
            offset: Смещение для пагинации
            
        Returns:
            List[Dict[str, Any]]: Список запросов
        """
        try:
            with session_scope() as session:
                requests = session.query(AccessRequest).filter(
                    AccessRequest.status == AccessRequestStatus.PENDING
                ).order_by(AccessRequest.created_at).limit(limit).offset(offset).all()
                
                return [{
                    "id": request.id,
                    "telegram_id": request.telegram_id,
                    "username": request.username,
                    "first_name": request.first_name,
                    "last_name": request.last_name,
                    "email": request.email,
                    "reason": request.reason,
                    "status": request.status.value,
                    "created_at": request.created_at,
                    "updated_at": request.updated_at
                } for request in requests]
                
        except SQLAlchemyError as e:
            logger.error(f"Ошибка получения ожидающих запросов: {e}")
            return []
    
    @staticmethod
    async def approve_request(
        request_id: int, 
        admin_id: int, 
        admin_notes: Optional[str] = None
    ) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """
        Одобрить запрос на доступ.
        
        Args:
            request_id: ID запроса
            admin_id: ID администратора
            admin_notes: Заметки администратора
            
        Returns:
            Tuple[bool, Optional[Dict[str, Any]], Optional[str]]: 
                (успех, данные запроса, сообщение об ошибке)
        """
        try:
            with session_scope() as session:
                request = session.query(AccessRequest).filter(AccessRequest.id == request_id).first()
                
                if not request:
                    return False, None, "Запрос не найден."
                
                if request.status != AccessRequestStatus.PENDING:
                    return False, None, "Запрос уже обработан."
                
                # Обновляем запрос
                request.status = AccessRequestStatus.APPROVED
                request.admin_id = admin_id
                request.admin_notes = admin_notes
                request.updated_at = datetime.now()
                
                # Создаем или активируем пользователя
                user = session.query(User).filter(User.telegram_id == request.telegram_id).first()
                
                if not user:
                    # Создаем нового пользователя
                    user = User(
                        telegram_id=request.telegram_id,
                        username=request.username,
                        first_name=request.first_name,
                        last_name=request.last_name,
                        email=request.email,
                        role=UserRole.PARTNER.value,
                        is_active=True
                    )
                    session.add(user)
                else:
                    # Активируем существующего пользователя
                    user.is_active = True
                    user.email = request.email or user.email
                
                session.flush()
                
                # Предоставляем базовые права доступа
                access_control = AccessControl(
                    telegram_id=request.telegram_id,
                    resource_type="system",
                    resource_id="base_access",
                    is_active=True,
                    expires_at=datetime.now() + timedelta(days=365)  # 1 год доступа по умолчанию
                )
                session.add(access_control)
                
                # Создаем данные для возврата
                result_data = {
                    "request": {
                        "id": request.id,
                        "telegram_id": request.telegram_id,
                        "username": request.username,
                        "first_name": request.first_name,
                        "last_name": request.last_name,
                        "email": request.email,
                        "status": request.status.value,
                        "admin_id": request.admin_id,
                        "admin_notes": request.admin_notes
                    },
                    "user": {
                        "id": user.id,
                        "telegram_id": user.telegram_id,
                        "username": user.username,
                        "role": user.role
                    }
                }
                
                return True, result_data, None
                
        except SQLAlchemyError as e:
            logger.error(f"Ошибка одобрения запроса: {e}")
            return False, None, f"Произошла ошибка при одобрении запроса: {str(e)}"
    
    @staticmethod
    async def deny_request(
        request_id: int, 
        admin_id: int, 
        admin_notes: Optional[str] = None
    ) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """
        Отклонить запрос на доступ.
        
        Args:
            request_id: ID запроса
            admin_id: ID администратора
            admin_notes: Заметки администратора
            
        Returns:
            Tuple[bool, Optional[Dict[str, Any]], Optional[str]]: 
                (успех, данные запроса, сообщение об ошибке)
        """
        try:
            with session_scope() as session:
                request = session.query(AccessRequest).filter(AccessRequest.id == request_id).first()
                
                if not request:
                    return False, None, "Запрос не найден."
                
                if request.status != AccessRequestStatus.PENDING:
                    return False, None, "Запрос уже обработан."
                
                # Обновляем запрос
                request.status = AccessRequestStatus.DENIED
                request.admin_id = admin_id
                request.admin_notes = admin_notes
                request.updated_at = datetime.now()
                
                # Создаем данные для возврата
                result_data = {
                    "id": request.id,
                    "telegram_id": request.telegram_id,
                    "username": request.username,
                    "first_name": request.first_name,
                    "last_name": request.last_name,
                    "email": request.email,
                    "status": request.status.value,
                    "admin_id": request.admin_id,
                    "admin_notes": request.admin_notes
                }
                
                return True, result_data, None
                
        except SQLAlchemyError as e:
            logger.error(f"Ошибка отклонения запроса: {e}")
            return False, None, f"Произошла ошибка при отклонении запроса: {str(e)}"
    
    @staticmethod
    async def get_admin_ids() -> List[int]:
        """
        Получить список ID администраторов.
        
        Returns:
            List[int]: Список ID администраторов
        """
        try:
            with session_scope() as session:
                admins = session.query(User).filter(
                    User.role == UserRole.ADMIN.value,
                    User.is_active == True
                ).all()
                
                return [admin.telegram_id for admin in admins]
                
        except SQLAlchemyError as e:
            logger.error(f"Ошибка получения администраторов: {e}")
            return []
    
    # --------- Методы для управления доступом ---------
    
    @staticmethod
    def check_access(telegram_id: int, resource_type: str, resource_id: str, session=None) -> bool:
        """
        Проверяет наличие доступа пользователя к ресурсу.
        
        Args:
            telegram_id: Telegram ID пользователя
            resource_type: Тип ресурса
            resource_id: ID ресурса
            session: SQLAlchemy сессия (опционально)
            
        Returns:
            bool: True, если доступ есть, иначе False
        """
        close_session = False
        
        try:
            if session is None:
                session = session_scope().__enter__()
                close_session = True
            
            # Проверяем роль пользователя
            user = session.query(User).filter(User.telegram_id == telegram_id).first()
            if not user or not user.is_active:
                return False
            
            # Администраторы и таргетологи имеют доступ ко всем ресурсам
            if user.role in [UserRole.ADMIN.value, UserRole.TARGETOLOGIST.value]:
                return True
            
            # Для партнеров проверяем наличие специфического доступа
            access = session.query(AccessControl).filter(
                AccessControl.telegram_id == telegram_id,
                AccessControl.resource_type == resource_type,
                AccessControl.resource_id == resource_id,
                AccessControl.is_active == True
            ).first()
            
            if access and access.is_valid():
                return True
                
            # Проверяем доступ к глобальным ресурсам
            if resource_type == "campaign":
                global_access = session.query(AccessControl).filter(
                    AccessControl.telegram_id == telegram_id,
                    AccessControl.resource_type == "all_campaigns",
                    AccessControl.is_active == True
                ).first()
                
                if global_access and global_access.is_valid():
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Ошибка проверки доступа для пользователя {telegram_id}: {str(e)}")
            return False
        finally:
            if close_session and session:
                session.close()
    
    @staticmethod
    def grant_access(
        telegram_id: int, 
        resource_type: str, 
        resource_id: str, 
        expires_in_days: Optional[int] = 30,
        params: Optional[Dict[str, Any]] = None,
        session=None
    ) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """
        Предоставляет доступ пользователю к ресурсу.
        
        Args:
            telegram_id: Telegram ID пользователя
            resource_type: Тип ресурса
            resource_id: ID ресурса
            expires_in_days: Срок действия доступа в днях (None - бессрочно)
            params: Дополнительные параметры доступа
            session: SQLAlchemy сессия (опционально)
            
        Returns:
            Tuple[bool, Optional[Dict[str, Any]], Optional[str]]: 
                (успех, данные доступа, сообщение об ошибке)
        """
        close_session = False
        
        try:
            if session is None:
                session = session_scope().__enter__()
                close_session = True
            
            # Проверяем существование пользователя
            user = session.query(User).filter(User.telegram_id == telegram_id).first()
            if not user:
                return False, None, f"Пользователь {telegram_id} не найден"
            
            # Ищем существующий доступ
            existing_access = session.query(AccessControl).filter(
                AccessControl.telegram_id == telegram_id,
                AccessControl.resource_type == resource_type,
                AccessControl.resource_id == resource_id
            ).first()
            
            if existing_access:
                # Обновляем существующий доступ
                existing_access.is_active = True
                
                if expires_in_days is not None:
                    existing_access.expires_at = datetime.now() + timedelta(days=expires_in_days)
                else:
                    existing_access.expires_at = None
                
                if params:
                    existing_access.set_params(params)
                
                session.commit()
                
                result_data = {
                    "id": existing_access.id,
                    "telegram_id": existing_access.telegram_id,
                    "resource_type": existing_access.resource_type,
                    "resource_id": existing_access.resource_id,
                    "is_active": existing_access.is_active,
                    "expires_at": existing_access.expires_at,
                    "params": existing_access.get_params()
                }
                
                logger.info(f"Обновлен доступ для пользователя {telegram_id} к {resource_type}:{resource_id}")
                return True, result_data, None
            else:
                # Создаем новый доступ
                expires_at = datetime.now() + timedelta(days=expires_in_days) if expires_in_days is not None else None
                
                access_control = AccessControl(
                    telegram_id=telegram_id,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    expires_at=expires_at,
                    is_active=True
                )
                
                if params:
                    access_control.set_params(params)
                
                session.add(access_control)
                session.commit()
                
                result_data = {
                    "id": access_control.id,
                    "telegram_id": access_control.telegram_id,
                    "resource_type": access_control.resource_type,
                    "resource_id": access_control.resource_id,
                    "is_active": access_control.is_active,
                    "expires_at": access_control.expires_at,
                    "params": access_control.get_params()
                }
                
                logger.info(f"Предоставлен доступ для пользователя {telegram_id} к {resource_type}:{resource_id}")
                return True, result_data, None
                
        except Exception as e:
            if session:
                session.rollback()
            logger.error(f"Ошибка при предоставлении доступа для пользователя {telegram_id}: {str(e)}")
            return False, None, f"Произошла ошибка при предоставлении доступа: {str(e)}"
        finally:
            if close_session and session:
                session.close()
    
    @staticmethod
    def revoke_access(
        telegram_id: int, 
        resource_type: str, 
        resource_id: str,
        session=None
    ) -> Tuple[bool, Optional[str]]:
        """
        Отзывает доступ пользователя к ресурсу.
        
        Args:
            telegram_id: Telegram ID пользователя
            resource_type: Тип ресурса
            resource_id: ID ресурса
            session: SQLAlchemy сессия (опционально)
            
        Returns:
            Tuple[bool, Optional[str]]: (успех, сообщение об ошибке)
        """
        close_session = False
        
        try:
            if session is None:
                session = session_scope().__enter__()
                close_session = True
            
            access = session.query(AccessControl).filter(
                AccessControl.telegram_id == telegram_id,
                AccessControl.resource_type == resource_type,
                AccessControl.resource_id == resource_id
            ).first()
            
            if access:
                access.is_active = False
                session.commit()
                logger.info(f"Отозван доступ для пользователя {telegram_id} к {resource_type}:{resource_id}")
                return True, None
            else:
                logger.warning(f"Доступ не найден для пользователя {telegram_id} к {resource_type}:{resource_id}")
                return False, "Доступ не найден"
                
        except Exception as e:
            if session:
                session.rollback()
            logger.error(f"Ошибка при отзыве доступа для пользователя {telegram_id}: {str(e)}")
            return False, f"Произошла ошибка при отзыве доступа: {str(e)}"
        finally:
            if close_session and session:
                session.close()
    
    @staticmethod
    def get_resource_access_list(
        resource_type: str, 
        resource_id: str,
        session=None
    ) -> List[Dict[str, Any]]:
        """
        Получает список пользователей с доступом к ресурсу.
        
        Args:
            resource_type: Тип ресурса
            resource_id: ID ресурса
            session: SQLAlchemy сессия (опционально)
            
        Returns:
            List[Dict[str, Any]]: Список данных о доступе пользователей
        """
        close_session = False
        
        try:
            if session is None:
                session = session_scope().__enter__()
                close_session = True
            
            access_list = session.query(AccessControl).filter(
                AccessControl.resource_type == resource_type,
                AccessControl.resource_id == resource_id,
                AccessControl.is_active == True
            ).all()
            
            result = []
            for access in access_list:
                if not access.is_valid():
                    continue
                    
                user = session.query(User).filter(User.telegram_id == access.telegram_id).first()
                if not user:
                    continue
                    
                result.append({
                    "access_id": access.id,
                    "user_id": user.id,
                    "telegram_id": user.telegram_id,
                    "username": user.username,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "role": user.role,
                    "expires_at": access.expires_at,
                    "params": access.get_params()
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Ошибка при получении списка доступа к ресурсу {resource_type}:{resource_id}: {str(e)}")
            return []
        finally:
            if close_session and session:
                session.close() 