from pathlib import Path

from sqlalchemy import create_engine

from src.config import DB_URL


def get_engine():
    return create_engine(DB_URL)


def run_sql_file(path: Path, params: dict | None = None) -> None:
    """Run a multi-statement SQL file in one transaction."""
    sql = Path(path).read_text()
    conn = get_engine().raw_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
        conn.commit()
    finally:
        conn.close()
