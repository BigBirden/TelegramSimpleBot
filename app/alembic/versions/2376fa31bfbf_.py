"""empty message

Revision ID: 2376fa31bfbf
Revises: cffefecefeb9
Create Date: 2025-06-10 22:05:23.281774

"""
from datetime import datetime
from sqlalchemy.orm import Session
from alembic import op
from typing import Sequence, Union

from app.models import User, Dialog, DialogUser, Message, UserRole


# revision identifiers, used by Alembic.
revision: str = '2376fa31bfbf'
down_revision: Union[str, None] = 'cffefecefeb9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    """Upgrade schema - add test data using proper SQLAlchemy ORM CRUD operations."""
    bind = op.get_bind()
    session = Session(bind=bind)

    # CREATE (Создание объектов)
    # 1. Создаем пользователей (одиночное добавление)
    admin = User(
        username="admin",
        first_name="Admin",
        last_name="System",
        role=UserRole.ADMIN
    )
    session.add(admin)  # Подготовка к сохранению

    # 2. Создаем пользователей (множественное добавление)
    user1 = User(
        username="user1",
        first_name="John",
        last_name="Doe",
        role=UserRole.USER
    )
    user2 = User(
        username="user2",
        first_name="Jane",
        last_name="Smith",
        role=UserRole.USER
    )
    session.add_all([user1, user2])  # Пакетное добавление

    # Фиксируем пользователей, чтобы получить их ID
    session.flush()

    # 3. Создаем диалог
    dialog = Dialog(created_at=datetime.utcnow())
    session.add(dialog)
    session.flush()  # Получаем ID диалога

    # 4. Добавляем участников диалога
    session.add_all([
        DialogUser(dialog_id=dialog.id, user_id=user1.id),
        DialogUser(dialog_id=dialog.id, user_id=user2.id)
    ])

    # 5. Создаем сообщения
    message1 = Message(
        text="Привет! Как дела?",
        created_at=datetime.utcnow(),
        user_id=user1.id,
        dialog_id=dialog.id
    )
    message2 = Message(
        text="Привет! Все отлично, спасибо!",
        created_at=datetime.utcnow(),
        user_id=user2.id,
        dialog_id=dialog.id
    )
    # Дополнительные сообщения от user1
    extra_message1 = Message(
        text="Как у тебя дела сегодня?",
        created_at=datetime.utcnow(),
        user_id=user1.id,
        dialog_id=dialog.id
    )

    extra_message2 = Message(
        text="Что нового у тебя?",
        created_at=datetime.utcnow(),
        user_id=user1.id,
        dialog_id=dialog.id
    )

    # Дополнительные сообщения от user2
    extra_message3 = Message(
        text="Все хорошо, спасибо за вопрос!",
        created_at=datetime.utcnow(),
        user_id=user2.id,
        dialog_id=dialog.id
    )

    extra_message4 = Message(
        text="Никаких особых новостей. А у тебя?",
        created_at=datetime.utcnow(),
        user_id=user2.id,
        dialog_id=dialog.id
    )
    session.add_all([message1, message2, extra_message1, extra_message2, extra_message3, extra_message4])

    # Фиксируем все изменения
    session.commit()

def downgrade() -> None:
    bind = op.get_bind()
    session = Session(bind=bind)

    # Удаляем сообщения, связанные с диалогами, созданными в upgrade()
    # Предположим, что в upgrade() создается один диалог, и запоминаем его created_at
    # Или используем уникальные идентификаторы пользователей, чтобы найти диалоги

    # Получаем пользователей по их username
    users = session.query(User).filter(User.username.in_(["admin", "user1", "user2"])).all()
    user_ids = [user.id for user in users]

    # Находим диалоги, связанные с этими пользователями через DialogUser
    dialog_ids = session.query(Dialog.id).join(DialogUser).filter(DialogUser.user_id.in_(user_ids)).all()
    dialog_ids = [id for (id,) in dialog_ids]

    # Удаляем сообщения, связанные с этими диалогами
    session.query(Message).filter(Message.dialog_id.in_(dialog_ids)).delete(synchronize_session=False)

    # Удаляем связи DialogUser
    session.query(DialogUser).filter(DialogUser.dialog_id.in_(dialog_ids)).delete(synchronize_session=False)

    # Удаляем диалоги
    session.query(Dialog).filter(Dialog.id.in_(dialog_ids)).delete(synchronize_session=False)

    # Удаляем пользователей
    session.query(User).filter(User.id.in_(user_ids)).delete(synchronize_session=False)

    session.commit()
    
    # Сброс счетчиков автоинкремента
    op.execute("SELECT setval('users_id_seq', 1, false);")
    op.execute("SELECT setval('dialogs_id_seq', 1, false);")
    op.execute("SELECT setval('messages_id_seq', 1, false);")
