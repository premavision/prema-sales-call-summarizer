from app.db.session import create_db_and_tables


def init_db() -> None:
    create_db_and_tables()
