# create_tables.py
from app.db import Base, engine
from app.models import Character

print("Creating database tables...")
Base.metadata.create_all(bind=engine)
print("Tables created successfully!")