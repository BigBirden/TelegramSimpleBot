from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

engine = None

def init_db(database_url):
    global engine
    engine = create_engine(database_url)

def get_engine():
    if engine is None:
        raise RuntimeError("DB engine not initialized")
    return engine