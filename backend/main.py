import os
import struct
import requests
import tempfile
import json
import subprocess
import sys
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from database import init_db, get_db
from pipeline import scan_directory, chunk_text, embed_texts

app = FastAPI(title="Semantic Local Discovery")

NUM_MPI_WORKERS = int(os.environ.get("NUM_MPI_WORKERS", "4"))

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
    num_workers: int = 4

class AskRequest(BaseModel):
    query: str
    model: str = "llama3.2:latest"

def serialize_f32(vector):
    return struct.pack('%sf' % len(vector), *vector)

def perform_search(query: str, limit: int = 5):
    if not query:
        return []
        
    query_emb = embed_texts([query])[0]
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
    return results

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

@app.post("/api/embed")
def embed_vault(req: EmbedRequest):
    if not os.path.exists(req.vault_path) or not os.path.isdir(req.vault_path):
        raise HTTPException(status_code=400, detail="Invalid vault path")
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT path, hash FROM files")
    existing_files = {row['path']: row['hash'] for row in cursor.fetchall()}
    conn.close()
    
    new_or_mod, deleted, _ = scan_directory(req.vault_path, existing_files)
    
    if not new_or_mod and not deleted:
        return {
            "status": "completed",
            "files_processed": 0,
            "chunks_created": 0,
            "message": "No changes detected."
        }
        
    with tempfile.NamedTemporaryFile('w', delete=False, suffix='.json') as f:
        json.dump({
            "new_or_mod": new_or_mod,
            "deleted": deleted
        }, f)
        temp_file_name = f.name
        
    # Enforce system limit of 7 workers. Default to 4 if exceeded or not provided.
    eff_workers = req.num_workers
    if eff_workers > 7 or eff_workers < 1:
        eff_workers = 4
        
    try:
        worker_script = os.path.join(os.path.dirname(__file__), "mpi_worker.py")
        cmd = ["/opt/homebrew/bin/mpirun", "-n", str(eff_workers + 1), sys.executable, worker_script, "--task-file", temp_file_name]
        subprocess.run(cmd, check=True)
        
        with open(temp_file_name + ".out", "r") as f:
            stats = json.load(f)
            
        files_processed = stats.get("files_processed", 0)
        chunks_created = stats.get("chunks_created", 0)
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"MPI embedding subprocess failed: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"MPI embedding failed: {str(e)}")
    finally:
        if os.path.exists(temp_file_name):
            os.remove(temp_file_name)
        if os.path.exists(temp_file_name + ".out"):
            os.remove(temp_file_name + ".out")
    
    return {
        "status": "completed",
        "files_processed": files_processed,
        "chunks_created": chunks_created
    }

@app.get("/api/search")
def search_api(q: str, limit: int = 5):
    return {"results": perform_search(q, limit)}

@app.post("/api/ask")
def ask_api(req: AskRequest):
    results = perform_search(req.query, limit=5)
    if not results:
        return {"answer": "I couldn't find any relevant information in your notes to answer that.", "sources": []}

    context_parts = []
    sources = []
    for r in results:
        context_parts.append(f"Content from {r['file_name']}:\n{r['chunk_text']}")
        sources.append({"file_name": r['file_name'], "file_path": r['file_path']})

    context_text = "\n\n---\n\n".join(context_parts)
    prompt = f"""You are a helpful assistant that answers questions based ONLY on the provided local obsidian notes.
If the answer is not in the context, say that you don't know based on the available notes.

CONTEXT FROM LOCAL NOTES:
{context_text}

USER QUESTION:
{req.query}

ANSWER:"""

    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": req.model,
                "prompt": prompt,
                "stream": False
            },
            timeout=120
        )
        response.raise_for_status()
        data = response.json()
        return {
            "answer": data.get("response", "No response from model."),
            "sources": sources
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ollama error: {str(e)}")

@app.get("/api/discover_links")
def discover_links(limit: int = 5):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT chunk_id, chunk_text, file_id FROM file_chunks ORDER BY chunk_id DESC LIMIT 50
    """)
    samples = cursor.fetchall()
    
    suggestions = []
    seen_pairs = set()
    
    for sample in samples:
        if len(suggestions) >= limit:
            break
            
        c_id = sample['chunk_id']
        f1_id = sample['file_id']
        t1 = sample['chunk_text']
        
        cursor.execute("""
            SELECT b.file_id, b.chunk_text, vec_chunks.distance
            FROM vec_chunks
            JOIN file_chunks b ON b.chunk_id = vec_chunks.chunk_id
            WHERE chunk_embedding MATCH (
                SELECT chunk_embedding FROM vec_chunks WHERE chunk_id = ?
            ) AND k = 10 AND b.file_id != ? AND distance < 0.15
            ORDER BY distance
        """, (c_id, f1_id))
        
        matches = cursor.fetchall()
        for m in matches:
            if len(suggestions) >= limit:
                break
            f2_id = m['file_id']
            pair = tuple(sorted((f1_id, f2_id)))
            if pair in seen_pairs:
                continue
            seen_pairs.add(pair)
            
            cursor.execute("SELECT path FROM files WHERE id=?", (f1_id,))
            path1 = cursor.fetchone()['path']
            cursor.execute("SELECT path FROM files WHERE id=?", (f2_id,))
            path2 = cursor.fetchone()['path']
            
            cursor.execute("SELECT 1 FROM dismissed_links WHERE (file1_path=? AND file2_path=?) OR (file1_path=? AND file2_path=?)", (path1, path2, path2, path1))
            if cursor.fetchone():
                continue
                
            try:
                with open(path1, 'r', encoding='utf-8') as f:
                    c1 = f.read()
                with open(path2, 'r', encoding='utf-8') as f:
                    c2 = f.read()
                basename_1 = os.path.basename(path1)
                basename_2 = os.path.basename(path2)
                if f"[[Related: {basename_2}]]" in c1 or f"[[Related: {basename_1}]]" in c2:
                    continue
            except Exception:
                continue
                
            t2 = m['chunk_text']
            prompt = f"Given these two excerpts from different notes:\nExcerpt 1: {t1}\nExcerpt 2: {t2}\nWhy are they related? Answer in ONE short sentence. Be concise and direct."
            reason = "Highly related content based on vector similarity."
            try:
                response = requests.post(
                    "http://localhost:11434/api/generate",
                    json={
                        "model": "llama3.2:latest",
                        "prompt": prompt,
                        "stream": False
                    },
                    timeout=30
                )
                if response.status_code == 200:
                    reason = response.json().get('response', reason).strip()
            except Exception:
                pass
                
            suggestions.append({
                "file1_path": path1,
                "file1_name": os.path.basename(path1),
                "file2_path": path2,
                "file2_name": os.path.basename(path2),
                "distance": m['distance'],
                "reason": reason
            })
            
    conn.close()
    return {"suggestions": suggestions}

class LinkPairRequest(BaseModel):
    file1_path: str
    file2_path: str

@app.post("/api/confirm_link")
def confirm_link(req: LinkPairRequest):
    try:
        basename_1 = os.path.basename(req.file1_path)
        basename_2 = os.path.basename(req.file2_path)
        with open(req.file1_path, 'a', encoding='utf-8') as f:
            f.write(f"\n\n[[Related: {basename_2}]]\n")
        with open(req.file2_path, 'a', encoding='utf-8') as f:
            f.write(f"\n\n[[Related: {basename_1}]]\n")
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/dismiss_link")
def dismiss_link(req: LinkPairRequest):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO dismissed_links (file1_path, file2_path) VALUES (?, ?)", (req.file1_path, req.file2_path))
    conn.commit()
    conn.close()
    return {"status": "success"}
