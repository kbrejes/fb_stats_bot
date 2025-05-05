from src.storage.database import get_session
from src.storage.models import User, Account, accounts_to_users

def fix_accounts_to_users():
    session = get_session()
    try:
        # Получаем все аккаунты
        accounts = session.query(Account).all()
        print(f"Найдено {len(accounts)} аккаунтов")
        
        fixed = 0
        for account in accounts:
            # Проверяем существование связи
            exists = session.query(accounts_to_users).filter_by(
                user_id=account.telegram_id,
                account_id=account.id
            ).first()
            
            if not exists:
                # Добавляем связь
                session.execute(
                    accounts_to_users.insert().values(
                        user_id=account.telegram_id,
                        account_id=account.id
                    )
                )
                fixed += 1
                print(f"Добавлена связь: user_id={account.telegram_id}, account_id={account.id}")
                
        session.commit()
        print(f"\nИсправлено {fixed} связей")
        
    finally:
        session.close()

if __name__ == "__main__":
    fix_accounts_to_users() 