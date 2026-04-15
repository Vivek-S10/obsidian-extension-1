import sqlean as sqlite3
import sqlite_vec

DB_PATH = "knowledge_base.sqlite"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    conn.enable_load_extension(False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            path TEXT UNIQUE,
            hash TEXT,
            last_modified REAL
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS file_chunks (
            chunk_id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_id INTEGER,
            chunk_text TEXT,
            FOREIGN KEY(file_id) REFERENCES files(id) ON DELETE CASCADE
        )
    """)
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='vec_chunks'")
    if not cursor.fetchone():
        cursor.execute("""
            CREATE VIRTUAL TABLE vec_chunks USING vec0(
                chunk_id INTEGER PRIMARY KEY,
                chunk_embedding float[384]
            )
        """)
        
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized.")
