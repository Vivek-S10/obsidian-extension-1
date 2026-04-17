# API Contracts

All endpoints live under `/api`.

## 1. `POST /api/scan`
Validates the vault path, recursively scans for markdown files, and compares them with the current database to return the processing delta.

**Request Body:**
```json
{
  "vault_path": "/absolute/path/to/vault"
}
```

**Response (200 OK):**
```json
{
  "is_valid": true,
  "stats": {
    "total_md_files": 120,
    "new_or_modified": 5,
    "deleted": 1
  }
}
```
**Response (400 Bad Request):**
Path is invalid or does not exist.

## 2. `POST /api/embed`
Initiates the chunking and embedding inference for new/modified files in the specified valid path. 

**Request Body:**
```json
{
  "vault_path": "/absolute/path/to/vault"
}
```

**Response (200 OK):**
```json
{
  "status": "completed",
  "files_processed": 5,
  "chunks_created": 30
}
```

## 3. `GET /api/search`
Performs a fast semantic cosine similarity lookup on the SQLite database using `sqlite-vec`.

**Query Parameters:**
- `q`: Target string to search for.
- `limit`: (Optional) Integer. Default 10.

**Response (200 OK):**
```json
{
  "results": [
    {
      "file_path": "/absolute/path/to/vault/File.md",
      "file_name": "File.md",
      "chunk_text": "This is a section of text matching...",
      "distance": 0.125432
    }
  ]
}

## 4. `POST /api/ask`
Performs a semantic search to retrieve context and then queries a local Ollama instance to generate a natural language response.

**Request Body:**
```json
{
  "query": "What are the key themes in my notes?",
  "model": "llama3"
}
```

**Response (200 OK):**
```json
{
  "answer": "Based on your notes, the key themes are...",
  "sources": [
    {
      "file_name": "Notes.md",
      "file_path": "/path/to/Notes.md"
    }
  ]
}
```
```

## 5. `GET /api/discover_links`
Calculates or retrieves top semantic file pairs.

**Response (200 OK):**
```json
{
  "suggestions": [
    {
      "file1_path": "/path/A.md",
      "file1_name": "A.md",
      "file2_path": "/path/B.md",
      "file2_name": "B.md",
      "distance": 0.1,
      "reason": "Both notes discuss XYZ."
    }
  ]
}
```

## 6. `POST /api/confirm_link`
Appends a bidirectional link to both files.

**Request Body:**
```json
{
  "file1_path": "/path/A.md",
  "file2_path": "/path/B.md"
}
```

**Response (200 OK):**
```json
{"status": "success"}
```

## 7. `POST /api/dismiss_link`
Dismisses a suggested link pair.

**Request Body:**
```json
{
  "file1_path": "/path/A.md",
  "file2_path": "/path/B.md"
}
```

**Response (200 OK):**
```json
{"status": "success"}
```
