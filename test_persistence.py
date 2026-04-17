import os
import shutil
from backend.pipeline import scan_directory

def test_persistence():
    # Setup test directories
    root = "scratch/test_persistence"
    if os.path.exists(root):
        shutil.rmtree(root)
    os.makedirs(f"{root}/vault_a")
    os.makedirs(f"{root}/vault_b")
    
    with open(f"{root}/vault_a/file_a.md", "w") as f:
        f.write("# File A")
    with open(f"{root}/vault_b/file_b.md", "w") as f:
        f.write("# File B")
    
    # Mock existing files in DB (Full absolute paths)
    vault_a_abs = os.path.abspath(f"{root}/vault_a")
    vault_b_abs = os.path.abspath(f"{root}/vault_b")
    file_a_path = os.path.join(vault_a_abs, "file_a.md")
    file_b_path = os.path.join(vault_b_abs, "file_b.md")
    
    existing_files = {
        file_a_path: "hash_a",
        file_b_path: "hash_b"
    }
    
    print("\n--- TEST: Scan Vault A ---")
    # Simulation: Scan only Vault A. 
    # Before the fix, File B would be in 'deleted'.
    # After the fix, File B should BE PRESERVED (not in deleted).
    new_or_mod, deleted, count = scan_directory(vault_a_abs, existing_files)
    
    print(f"Scanning: {vault_a_abs}")
    print(f"Found in scan: {count}")
    print(f"Deleted identified: {deleted}")
    
    if file_b_path in deleted:
        print("❌ FAILURE: File B from a DIFFERENT vault was marked as deleted!")
    else:
        print("✅ SUCCESS: File B from different vault was preserved.")

    print("\n--- TEST: Deletion within Vault A ---")
    # Simulation: Remove File A from disk, then scan Vault A.
    # File A should be in 'deleted'.
    os.remove(file_a_path)
    new_or_mod, deleted, count = scan_directory(vault_a_abs, existing_files)
    print(f"Deleted identified: {deleted}")
    
    if file_a_path in deleted:
        print("✅ SUCCESS: File A (actual deletion) was correctly identified.")
    else:
        print("❌ FAILURE: File A was NOT identified as deleted.")

if __name__ == "__main__":
    test_persistence()
