from src.core.config import Config
from src.model import SourceCodeModel
from src.utils import crawl_local_files


class SourceCodeService:
    def __init__(self, config: Config, source_code_model: SourceCodeModel):
        self.config = config
        self.source_code_model = source_code_model
    
    async def ensure_source_code(self, target_dir: str) -> bool:
        if self.source_code_model.has_data():
            print("Use cached source code")
            return True
        
        if not target_dir:
            print("Error: target_dir is required when no cached source code exists")
            return False
        
        print(f"Extracting source code from {target_dir}")
        
        source_code_entities = crawl_local_files(
            directory=target_dir,
            exclude_patterns=self.config.default_exclude_patterns or set(),
            include_patterns=self.config.default_include_patterns or set(),
            use_relative_paths=True,
            is_compress=True
        )
        
        if not source_code_entities:
            print(f"Error: No files found in {target_dir}")
            return False
        
        self.source_code_model.batch_insert(source_code_entities)
        print(f"Fetch {len(source_code_entities)} files")
        return True
