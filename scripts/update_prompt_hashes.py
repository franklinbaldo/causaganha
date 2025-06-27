import hashlib
import os
import re
import sys
from pathlib import Path

def calculate_file_hash(filepath: Path) -> str:
    """Calculates the SHA1 hash of a file's content."""
    hasher = hashlib.sha1()
    with open(filepath, 'rb') as f:
        while chunk := f.read(8192):
            hasher.update(chunk)
    return hasher.hexdigest()

def update_prompt_hashes(prompts_dir: Path):
    """
    Iterates through prompt files, calculates their hash, and renames them
    if the hash is not already part of the filename.
    """
    if not prompts_dir.is_dir():
        print(f"Error: Prompts directory not found at {prompts_dir}", file=sys.stderr)
        sys.exit(1)

    renamed_files = []
    for filepath in prompts_dir.iterdir():
        if filepath.is_file() and filepath.suffix == '.txt':
            # Check if the file already has a hash in its name
            # Pattern: <name>-<hash>.txt
            match = re.match(r"^(.*?)-([0-9a-fA-F]{8,40})\.txt$", filepath.name)
            
            if match:
                # File already has a hash, verify it
                base_name_without_hash = match.group(1)
                existing_hash = match.group(2)
                current_content_hash = calculate_file_hash(filepath)
                
                if existing_hash != current_content_hash:
                    print(f"Warning: Content of {filepath.name} has changed but hash in filename does not match. Renaming to reflect new content.", file=sys.stderr)
                    # Proceed to rename with new hash
                else:
                    # Hash matches, no action needed
                    continue
            
            # If no hash or hash mismatch, calculate and rename
            base_name = filepath.stem # Name without .txt
            content_hash = calculate_file_hash(filepath)
            short_hash = content_hash[:8] # Use first 8 chars for brevity

            new_name = f"{base_name}-{short_hash}{filepath.suffix}"
            new_filepath = filepath.with_name(new_name)

            if filepath != new_filepath:
                print(f"Renaming '{filepath.name}' to '{new_filepath.name}'")
                filepath.rename(new_filepath)
                renamed_files.append(new_filepath)
    
    if renamed_files:
        print("\nPrompt files were renamed. Please update your config.toml to reflect the new filenames.", file=sys.stderr)
        sys.exit(1) # Exit with error to signal that config needs update
    else:
        print("No prompt files needed renaming.")

if __name__ == "__main__":
    # Assuming the script is run from the project root or from .git/hooks
    # Adjust prompts_dir_path as necessary
    prompts_dir_path = Path("prompts")
    update_prompt_hashes(prompts_dir_path)
