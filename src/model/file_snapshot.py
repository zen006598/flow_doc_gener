import json
import os
from typing import List
from src.model.file_info import FileInfo


class FileSnapshot:
    """Class to handle file snapshots for the application"""
    
    def __init__(self, run_id: str, target_dir: str = "src/cache"):
        self.run_id = run_id 
        self.cache_dir = os.path.join(target_dir, self.run_id)
    
    def save_snapshot(self, files: List[FileInfo]):
        """Save the file snapshot to JSON format"""
        json_output = {
            "dir_structure": {file.file_id: file.path for file in files},
            "contents": {file.file_id: self.compress_content(file.content) for file in files}
        }
        # Save to src/cache/run_id/sources.json
        os.makedirs(self.cache_dir, exist_ok=True)
        sources_file = os.path.join(self.cache_dir, "sources.json")
        with open(sources_file, "w", encoding="utf-8") as f:
            json.dump(json_output, f, indent=2, ensure_ascii=False)
            
    def compress_content(self, content):
        lines = content.split('\n')
        stripped_lines = [line.strip() for line in lines if line.strip()]  # Remove empty lines
        
        # Merge single character lines with next line
        compressed_lines = []
        i = 0
        while i < len(stripped_lines):
            current_line = stripped_lines[i]
            if len(current_line) == 1 and i + 1 < len(stripped_lines):
                # Merge single character with next line
                next_line = stripped_lines[i + 1]
                compressed_lines.append(current_line + ' ' + next_line)
                i += 2
            else:
                compressed_lines.append(current_line)
                i += 1
        
        return '\n'.join(compressed_lines)
    
    def snapshot_exists(self) -> bool:
        """Check if snapshot already exists and has files"""
        sources_file = os.path.join(self.cache_dir, "sources.json")
        if os.path.exists(sources_file):
            try:
                with open(sources_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                # Check if snapshot has content
                return bool(data.get("contents", {}))
            except (json.JSONDecodeError, IOError):
                return False
        return False
    