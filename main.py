import argparse
import asyncio

from src.core.config import Config
from pipeline import Pipeline

# Default file patterns
DEFAULT_INCLUDE_PATTERNS = ["*.cs"]
DEFAULT_EXCLUDE_PATTERNS = [
    "*.md", 
    "dockerfile",
    "*test*",
    "*Test*",
    "*test*/*",
    "*Test*/*",
    "*/test*/*",
    "*/Test*/*",
    "tests/*",
    "test/*",
    "__tests__/*",
]

async def main():
    config = Config()
    
    parser = argparse.ArgumentParser(
        description="Generate a API feature documentation for a repository."
    )
    
    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument("--dir", help="Path to local directory.")
    parser.add_argument(
        "-i", "--include", 
        nargs="+", 
        help="Include file patterns (e.g. '*.py' '*.js'). Defaults to common code files if not specified."
    )
    parser.add_argument(
        "-e", "--exclude", 
        nargs="+", 
        help="Exclude file patterns (e.g. 'tests/*' 'docs/*'). Defaults to test/build directories if not specified."
    )
    parser.add_argument(
        "-l", "--lang", 
        default="zh-TW", 
        help="Language for the generated tutorial (default: zh-TW)"
    )
    parser.add_argument(
        "--run-id", 
        help="Reuse existing artifacts directory with specified run ID (e.g., '20250812T032052Z')"
    )
    parser.add_argument(
        "--target-func", 
        nargs="*", 
        help="Target function to analyze (e.g., 'main', 'run'). If specified, only files related to this function will be processed."
    )
    
    args = parser.parse_args()

    # Use provided patterns or defaults
    include_patterns = args.include if args.include else DEFAULT_INCLUDE_PATTERNS
    exclude_patterns = args.exclude if args.exclude else DEFAULT_EXCLUDE_PATTERNS
    
    # Convert empty list to None for consistency
    target_func = args.target_func if args.target_func else None
    
    pipeline = Pipeline(config)
    await pipeline.run(
        target_dir=args.dir,
        lang=args.lang,
        run_id=args.run_id,
        appoint_entries=target_func,
        include_patterns=include_patterns,
        exclude_patterns=exclude_patterns
    )

if __name__ == "__main__":
    asyncio.run(main())
