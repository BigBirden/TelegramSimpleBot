from aiogram import BaseMiddleware
from typing import Callable, Dict, Any, Awaitable
from aiogram.types import Message
from sqlalchemy import select

from models import User, UserRole, Dialog
from models import Message as DbMessage
from db import get_session

class MessageSaverMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        # Сохраняем сообщение перед обработкой
        if event.text and event.from_user:
            await self.save_message(event)
        
        # Продолжаем обработку
        return await handler(event, data)
    
    async def save_message(self, message: Message):
        if message.from_user:
            telegram_id = message.from_user.id
            async with get_session() as session:
                # Получаем пользователя
                user = await session.get(User, telegram_id)
                
                # Создаем пользователя если не существует
                if not user:
                    user = User(
                        telegram_id=telegram_id,
                        username=message.from_user.username,
                        first_name=message.from_user.first_name,
                        last_name=message.from_user.last_name,
                        role=UserRole.USER
                    )
                    session.add(user)
                    await session.flush()
                
                # Получаем диалог
                dialog = await session.scalar(
                    select(Dialog).where(Dialog.user_id == telegram_id)
                )
                
                # Создаем диалог если не существует
                if not dialog:
                    dialog = Dialog(user_id=telegram_id)
                    session.add(dialog)
                    await session.flush()
                
                # Сохраняем сообщение
                msg = DbMessage(
                    text=message.text,
                    dialog_id=dialog.id
                )
                session.add(msg)
                await session.commit()