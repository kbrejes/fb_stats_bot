from src.storage.database import get_session
from src.storage.models import User, Account, accounts_to_users

def check_user_accounts(user_id: int):
    session = get_session()
    try:
        # Получаем пользователя
        user = session.query(User).filter_by(telegram_id=user_id).first()
        if not user:
            print(f"Пользователь {user_id} не найден")
            return
            
        print(f"\nИнформация о пользователе:")
        print(f"ID: {user.telegram_id}")
        print(f"Username: {user.username}")
        print(f"Роль: {user.role}")
        
        # Проверяем прямые аккаунты (через telegram_id)
        direct_accounts = session.query(Account).filter_by(telegram_id=user_id).all()
        print(f"\nПрямые аккаунты (через telegram_id):")
        for acc in direct_accounts:
            print(f"- ID: {acc.id}, FB ID: {acc.fb_account_id}, Name: {acc.name}")
            
        # Проверяем shared аккаунты (через accounts_to_users)
        shared_accounts = user.shared_accounts
        print(f"\nShared аккаунты (через accounts_to_users):")
        for acc in shared_accounts:
            print(f"- ID: {acc.id}, FB ID: {acc.fb_account_id}, Name: {acc.name}")
            
    finally:
        session.close()

if __name__ == "__main__":
    check_user_accounts(7636777939) 