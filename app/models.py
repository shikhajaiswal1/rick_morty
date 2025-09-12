# app/models.py
from sqlalchemy import Column, Integer, String
from app.db import Base

class Character(Base):
    __tablename__ = "characters"  # Table name in PostgreSQL

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    status = Column(String)
    species = Column(String)
    origin = Column(String)