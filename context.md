# Context: Semantic Local Discovery

## Project Mission
Build a local-first semantic search engine over a folder of Markdown files (Obsidian vaults). Allows Natural Language Search based on intent and context rather than exact word matching.

## Architecture
- **Backend**: Python 3, FastAPI
- **Frontend**: React (Vite) + Vanilla CSS (No Tailwind)
- **Database**: SQLite + `sqlite-vec` (Vector Storage Extension)
- **Embedding Model**: `all-MiniLM-L6-v2` (Sentence-Transformers)

## Core Functional Workflow
1. **Scan & Validate**: Accepts an absolute local path. Recursively finds `.md` files. Generates MD5 file hashes and compares against the local SQLite database to detect new, modified, or deleted files (Smart Sync).
2. **Text Processing & Vectorization**: Breaks markdown files down into chunks of 500 characters with a 50-character overlap. Translates these chunks into 384-dimensional vector embeddings locally via `all-MiniLM-L6-v2`.
3. **Persistent Storage**: Stores file metadata and vector embeddings into a standalone SQLite DB. The database schema links files into text chunks and chunks into their high-dimensional representations in `vec0` tables.
4. **Semantic Search**: Hashes a user's prompt using the identical pipeline and matches it against the stored chunks via Cosine Similarity (`distance`). Returns file reference, name, matched text, and distance.

## Technical Guardrails
- **Zero-Cloud Policy**: Data and inference strictly local.
- **Stateless Search**: No search properties/queries saved between launches.
- **Binary Portability**: The app state must persist inside a single `knowledge_base.sqlite` file.
- **No Mock Data**: Ensure the frontend always hits real Python endpoints.
- **Librarian Mode**: All API changes and architecture updates must reflect here first.
