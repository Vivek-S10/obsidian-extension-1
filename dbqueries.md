# Database Queries for Local Semantic Discovery

This document provides common SQL queries to interact with the `knowledge_base.sqlite` database. Note that vector queries require the `sqlite-vec` extension to be loaded.

## 1. File & Knowledge Base Overview

### Check All Indexed Files
Shows all files currently in the database along with their content hashes.
```sql
SELECT id, path, hash FROM files;
```

### Knowledge Base Statistics
Returns the total number of files and chunks indexed.
```sql
SELECT 
    (SELECT COUNT(*) FROM files) as total_files,
    (SELECT COUNT(*) FROM file_chunks) as total_chunks;
```

---

## 2. Content & Chunk Management

### Retrieve All Chunks for a Specific File
Replace `1` with the actual file ID from clinical research.
```sql
SELECT chunk_id, chunk_text 
FROM file_chunks 
WHERE file_id = 1;
```

### Keyword Search within Chunks
Perform a traditional SQL search for specific keywords in your notes.
```sql
SELECT files.path, file_chunks.chunk_text
FROM file_chunks
JOIN files ON files.id = file_chunks.file_id
WHERE chunk_text LIKE '%obsidian%';
```

---

## 3. Vector & Semantic Queries
*Note: These queries use `sqlite-vec` specific syntax.*

### Semantic Search (Vector Match)
Finds chunks most similar to a provided embedding (blob).
```sql
SELECT 
    file_chunks.chunk_text,
    files.path,
    vec_chunks.distance
FROM vec_chunks
JOIN file_chunks ON file_chunks.chunk_id = vec_chunks.chunk_id
JOIN files ON files.id = file_chunks.file_id
WHERE chunk_embedding MATCH ? -- Your serialized vector here
  AND k = 5
ORDER BY distance;
```

---

## 4. Metadata & Cleanup

### View Recently Modified Files
```sql
SELECT path, datetime(last_modified, 'unixepoch') as last_mod
FROM files
ORDER BY last_modified DESC
LIMIT 10;
```

### Check Dismissed Links
See which pairs of files you have marked to never link again.
```sql
SELECT file1_path, file2_path FROM dismissed_links;
```

### Purge All Data
Resets the knowledge base completely.
```sql
DELETE FROM vec_chunks;
DELETE FROM file_chunks;
DELETE FROM files;
```
