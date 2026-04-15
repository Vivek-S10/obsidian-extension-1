import os
import struct
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from database import init_db, get_db
from pipeline import scan_directory, chunk_text, embed_texts

app = FastAPI(title="Semantic Local Discovery")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_startup():
    init_db()

class ScanRequest(BaseModel):
    vault_path: str

class EmbedRequest(BaseModel):
    vault_path: str

@app.post("/api/scan")
def scan_vault(req: ScanRequest):
    if not os.path.exists(req.vault_path) or not os.path.isdir(req.vault_path):
        raise HTTPException(status_code=400, detail="Invalid vault path")
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT path, hash FROM files")
    existing_files = {row['path']: row['hash'] for row in cursor.fetchall()}
    conn.close()

    new_or_mod, deleted, total = scan_directory(req.vault_path, existing_files)
    
    return {
        "is_valid": True,
        "stats": {
            "total_md_files": total,
            "new_or_modified": len(new_or_mod),
            "deleted": len(deleted)
        }
    }

def serialize_f32(vector):
    return struct.pack('%sf' % len(vector), *vector)

@app.post("/api/embed")
def embed_vault(req: EmbedRequest):
    if not os.path.exists(req.vault_path) or not os.path.isdir(req.vault_path):
        raise HTTPException(status_code=400, detail="Invalid vault path")
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT path, hash FROM files")
    existing_files = {row['path']: row['hash'] for row in cursor.fetchall()}
    
    new_or_mod, deleted, _ = scan_directory(req.vault_path, existing_files)
    
    for d_path in deleted:
        cursor.execute("SELECT id FROM files WHERE path=?", (d_path,))
        row = cursor.fetchone()
        if row:
            f_id = row['id']
            cursor.execute("DELETE FROM vec_chunks WHERE chunk_id IN (SELECT chunk_id FROM file_chunks WHERE file_id=?)", (f_id,))
            cursor.execute("DELETE FROM file_chunks WHERE file_id=?", (f_id,))
            cursor.execute("DELETE FROM files WHERE id=?", (f_id,))
            
    files_processed = 0
    chunks_created = 0
    
    for path, f_hash, mtime in new_or_mod:
        cursor.execute("SELECT id FROM files WHERE path=?", (path,))
        row = cursor.fetchone()
        if row:
            f_id = row['id']
            cursor.execute("DELETE FROM vec_chunks WHERE chunk_id IN (SELECT chunk_id FROM file_chunks WHERE file_id=?)", (f_id,))
            cursor.execute("DELETE FROM file_chunks WHERE file_id=?", (f_id,))
            cursor.execute("UPDATE files SET hash=?, last_modified=? WHERE id=?", (f_hash, mtime, f_id))
        else:
            cursor.execute("INSERT INTO files (path, hash, last_modified) VALUES (?, ?, ?)", (path, f_hash, mtime))
            f_id = cursor.lastrowid
            
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                text = f.read()
        except Exception:
            continue
            
        chunks = chunk_text(text)
        if not chunks:
            continue
            
        embeddings = embed_texts(chunks)
        for i, chunk in enumerate(chunks):
            cursor.execute("INSERT INTO file_chunks (file_id, chunk_text) VALUES (?, ?)", (f_id, chunk))
            chunk_id = cursor.lastrowid
            emb_blob = serialize_f32(embeddings[i])
            cursor.execute("INSERT INTO vec_chunks (chunk_id, chunk_embedding) VALUES (?, ?)", (chunk_id, emb_blob))
            chunks_created += 1
            
        files_processed += 1
        conn.commit()

    conn.close()
    
    return {
        "status": "completed",
        "files_processed": files_processed,
        "chunks_created": chunks_created
    }

@app.get("/api/search")
def search_vault(q: str, limit: int = 5):
    if not q:
        return {"results": []}
        
    query_emb = embed_texts([q])[0]
    query_blob = serialize_f32(query_emb)
    
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            file_chunks.chunk_text,
            files.path as file_path,
            vec_chunks.distance
        FROM vec_chunks
        JOIN file_chunks ON file_chunks.chunk_id = vec_chunks.chunk_id
        JOIN files ON files.id = file_chunks.file_id
        WHERE chunk_embedding MATCH ?
          AND k = ?
        ORDER BY distance
    """, (query_blob, limit))
    
    results = []
    for row in cursor.fetchall():
        results.append({
            "file_path": row['file_path'],
            "file_name": os.path.basename(row['file_path']),
            "chunk_text": row['chunk_text'],
            "distance": row['distance']
        })
        
    conn.close()
    return {"results": results}
