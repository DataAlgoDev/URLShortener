from database import Base
from sqlalchemy import Column, Integer, String, Text


class URLModel(Base):
    __tablename__ = "urls"

    sln = Column(Integer, primary_key=True, index=True, autoincrement=True)
    uid = Column(String(7), unique=True, index=False, nullable=True)
    l_url = Column(Text, nullable=False)
