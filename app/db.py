from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase

engine = None
AsyncSessionLocal = None

def init_db(database_url):
    global engine, AsyncSessionLocal
    engine = create_async_engine(database_url)
    AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

@asynccontextmanager
async def get_session():
    if AsyncSessionLocal != None:
        async with AsyncSessionLocal() as session:
            try:
                yield session                       # <-- Отдаём сессию в код
                await session.commit()              # Если не было ошибок
            except Exception:
                await session.rollback()            # Откат при ошибке
                raise
            finally:
                await session.close()               # Всегда закрываем
    else:
        raise Exception("AsyncSessionLocal is None")
    

class Base(AsyncAttrs, DeclarativeBase):
    pass