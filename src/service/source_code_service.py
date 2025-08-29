from src.core.config import Config
from src.entity.source_code_entity import SourceCodeEntity
from src.model import SourceCodeModel
from src.utils import crawl_local_files


class SourceCodeService:
    def __init__(self, config: Config, source_code_model: SourceCodeModel):
        self.config = config
        self.source_code_model = source_code_model
        
    def has_cache(self) -> bool:
        return self.source_code_model.has_data()
    
    def save_cache(self, source_code_entities: list[SourceCodeEntity]) -> None:
        self.source_code_model.batch_insert(source_code_entities)
    
    def crawl_repo(self, target_dir: str, include_patterns: list[str] = None, exclude_patterns: list[str] = None) -> list[SourceCodeEntity]:
        if not target_dir:
            raise ValueError("Target directory is not specified.")
        
        print(f"Extracting source code from {target_dir}")
        
        # Use provided patterns (should always be provided from main.py now)
        final_include = set(include_patterns) if include_patterns else set()
        final_exclude = set(exclude_patterns) if exclude_patterns else set()
        
        source_code_entities = crawl_local_files(
            directory=target_dir,
            exclude_patterns=final_exclude,
            include_patterns=final_include,
            use_relative_paths=True,
            is_compress=True
        )
        
        if not source_code_entities:
            raise ValueError(f"No source code files found in directory: {target_dir}")
        
        return source_code_entities
