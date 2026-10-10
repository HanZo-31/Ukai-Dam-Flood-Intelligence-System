import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

load_dotenv(Path(__file__).resolve().parents[4] / ".env")

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://ukai:ukai@localhost:5432/ukai",
)

connection_url = make_url(DATABASE_URL)
if connection_url.host == "localhost":
    connection_url = connection_url.set(host="127.0.0.1")
connection_url = connection_url.update_query_dict({"connect_timeout": connection_url.query.get("connect_timeout", "5")})

engine = create_engine(
    connection_url,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)
