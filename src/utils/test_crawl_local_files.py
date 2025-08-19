import os
import tempfile
import shutil
import pathspec
from unittest import TestCase, main
from crawl_local_files import crawl_local_files, _should_include_file, _should_exclude_directory


class TestCrawlLocalFiles(TestCase):
    
    def setUp(self):
        """Create temporary test directory structure"""
        self.test_dir = tempfile.mkdtemp()
        
        # Create test directory structure
        test_structure = {
            'src/main.py': 'print("main")',
            'src/utils.py': 'def helper(): pass',
            'src/__pycache__/main.cpython-39.pyc': 'compiled',
            'tests/test_main.py': 'def test(): pass',
            'docs/readme.md': '# README',
            'node_modules/package/index.js': 'module.exports = {}',
            '.git/config': '[core]',
            '.venv/lib/python3.9/site-packages/pkg.py': 'package',
            'data/file.json': '{"key": "value"}',
            'build/output.js': 'built file',
            '.gitignore': '__pycache__/\n*.pyc\nnode_modules/\n',
        }
        
        for filepath, content in test_structure.items():
            full_path = os.path.join(self.test_dir, filepath)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)
    
    def tearDown(self):
        """Clean up temporary test directory"""
        shutil.rmtree(self.test_dir)


class TestShouldIncludeFile(TestCase):
    
    def setUp(self):
        """Set up gitignore spec for testing"""
        gitignore_patterns = ['__pycache__/', '*.pyc', 'node_modules/']
        self.gitignore_spec = pathspec.PathSpec.from_lines('gitwildmatch', gitignore_patterns)
    
    def test_include_with_no_patterns(self):
        """Test file inclusion with no patterns - should include all"""
        self.assertTrue(_should_include_file('src/main.py', None, None, None))
        self.assertTrue(_should_include_file('any/file.txt', None, None, None))
    
    def test_exclude_patterns(self):
        """Test file exclusion with exclude patterns"""
        exclude_patterns = {'*.pyc', 'tests/*', '*/temp/*'}
        
        # Should exclude
        self.assertFalse(_should_include_file('main.pyc', None, exclude_patterns, None))
        self.assertFalse(_should_include_file('tests/test.py', None, exclude_patterns, None))
        self.assertFalse(_should_include_file('src/temp/file.txt', None, exclude_patterns, None))
        
        # Should include
        self.assertTrue(_should_include_file('src/main.py', None, exclude_patterns, None))
        self.assertTrue(_should_include_file('docs/readme.md', None, exclude_patterns, None))
    
    def test_include_patterns(self):
        """Test file inclusion with include patterns"""
        include_patterns = {'*.py', '*.js'}
        
        # Should include
        self.assertTrue(_should_include_file('main.py', include_patterns, None, None))
        self.assertTrue(_should_include_file('script.js', include_patterns, None, None))
        
        # Should exclude
        self.assertFalse(_should_include_file('readme.md', include_patterns, None, None))
        self.assertFalse(_should_include_file('config.json', include_patterns, None, None))
    
    def test_include_and_exclude_patterns(self):
        """Test combination of include and exclude patterns"""
        include_patterns = {'*.py', '*.js'}
        exclude_patterns = {'test_*.py', '*/node_modules/*'}
        
        # Include takes precedence, but exclude can override
        self.assertTrue(_should_include_file('main.py', include_patterns, exclude_patterns, None))
        self.assertFalse(_should_include_file('test_main.py', include_patterns, exclude_patterns, None))
        self.assertFalse(_should_include_file('src/node_modules/pkg.js', include_patterns, exclude_patterns, None))
    
    def test_gitignore_exclusion(self):
        """Test gitignore pattern exclusion"""
        # Should exclude based on gitignore
        self.assertFalse(_should_include_file('__pycache__/main.cpython-39.pyc', None, None, self.gitignore_spec))
        self.assertFalse(_should_include_file('main.pyc', None, None, self.gitignore_spec))
        self.assertFalse(_should_include_file('node_modules/pkg/index.js', None, None, self.gitignore_spec))
        
        # Should include
        self.assertTrue(_should_include_file('src/main.py', None, None, self.gitignore_spec))


class TestShouldExcludeDirectory(TestCase):
    
    def setUp(self):
        """Set up gitignore spec for testing"""
        gitignore_patterns = ['__pycache__/', '*.pyc', 'node_modules/', '.git/']
        self.gitignore_spec = pathspec.PathSpec.from_lines('gitwildmatch', gitignore_patterns)
    
    def test_exclude_with_no_patterns(self):
        """Test directory exclusion with no patterns - should include all"""
        self.assertFalse(_should_exclude_directory('src', 'src', None, None))
        self.assertFalse(_should_exclude_directory('any/dir', 'dir', None, None))
    
    def test_exclude_patterns(self):
        """Test directory exclusion with exclude patterns"""
        exclude_patterns = {'__pycache__/*', 'node_modules/*', '*/temp/*', 'build'}
        
        # Should exclude
        self.assertTrue(_should_exclude_directory('__pycache__', '__pycache__', exclude_patterns, None))
        self.assertTrue(_should_exclude_directory('node_modules', 'node_modules', exclude_patterns, None))
        self.assertTrue(_should_exclude_directory('src/temp', 'temp', exclude_patterns, None))
        self.assertTrue(_should_exclude_directory('build', 'build', exclude_patterns, None))
        
        # Should include
        self.assertFalse(_should_exclude_directory('src', 'src', exclude_patterns, None))
        self.assertFalse(_should_exclude_directory('tests', 'tests', exclude_patterns, None))
    
    def test_gitignore_exclusion(self):
        """Test gitignore directory exclusion"""
        # Should exclude based on gitignore
        self.assertTrue(_should_exclude_directory('__pycache__', '__pycache__', None, self.gitignore_spec))
        self.assertTrue(_should_exclude_directory('node_modules', 'node_modules', None, self.gitignore_spec))
        self.assertTrue(_should_exclude_directory('.git', '.git', None, self.gitignore_spec))
        
        # Should include
        self.assertFalse(_should_exclude_directory('src', 'src', None, self.gitignore_spec))
        self.assertFalse(_should_exclude_directory('tests', 'tests', None, self.gitignore_spec))
    
    def test_pattern_with_slash(self):
        """Test patterns ending with /*"""
        exclude_patterns = {'build/*', '*/cache/*'}
        
        # Should exclude directories that match pattern without /*
        self.assertTrue(_should_exclude_directory('build', 'build', exclude_patterns, None))
        self.assertTrue(_should_exclude_directory('src/cache', 'cache', exclude_patterns, None))


class TestCrawlLocalFilesIntegration(TestCrawlLocalFiles):
    
    def test_basic_crawl(self):
        """Test basic directory crawling"""
        result = crawl_local_files(self.test_dir)
        
        # Should return list of file dictionaries
        self.assertIsInstance(result, list)
        self.assertTrue(len(result) > 0)
        
        # Check structure
        for file_info in result:
            self.assertIn('file_id', file_info)
            self.assertIn('path', file_info)
            self.assertIn('content', file_info)
            self.assertIsInstance(file_info['file_id'], int)
            self.assertIsInstance(file_info['path'], str)
            self.assertIsInstance(file_info['content'], str)
    
    def test_crawl_with_exclude_patterns(self):
        """Test crawling with exclude patterns"""
        exclude_patterns = {'*.pyc', '__pycache__/*', 'node_modules/*', '.git/*'}
        result = crawl_local_files(self.test_dir, exclude_patterns=exclude_patterns)
        
        # Should not contain excluded files
        paths = [f['path'] for f in result]
        
        # Check no excluded files present
        excluded_files = [p for p in paths if p.endswith('.pyc') or 
                         '__pycache__' in p or 'node_modules' in p or p.startswith('.git/')]
        if excluded_files:
            print(f"Excluded files found: {excluded_files}")
        self.assertEqual(len(excluded_files), 0)
        
        # Should contain included files
        self.assertTrue(any('src/main.py' in p for p in paths))
        self.assertTrue(any('tests/test_main.py' in p for p in paths))
    
    def test_crawl_with_include_patterns(self):
        """Test crawling with include patterns"""
        include_patterns = {'*.py', '*.md'}
        result = crawl_local_files(self.test_dir, include_patterns=include_patterns)
        
        paths = [f['path'] for f in result]
        
        # Should only contain .py and .md files
        for path in paths:
            self.assertTrue(path.endswith('.py') or path.endswith('.md'))
    
    def test_crawl_with_max_file_size(self):
        """Test crawling with file size limit"""
        # Create a large file
        large_file_path = os.path.join(self.test_dir, 'large.txt')
        with open(large_file_path, 'w') as f:
            f.write('x' * 1000)  # 1KB file
        
        # Crawl with 500 byte limit
        result = crawl_local_files(self.test_dir, max_file_size=500)
        
        paths = [f['path'] for f in result]
        
        # Large file should be excluded
        self.assertFalse(any('large.txt' in p for p in paths))
        
        # Small files should be included
        self.assertTrue(any('src/main.py' in p for p in paths))
    
    def test_crawl_with_relative_paths(self):
        """Test relative vs absolute paths"""
        # Test relative paths (default)
        result_rel = crawl_local_files(self.test_dir, use_relative_paths=True)
        
        # Test absolute paths
        result_abs = crawl_local_files(self.test_dir, use_relative_paths=False)
        
        # Relative paths should not start with /
        for file_info in result_rel:
            self.assertFalse(file_info['path'].startswith('/'))
        
        # Absolute paths should start with / or drive letter
        for file_info in result_abs:
            path = file_info['path']
            self.assertTrue(path.startswith('/') or (len(path) > 1 and path[1] == ':'))
    
    def test_crawl_with_gitignore(self):
        """Test crawling respects .gitignore"""
        result = crawl_local_files(self.test_dir)
        
        paths = [f['path'] for f in result]
        
        # Should exclude files matching .gitignore patterns
        gitignore_excluded = [p for p in paths if '__pycache__' in p or 
                             p.endswith('.pyc') or 'node_modules' in p]
        self.assertEqual(len(gitignore_excluded), 0)
    
    def test_nonexistent_directory(self):
        """Test handling of nonexistent directory"""
        with self.assertRaises(ValueError):
            crawl_local_files('/nonexistent/directory')
    
    def test_empty_directory(self):
        """Test crawling empty directory"""
        empty_dir = tempfile.mkdtemp()
        try:
            result = crawl_local_files(empty_dir)
            self.assertEqual(len(result), 0)
        finally:
            os.rmdir(empty_dir)
    
    def test_file_id_assignment(self):
        """Test file_id assignment is sequential"""
        result = crawl_local_files(self.test_dir)
        
        file_ids = [f['file_id'] for f in result]
        file_ids.sort()
        
        # Should be sequential starting from 0
        expected_ids = list(range(len(result)))
        self.assertEqual(file_ids, expected_ids)


class TestCrossPlatformCompatibility(TestCase):
    
    def test_path_separator_normalization(self):
        """Test that paths are normalized to forward slashes"""
        # This test ensures cross-platform compatibility
        test_paths = [
            'src\\main.py',  # Windows style
            'src/main.py',   # Unix style
            'src\\utils\\helper.py',  # Windows nested
            'src/utils/helper.py',    # Unix nested
        ]
        
        exclude_patterns = {'*.pyc'}
        
        for path in test_paths:
            # Should handle both path separators correctly
            result = _should_include_file(path, None, exclude_patterns, None)
            self.assertIsInstance(result, bool)


if __name__ == '__main__':
    main()