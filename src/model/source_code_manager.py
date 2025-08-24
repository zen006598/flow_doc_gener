from typing import List
from src.model.file_info import FileInfo
from src.model.snapshot_manager import SnapshotManager
from src.model.feature_analysis_models import SourceCodeFile


class SourceCodeManager:
    """Class to handle file snapshots for the application"""
    
    def __init__(self, snapshot_manager: SnapshotManager, file_name: str):
        self.snapshot_manager = snapshot_manager
        self.file_name = file_name
    
    def save_snapshot(self, files: List[FileInfo], run_id: str):
        """Save the file snapshot to JSON format"""
        json_output = {
            "dir_structure": {file.file_id: file.path for file in files},
            "contents": {file.file_id: self.compress_content(file.content) for file in files}
        }
        self.snapshot_manager.save_file(run_id, self.file_name, json_output)
            
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
                compressed_lines.append(current_line + '' + next_line)
                i += 2
            else:
                compressed_lines.append(current_line)
                i += 1
        
        return '\n'.join(compressed_lines)
    
    def is_snapshot_exists(self, run_id: str) -> bool:
        """Check if snapshot already exists and has files"""
        if not self.snapshot_manager.file_exists(run_id, self.file_name):
            return False
        
        data = self.snapshot_manager.load_file(run_id, self.file_name)
        if data is None:
            return False
        
        # Check if snapshot has content
        return bool(data.get("contents", {}))
    
    def get_source_files_by_ids(self, run_id: str, file_ids: List[int]) -> List[SourceCodeFile]:
        """
        Get source code files by file IDs
        
        Args:
            run_id: The run ID
            file_ids: List of file IDs to retrieve
            
        Returns:
            List of SourceCodeFile objects with file_id, path, and content
        """
        if not self.snapshot_manager.file_exists(run_id, self.file_name):
            return []
        
        data = self.snapshot_manager.load_file(run_id, self.file_name)
        if not data:
            return []
        
        dir_structure = data.get("dir_structure", {})
        contents = data.get("contents", {})
        source_files = []
        
        for file_id in file_ids:
            file_id_str = str(file_id)
            
            # Get path from dir_structure
            path = dir_structure.get(file_id_str, "")
            
            # Get content from contents
            content = contents.get(file_id_str, "")
            
            if path and content:  # Only add if both path and content exist
                source_files.append(SourceCodeFile(
                    file_id=file_id,
                    path=path,
                    content=content
                ))
        
        return source_files
