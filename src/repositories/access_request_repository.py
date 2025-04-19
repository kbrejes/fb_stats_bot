"""
Репозиторий для работы с запросами доступа.
"""
from datetime import datetime
from typing import List, Optional, Dict, Any

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc

from src.storage.database import get_session
from src.storage.models import AccessRequest, AccessControl, User
from src.utils.logger import get_logger

logger = get_logger(__name__)


class AccessRequestRepository:
    """Репозиторий для работы с запросами доступа от партнеров."""
    
    def __init__(self, session: Optional[Session] = None):
        """
        Инициализирует репозиторий.
        
        Args:
            session: Сессия SQLAlchemy (опционально).
                    Если не предоставлена, будет создана новая сессия.
        """
        self._session = session
    
    @property
    def session(self) -> Session:
        """
        Возвращает текущую сессию или создает новую, если сессия не была предоставлена.
        
        Returns:
            Сессия SQLAlchemy.
        """
        if self._session is None:
            self._session = get_session()
            self._close_session = True
        else:
            self._close_session = False
        return self._session
    
    def close(self):
        """Закрывает сессию, если она была создана этим репозиторием."""
        if getattr(self, '_close_session', False) and self._session:
            self._session.close()
            self._session = None
    
    def create_request(
        self, 
        telegram_id: int, 
        resource_type: str, 
        resource_id: str, 
        message: Optional[str] = None,
        requested_duration: int = 30
    ) -> Optional[AccessRequest]:
        """
        Создает новый запрос на доступ.
        
        Args:
            telegram_id: Telegram ID пользователя.
            resource_type: Тип ресурса.
            resource_id: ID ресурса.
            message: Сообщение от пользователя.
            requested_duration: Запрашиваемая длительность доступа в днях.
            
        Returns:
            Объект AccessRequest или None в случае ошибки.
        """
        try:
            # Проверяем существование пользователя
            user = self.session.query(User).filter(User.telegram_id == telegram_id).first()
            if not user:
                logger.error(f"User {telegram_id} not found")
                return None
            
            # Проверяем, что пользователь не таргетолог и не админ (им не нужны запросы)
            if user.is_targetologist():
                logger.warning(f"User {telegram_id} is a targetologist or admin, no need for access request")
                return None
            
            # Проверяем наличие активного запроса
            existing_request = self.session.query(AccessRequest).filter(
                AccessRequest.telegram_id == telegram_id,
                AccessRequest.resource_type == resource_type,
                AccessRequest.resource_id == resource_id,
                AccessRequest.status == "pending"
            ).first()
            
            if existing_request:
                logger.info(f"Access request for user {telegram_id} already exists, updating message")
                if message:
                    existing_request.message = message
                existing_request.requested_duration = requested_duration
                existing_request.created_at = datetime.now()  # Обновляем дату создания
                self.session.commit()
                return existing_request
            
            # Создаем новый запрос
            access_request = AccessRequest(
                telegram_id=telegram_id,
                resource_type=resource_type,
                resource_id=resource_id,
                message=message,
                requested_duration=requested_duration,
                status="pending"
            )
            
            self.session.add(access_request)
            self.session.commit()
            logger.info(f"Created access request for user {telegram_id} to {resource_type}:{resource_id}")
            return access_request
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error creating access request for user {telegram_id}: {str(e)}")
            return None
    
    def get_pending_requests(self) -> List[AccessRequest]:
        """
        Получает список ожидающих запросов.
        
        Returns:
            Список объектов AccessRequest со статусом "pending".
        """
        try:
            pending_requests = self.session.query(AccessRequest).filter(
                AccessRequest.status == "pending"
            ).order_by(desc(AccessRequest.created_at)).all()
            
            return pending_requests
        except Exception as e:
            logger.error(f"Error fetching pending requests: {str(e)}")
            return []
    
    def get_user_requests(self, telegram_id: int, include_processed: bool = False) -> List[AccessRequest]:
        """
        Получает список запросов пользователя.
        
        Args:
            telegram_id: Telegram ID пользователя.
            include_processed: Включать обработанные запросы.
            
        Returns:
            Список объектов AccessRequest для указанного пользователя.
        """
        try:
            query = self.session.query(AccessRequest).filter(
                AccessRequest.telegram_id == telegram_id
            )
            
            if not include_processed:
                query = query.filter(AccessRequest.status == "pending")
            
            requests = query.order_by(desc(AccessRequest.created_at)).all()
            
            return requests
        except Exception as e:
            logger.error(f"Error fetching requests for user {telegram_id}: {str(e)}")
            return []
    
    def get_request_by_id(self, request_id: int) -> Optional[AccessRequest]:
        """
        Получает запрос по его ID.
        
        Args:
            request_id: ID запроса.
            
        Returns:
            Объект AccessRequest или None, если запрос не найден.
        """
        try:
            return self.session.query(AccessRequest).filter(
                AccessRequest.id == request_id
            ).first()
        except Exception as e:
            logger.error(f"Error fetching request {request_id}: {str(e)}")
            return None
    
    def approve_request(
        self, 
        request_id: int, 
        admin_id: int, 
        admin_notes: Optional[str] = None,
        custom_duration: Optional[int] = None
    ) -> Optional[AccessControl]:
        """
        Одобряет запрос и создает соответствующее разрешение.
        
        Args:
            request_id: ID запроса.
            admin_id: Telegram ID администратора.
            admin_notes: Заметки администратора.
            custom_duration: Пользовательская длительность доступа в днях.
            
        Returns:
            Созданный объект AccessControl или None в случае ошибки.
        """
        try:
            # Проверяем права администратора
            admin = self.session.query(User).filter(User.telegram_id == admin_id).first()
            if not admin or not admin.is_admin():
                logger.error(f"User {admin_id} is not an admin")
                return None
            
            # Находим запрос
            request = self.session.query(AccessRequest).filter(
                AccessRequest.id == request_id
            ).first()
            
            if not request:
                logger.error(f"Request {request_id} not found")
                return None
            
            if request.status != "pending":
                logger.warning(f"Request {request_id} already processed")
                return None
            
            # Одобряем запрос
            request.approve(admin_id=admin_id, admin_notes=admin_notes)
            
            # Определяем длительность доступа
            duration = custom_duration if custom_duration is not None else request.requested_duration
            
            # Создаем разрешение
            from src.repositories.access_control_repository import AccessControlRepository
            access_control_repo = AccessControlRepository(session=self.session)
            
            access_control = access_control_repo.grant_access(
                telegram_id=request.telegram_id,
                resource_type=request.resource_type,
                resource_id=request.resource_id,
                expires_in_days=duration
            )
            
            self.session.commit()
            logger.info(f"Approved request {request_id} and granted access for user {request.telegram_id}")
            return access_control
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error approving request {request_id}: {str(e)}")
            return None
    
    def reject_request(
        self, 
        request_id: int, 
        admin_id: int, 
        admin_notes: Optional[str] = None
    ) -> bool:
        """
        Отклоняет запрос.
        
        Args:
            request_id: ID запроса.
            admin_id: Telegram ID администратора.
            admin_notes: Заметки администратора.
            
        Returns:
            True, если запрос успешно отклонен, иначе False.
        """
        try:
            # Проверяем права администратора
            admin = self.session.query(User).filter(User.telegram_id == admin_id).first()
            if not admin or not admin.is_admin():
                logger.error(f"User {admin_id} is not an admin")
                return False
            
            # Находим запрос
            request = self.session.query(AccessRequest).filter(
                AccessRequest.id == request_id
            ).first()
            
            if not request:
                logger.error(f"Request {request_id} not found")
                return False
            
            if request.status != "pending":
                logger.warning(f"Request {request_id} already processed")
                return False
            
            # Отклоняем запрос
            request.reject(admin_id=admin_id, admin_notes=admin_notes)
            
            self.session.commit()
            logger.info(f"Rejected request {request_id} from user {request.telegram_id}")
            return True
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error rejecting request {request_id}: {str(e)}")
            return False
    
    def get_processed_requests(
        self,
        status: Optional[str] = None,
        limit: int = 50
    ) -> List[AccessRequest]:
        """
        Получает список обработанных запросов.
        
        Args:
            status: Статус запросов ("approved" или "rejected").
                   Если None, возвращаются все обработанные запросы.
            limit: Максимальное количество запросов.
            
        Returns:
            Список объектов AccessRequest.
        """
        try:
            query = self.session.query(AccessRequest).filter(
                AccessRequest.status != "pending"
            )
            
            if status in ["approved", "rejected"]:
                query = query.filter(AccessRequest.status == status)
            
            processed_requests = query.order_by(
                desc(AccessRequest.processed_at)
            ).limit(limit).all()
            
            return processed_requests
        except Exception as e:
            logger.error(f"Error fetching processed requests: {str(e)}")
            return [] 