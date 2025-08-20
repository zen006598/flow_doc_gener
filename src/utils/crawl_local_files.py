import os
import fnmatch
from typing import List
import pathspec
from src.model.file_info import FileInfo

def _should_include_file(filepath, include_patterns, exclude_patterns, gitignore_spec):
    """
    Determine if a file should be included based on include/exclude patterns and gitignore.
    
    Args:
        filepath (str): Relative path of the file
        include_patterns (set): File patterns to include
        exclude_patterns (set): File patterns to exclude  
        gitignore_spec: Parsed gitignore specification
        
    Returns:
        bool: True if file should be included, False otherwise
    """
    # Check exclusion first (gitignore and exclude_patterns)
    if gitignore_spec and gitignore_spec.match_file(filepath):
        return False
        
    if exclude_patterns:
        for pattern in exclude_patterns:
            if fnmatch.fnmatch(filepath, pattern):
                return False
    
    # Check inclusion
    if include_patterns:
        for pattern in include_patterns:
            if fnmatch.fnmatch(filepath, pattern):
                return True
        return False  # If include patterns specified but none match
    else:
        return True  # Include by default if no include patterns


def _should_exclude_directory(dirpath, dirname, exclude_patterns, gitignore_spec):
    """
    Determine if a directory should be excluded from traversal.
    
    Args:
        dirpath (str): Relative path of the directory
        dirname (str): Directory name only
        exclude_patterns (set): Directory patterns to exclude
        gitignore_spec: Parsed gitignore specification
        
    Returns:
        bool: True if directory should be excluded, False otherwise
    """
    if gitignore_spec:
        # Try both dirpath and dirpath with trailing slash for gitignore directory patterns
        if gitignore_spec.match_file(dirpath) or gitignore_spec.match_file(dirpath + '/'):
            return True
        
    if exclude_patterns:
        for pattern in exclude_patterns:
            # Always try both dirpath and dirname for comprehensive matching
            if fnmatch.fnmatch(dirpath, pattern) or fnmatch.fnmatch(dirname, pattern):
                return True
            # Also check if dirpath matches pattern without trailing /*
            if pattern.endswith('/*'):
                pattern_without_slash = pattern[:-2]
                if fnmatch.fnmatch(dirpath, pattern_without_slash) or fnmatch.fnmatch(dirname, pattern_without_slash):
                    return True
    
    return False


def crawl_local_files(
    directory,
    include_patterns=None,
    exclude_patterns=None,
    max_file_size=None,
    use_relative_paths=True,
) -> List[FileInfo]:
    """
    Crawl files in a local directory with similar interface as crawl_github_files.
    Args:
        directory (str): Path to local directory
        include_patterns (set): File patterns to include (e.g. {"*.py", "*.js"})
        exclude_patterns (set): File patterns to exclude (e.g. {"tests/*"})
        max_file_size (int): Maximum file size in bytes
        use_relative_paths (bool): Whether to use paths relative to directory

    Returns:
        List[FileInfo]: List of FileInfo objects
    """
    if not os.path.isdir(directory):
        raise ValueError(f"Directory does not exist: {directory}")

    # Normalize directory path for cross-platform compatibility
    directory = os.path.abspath(directory)
    
    result_files = []
    file_id = 0

    # --- Load .gitignore ---
    gitignore_path = os.path.join(directory, ".gitignore")
    gitignore_spec = None
    if os.path.exists(gitignore_path):
        try:
            with open(gitignore_path, "r", encoding="utf-8-sig") as f:
                gitignore_patterns = f.readlines()
            gitignore_spec = pathspec.PathSpec.from_lines("gitwildmatch", gitignore_patterns)
        except Exception:
            pass

    all_files = []
    for root, dirs, files in os.walk(directory):
        # Filter directories using extracted helper function
        excluded_dirs = set()
        for d in dirs:
            dirpath_abs = os.path.join(root, d)
            # Use forward slashes for cross-platform gitignore compatibility
            dirpath_rel = os.path.relpath(dirpath_abs, directory).replace(os.sep, '/')
            
            if _should_exclude_directory(dirpath_rel, d, exclude_patterns, gitignore_spec):
                excluded_dirs.add(d)

        for d in dirs.copy():
            if d in excluded_dirs:
                dirs.remove(d)

        for filename in files:
            filepath = os.path.join(root, filename)
            all_files.append(filepath)


    for filepath in all_files:
        # Use forward slashes for cross-platform compatibility
        if use_relative_paths:
            relpath = os.path.relpath(filepath, directory).replace(os.sep, '/')
        else:
            relpath = filepath


        # Use extracted helper function for include/exclude logic
        if not _should_include_file(relpath, include_patterns, exclude_patterns, gitignore_spec):
            continue

        if max_file_size and os.path.getsize(filepath) > max_file_size:
            continue

        # --- File is being processed ---        
        try:
            with open(filepath, "r", encoding="utf-8-sig") as f:
                content = f.read()
            
            file_info = FileInfo(
                file_id=file_id,
                path=relpath,
                content=content
            )
            result_files.append(file_info)
            file_id += 1
        except Exception:
            pass

    return result_files


if __name__ == "__main__":
    print("--- Crawling parent directory ('..') ---")
    files_data = crawl_local_files(
        ".",
        exclude_patterns={
            "*.pyc", 
            "__pycache__/*",
            ".venv/*", 
            ".git/*",
            "docs/*",
            "output/*",
            "node_modules/*",
            "*/node_modules/*",
            "*/.venv/*",
            "*/.git/*",
            "*/build/*",
            "*/dist/*",
            "*/data/*",
        },
    )
    print(f"Found {len(files_data)} files:")
    for file in files_data:
        print(f" - {file.path} (ID: {file.file_id})")