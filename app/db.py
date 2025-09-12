# app/db.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# PostgreSQL connection URL format:
# postgresql://username:password@localhost:5432/database_name
DATABASE_URL = "postgresql://postgres:password1234@localhost:5432/rickmorty_db"

# Create database engine
engine = create_engine(DATABASE_URL)

# Session to interact with the database
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for defining models (tables)
Base = declarative_base()
