from environment import DATABASE_URL
from sqlalchemy import Column, Integer, String, Text, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()


class URLModel(Base):
    __tablename__ = "urls"

    sln = Column(Integer, primary_key=True, index=True, autoincrement=True)
    uid = Column(String(7), unique=True, index=False, nullable=True)
    l_url = Column(Text, nullable=False)
    clicks = Column(Integer, server_default="0", default=0, nullable=False)


engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
