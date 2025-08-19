from dataclasses import dataclass


@dataclass
class FileInfo:
    """Data Transfer Object for individual file information"""
    file_id: int
    path: str
    content: str
    
    def __post_init__(self):
        """Validate file info after initialization"""
        if not isinstance(self.file_id, int):
            raise TypeError("file_id must be an integer")
        if not isinstance(self.path, str):
            raise TypeError("path must be a string")
        if not isinstance(self.content, str):
            raise TypeError("content must be a string")
    
    def to_dict(self) -> dict:
        """Convert to dictionary for backward compatibility"""
        return {
            "file_id": self.file_id,
            "path": self.path,
            "content": self.content
        }