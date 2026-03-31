import os
import re
import sys
import shutil

# Case-sensitive mappings
MAPPINGS = {
    r'FinanzBro': 'FinanceBro',
    r'finanzbro': 'financebro',
    r'FINANZBRO': 'FINANCEBRO'
}

EXCLUDE_DIRS = {'.git', 'venv', '__pycache__', '.pytest_cache', 'artifacts', 'docs/screenshots'}
EXCLUDE_EXTS = {'.png', '.jpg', '.jpeg', '.db', '.pdf', '.db-shm', '.db-wal', '.pyc'}

def main():
    base_dir = r"c:\Users\Jonas\OneDrive\Dokumente\FinanzBro"
    modified_files = []
    
    # 1. String Replacement pass
    for root, dirs, files in os.walk(base_dir):
        # Exclude directories
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        
        for file in files:
            file_path = os.path.join(root, file)
            ext = os.path.splitext(file)[1].lower()
            
            # Skip binary/unsupported extensions
            if ext in EXCLUDE_EXTS or file.endswith('rename_script.py'):
                continue
                
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                original_content = content
                for search, replace in MAPPINGS.items():
                    content = re.sub(search, replace, content)
                    
                if content != original_content:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    modified_files.append(file_path)
            except Exception as e:
                # If we hit an encoding error (e.g. unknown binary not in EXCLUDE), skip gently
                print(f"Skipping {file_path}: {e}")

    # 2. File rename pass (specifically the cache/ DB files)
    cache_dir = os.path.join(base_dir, 'cache')
    if os.path.exists(cache_dir):
        for f in os.listdir(cache_dir):
            if 'finanzbro' in f.lower():
                old_path = os.path.join(cache_dir, f)
                new_name = f.replace('finanzbro', 'financebro').replace('FinanzBro', 'FinanceBro')
                new_path = os.path.join(cache_dir, new_name)
                try:
                    os.rename(old_path, new_path)
                    print(f"Renamed file: {old_path} -> {new_path}")
                except Exception as e:
                    print(f"WARNING: Could not rename {old_path} (Perhaps a Server lock is active?): {e}")

    print(f"\nSuccessfully modified {len(modified_files)} files.")
    for m in modified_files[:20]:
        print(f" - {m}")
    if len(modified_files) > 20:
        print(f"   ... and {len(modified_files)-20} more.")

if __name__ == "__main__":
    main()
