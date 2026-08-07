from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from openbilanz.core.config import DATABASE_URL

engine = create_engine(DATABASE_URL, echo=False)

SessionLocal = sessionmaker(bind=engine)

Base = declarative_base()


from openbilanz.database import models  # noqa: E402, F401


def create_database():
    Base.metadata.create_all(engine)
