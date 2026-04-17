import os
import sys
import argparse
import logging
from database import get_db

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def delete_vault(vault_path):
    if not vault_path:
        logger.error("No vault path provided.")
        return

    # Normalize path to ensure it matches correctly in the DB
    # We use abspath to ensure consistency if the DB contains absolute paths
    vault_path_abs = os.path.abspath(vault_path)
    # Ensure it ends with a separator to avoid matching partial directory names
    if not vault_path_abs.endswith(os.sep):
        vault_path_abs += os.sep

    pattern = vault_path_abs + "%"
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Enable foreign keys just in case, though we handle deletions manually to be safe with virtual tables
    cursor.execute("PRAGMA foreign_keys = ON")
    
    try:
        # 1. Count what we are about to delete for the summary
        cursor.execute("SELECT COUNT(*) FROM files WHERE path LIKE ? OR path = ?", (pattern, vault_path_abs[:-1]))
        file_count = cursor.fetchone()[0]
        
        if file_count == 0:
            logger.info(f"No records found for vault: {vault_path_abs}")
            conn.close()
            return

        logger.info(f"Found {file_count} files in vault {vault_path_abs}. Starting deletion...")

        # 2. Delete from vec_chunks (Virtual table, must be deleted first or explicitly)
        # We find all chunk_ids associated with files in this vault
        cursor.execute("""
            DELETE FROM vec_chunks 
            WHERE chunk_id IN (
                SELECT chunk_id 
                FROM file_chunks 
                WHERE file_id IN (
                    SELECT id FROM files WHERE path LIKE ? OR path = ?
                )
            )
        """, (pattern, vault_path_abs[:-1]))
        vec_deleted = cursor.rowcount
        logger.info(f"Deleted {vec_deleted} vector records.")

        # 3. Delete from file_chunks (Cascade would handle this if configured, but let's be explicit)
        cursor.execute("""
            DELETE FROM file_chunks 
            WHERE file_id IN (
                SELECT id FROM files WHERE path LIKE ? OR path = ?
            )
        """, (pattern, vault_path_abs[:-1]))
        logger.info(f"Deleted file chunk records.")

        # 4. Delete from dismissed_links
        cursor.execute("""
            DELETE FROM dismissed_links 
            WHERE file1_path LIKE ? OR file1_path = ? 
               OR file2_path LIKE ? OR file2_path = ?
        """, (pattern, vault_path_abs[:-1], pattern, vault_path_abs[:-1]))
        links_deleted = cursor.rowcount
        logger.info(f"Deleted {links_deleted} dismissed link records.")

        # 5. Finally delete from files
        cursor.execute("DELETE FROM files WHERE path LIKE ? OR path = ?", (pattern, vault_path_abs[:-1]))
        logger.info(f"Deleted {file_count} file records.")

        conn.commit()
        logger.info("Successfully deleted all records for the vault.")
        
    except Exception as e:
        conn.rollback()
        logger.error(f"An error occurred during deletion: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Delete all records and vectors for a specific vault from the database.")
    parser.add_argument("vault_path", help="The absolute or relative path to the vault directory.")
    
    args = parser.parse_args()
    
    # Ask for confirmation if it's not a script running in a pipe
    if sys.stdin.isatty():
        confirm = input(f"Are you sure you want to delete all records for vault '{args.vault_path}'? (y/N): ")
        if confirm.lower() != 'y':
            print("Operation cancelled.")
            sys.exit(0)
            
    delete_vault(args.vault_path)
