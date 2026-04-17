import sys
import os
import json
import argparse
import struct
import logging
from mpi4py import MPI

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - Rank %(rank)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from database import get_db

def serialize_f32(vector):
    return struct.pack('%sf' % len(vector), *vector)

def worker_process(tasks, rank):
    from pipeline import chunk_text, embed_texts
    results = []
    if not tasks:
        logger.info(f"Rank {rank}: No tasks received.")
        return results
    
    logger.info(f"Rank {rank}: Received {len(tasks)} files to process.")
    
    for t in tasks:
        path, f_hash, mtime = t
        filename = os.path.basename(path)
        logger.info(f"Rank {rank}: Processing {filename}...")
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                text = f.read()
        except Exception as e:
            logger.error(f"Rank {rank}: Error reading {filename}: {e}")
            continue
            
        chunks = chunk_text(text)
        if not chunks:
            logger.warning(f"Rank {rank}: No text found in {filename}")
            continue
            
        embeddings = embed_texts(chunks)
        results.append({
            "path": path,
            "hash": f_hash,
            "mtime": mtime,
            "chunks": chunks,
            "embeddings": embeddings
        })
    logger.info(f"Rank {rank}: Finished processing {len(results)}/{len(tasks)} files.")
    return results

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--task-file", required=True)
    args = parser.parse_args()
    
    comm = MPI.COMM_WORLD
    rank = comm.Get_rank()
    size = comm.Get_size()
    
    chunks = None
    deleted = []
    if rank == 0:
        with open(args.task_file, 'r') as f:
            tasks_data = json.load(f)
            
        new_or_mod = tasks_data.get('new_or_mod', [])
        deleted = tasks_data.get('deleted', [])
        
        chunks = [[] for _ in range(size)]
        if size > 1:
            for i, task in enumerate(new_or_mod):
                worker_idx = (i % (size - 1)) + 1
                chunks[worker_idx].append(task)
        else:
            chunks[0] = new_or_mod
            
    my_tasks = comm.scatter(chunks, root=0)
    
    if rank == 0:
        logger.info("Master: Task distribution complete. Waiting for workers...")
        my_results = []
        if size == 1:
            my_results = worker_process(my_tasks, rank)
    else:
        my_results = worker_process(my_tasks, rank)
        
    all_results = comm.gather(my_results, root=0)
    
    if rank == 0:
        logger.info("Master: All results gathered. Committing to database...")
        conn = get_db()
        cursor = conn.cursor()
        
        # Process deleted
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
        
        for r_list in all_results:
            if not r_list: continue
            for item in r_list:
                path = item['path']
                f_hash = item['hash']
                mtime = item['mtime']
                
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
                    
                for i, chunk in enumerate(item['chunks']):
                    cursor.execute("INSERT INTO file_chunks (file_id, chunk_text) VALUES (?, ?)", (f_id, chunk))
                    chunk_id = cursor.lastrowid
                    emb_blob = serialize_f32(item['embeddings'][i])
                    cursor.execute("INSERT INTO vec_chunks (chunk_id, chunk_embedding) VALUES (?, ?)", (chunk_id, emb_blob))
                    chunks_created += 1
                    
                files_processed += 1
                
        conn.commit()
        conn.close()
        logger.info(f"Master: Final bulk insertion complete. Processed {files_processed} files, created {chunks_created} chunks.")
        
        with open(args.task_file + ".out", "w") as f:
            json.dump({
                "files_processed": files_processed,
                "chunks_created": chunks_created
            }, f)

if __name__ == "__main__":
    # Inject rank into logging
    comm = MPI.COMM_WORLD
    rank = comm.Get_rank()
    logging.LoggerAdapter(logger, {"rank": rank}) # This style doesn't work for basicConfig, but we can do it manually
    
    # Simple fix for the rank format:
    import logging
    old_factory = logging.getLogRecordFactory()
    def record_factory(*args, **kwargs):
        record = old_factory(*args, **kwargs)
        record.rank = rank
        return record
    logging.setLogRecordFactory(record_factory)
    
    main()
