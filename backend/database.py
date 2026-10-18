from sqlalchemy import Column, ForeignKey, Integer, String, Text, create_engine
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

from backend.environment import DATABASE_URL

Base = declarative_base()


class URLModel(Base):
    __tablename__ = "urls"

    sln = Column(Integer, primary_key=True, index=True, autoincrement=True)
    uid = Column(String(7), unique=True, index=False, nullable=True)
    s_url = Column(Text, nullable=True)
    l_url = Column(Text, nullable=False)
    clicks = Column(Integer, server_default="0", default=0, nullable=False)
    user_id = Column(
        Integer,
        ForeignKey("users.user_id", ondelete="SET NULL"),
        nullable=True,
    )
    owner = relationship("UserModel", back_populates="urls")


class UserModel(Base):
    __tablename__ = "users"
    user_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_name = Column(Text, nullable=False, index=True, unique=True)
    hashed_pwd = Column(String(255), nullable=False)
    urls = relationship(
        "URLModel", back_populates="owner", cascade="all, delete-orphan"
    )


engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
