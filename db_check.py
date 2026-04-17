import os
import sys

# Add the current directory to sys.path so we can import from backend
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from backend.database import get_db
except ImportError as e:
    print(f"Error: Could not find backend.database ({e}).")
    sys.exit(1)

def check_db():
    conn = get_db()
    cursor = conn.cursor()

    print("\n" + "="*80)
    print("📋 FULL DATABASE EXPORT")
    print("="*80)

    # 0. List All Tables
    print("\n--- 🏗️ DATABASE SCHEMA (TABLES) ---")
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cursor.fetchall()]
    print(f"Tables found: {', '.join(tables)}")

    # 1. Show All Files
    print("\n--- 📄 ALL FILES (files table) ---")
    cursor.execute("SELECT * FROM files")
    files = cursor.fetchall()
    if not files:
        print("Table is empty.")
    else:
        print(f"{'ID':<5} | {'Hash (Partial)':<15} | {'Path'}")
        print("-" * 80)
        for f in files:
            print(f"{f['id']:<5} | {f['hash'][:12]:<15} | {f['path']}")

    # 2. Show All Chunks
    print("\n--- 🧩 ALL TEXT CHUNKS (file_chunks table) ---")
    cursor.execute("SELECT * FROM file_chunks")
    chunks = cursor.fetchall()
    if not chunks:
        print("Table is empty.")
    else:
        print(f"{'ID':<5} | {'File ID':<8} | {'Snippet'}")
        print("-" * 80)
        for c in chunks:
            # Clean up newlines for cleaner console printing
            clean_text = c['chunk_text'].replace('\n', ' ')[:60]
            print(f"{c['chunk_id']:<5} | {c['file_id']:<8} | {clean_text}...")

    # 3. Show Vector IDs
    print("\n--- 🔢 VECTOR EMBEDDINGS (vec_chunks table) ---")
    try:
        cursor.execute("SELECT chunk_id FROM vec_chunks")
        vecs = cursor.fetchall()
        if not vecs:
            print("Table is empty.")
        else:
            print(f"Total Vectors: {len(vecs)}")
            vec_ids = [str(v[0]) for v in vecs]
            print(f"Stored Chunk IDs: {', '.join(vec_ids)}")
            print("Status: [Embeedings are stored as BLOBs and hidden from this view for readability]")
    except Exception as e:
        print(f"Error: {e}")

    # 4. Show Dismissed Links
    print("\n--- 🚫 DISMISSED LINKS (dismissed_links table) ---")
    cursor.execute("SELECT * FROM dismissed_links")
    dismissed = cursor.fetchall()
    if not dismissed:
        print("Table is empty (no links dismissed yet).")
    else:
        for d in dismissed:
            print(f"Dismissed: {os.path.basename(d['file1_path'])} <-> {os.path.basename(d['file2_path'])}")

    print("\n" + "="*80)
    print("✅ END OF DATABASE EXPORT")
    print("="*80 + "\n")

    conn.close()

if __name__ == "__main__":
    check_db()
