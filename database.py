from sqlmodel import SQLModel, create_engine, Session
import os

database_url = os.environ.get("DATABASE_URL")

if database_url and database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

if not database_url:
    sqlite_file_name = "database.db"
    database_url = f"sqlite:///{sqlite_file_name}"
    connect_args = {"check_same_thread": False}
else:
    connect_args = {}

engine = create_engine(database_url, echo=False, connect_args=connect_args)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session