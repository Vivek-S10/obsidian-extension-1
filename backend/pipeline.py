import os
import hashlib
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
_model = None

def get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        logger.info("Loading SentenceTransformer model...")
        _model = SentenceTransformer('all-MiniLM-L6-v2')
    return _model

def get_file_hash(filepath):
    hasher = hashlib.md5()
    try:
        with open(filepath, 'rb') as f:
            buf = f.read()
            hasher.update(buf)
        return hasher.hexdigest()
    except Exception as e:
        logger.error(f"Error reading file {filepath}: {e}")
        return None

def scan_directory(vault_path, existing_files):
    found_paths = set()
    new_or_modified = []
    
    for root, _, files in os.walk(vault_path):
        for file in files:
            if file.endswith('.md'):
                full_path = os.path.join(root, file)
                found_paths.add(full_path)
                file_hash = get_file_hash(full_path)
                if file_hash:
                    if full_path not in existing_files or existing_files[full_path] != file_hash:
                        new_or_modified.append((full_path, file_hash, os.path.getmtime(full_path)))
                        
    vault_path_abs = os.path.abspath(vault_path)
    deleted = []
    for path in existing_files:
        path_abs = os.path.abspath(path)
        if path_abs.startswith(vault_path_abs):
            if path not in found_paths:
                deleted.append(path)
                
    return new_or_modified, deleted, len(found_paths)

def chunk_text(text, chunk_size=500, overlap=50):
    chunks = []
    if not text:
        return chunks
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += (chunk_size - overlap)
    return chunks

def embed_texts(texts):
    if not texts:
        return []
    m = get_model()
    embeddings = m.encode(texts)
    return embeddings.tolist()
