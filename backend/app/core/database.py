import psycopg2
from psycopg2.extras import RealDictCursor, Json
from psycopg2.extensions import register_adapter
from app.core.config import settings
from typing import Generator
import json

# Register JSON adapter for Python dicts/lists to PostgreSQL JSONB
register_adapter(dict, Json)
register_adapter(list, Json)

def get_db_connection():
    """Create database connection using settings"""
    return psycopg2.connect(
        host=settings.PGHOST,
        port=settings.PGPORT,
        user=settings.PGUSER,
        password=settings.PGPASSWORD,
        database=settings.PGDATABASE
    )

def get_db() -> Generator[psycopg2.extensions.connection, None, None]:
    """Dependency to get database connection"""
    conn = get_db_connection()
    try:
        yield conn
    finally:
        conn.close()

def execute_query(query: str, params: tuple = None, fetch_one: bool = False):
    """Execute database query with error handling"""
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params)
            conn.commit()  # Commit the transaction
            
            # Check if query returns results (SELECT, WITH, or queries with RETURNING clause)
            query_upper = query.strip().upper()
            should_fetch = (
                query_upper.startswith('SELECT') or 
                query_upper.startswith('WITH') or
                'RETURNING' in query_upper
            )
            
            if should_fetch:
                if fetch_one:
                    return cur.fetchone()
                else:
                    return cur.fetchall()
            else:
                # For INSERT/UPDATE/DELETE queries without RETURNING, return None
                return None
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()
