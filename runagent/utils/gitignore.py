"""
Gitignore parser utility for filtering files during agent upload.
Respects .gitignore rules similar to Git's behavior.
"""
import os
import fnmatch
from pathlib import Path
from typing import List, Set


class GitignoreFilter:
    """Filter files based on .gitignore rules"""
    
    def __init__(self, root_path: Path):
        self.root_path = root_path
        self.ignore_patterns = self._load_gitignore_patterns()
        
        # Add common Python patterns if no .gitignore exists
        if not (root_path / '.gitignore').exists():
            self.ignore_patterns.extend([
                '__pycache__/',
                '*.pyc',
                '*.pyo',
                '*.pyd',
                '.Python',
                'build/',
                'develop-eggs/',
                'dist/',
                'downloads/',
                'eggs/',
                '.eggs/',
                'lib/',
                'lib64/',
                'parts/',
                'sdist/',
                'var/',
                'wheels/',
                '*.egg-info/',
                '.installed.cfg',
                '*.egg',
                '.venv/',
                'venv/',
                'env/',
                '.DS_Store',
                'Thumbs.db'
            ])
    
    def _load_gitignore_patterns(self) -> List[str]:
        """Load patterns from .gitignore file"""
        gitignore_path = self.root_path / '.gitignore'
        patterns = []
        
        if gitignore_path.exists():
            try:
                with gitignore_path.open('r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        # Skip empty lines and comments
                        if line and not line.startswith('#'):
                            patterns.append(line)
            except Exception:
                # If we can't read .gitignore, continue without it
                pass
        
        return patterns
    
    def _matches_pattern(self, file_path: str, pattern: str) -> bool:
        """Check if file path matches a gitignore pattern"""
        # Convert to forward slashes for consistent matching
        normalized_path = file_path.replace('\\', '/')
        
        # Handle directory patterns (ending with /)
        if pattern.endswith('/'):
            pattern = pattern[:-1]
            # Directory patterns match directories and files within them
            return fnmatch.fnmatch(normalized_path, pattern) or fnmatch.fnmatch(normalized_path, f"{pattern}/*")
        
        # Handle negation patterns (starting with !)
        if pattern.startswith('!'):
            pattern = pattern[1:]
            return fnmatch.fnmatch(normalized_path, pattern)
        
        # Regular pattern matching
        return fnmatch.fnmatch(normalized_path, pattern)
    
    def should_ignore(self, file_path: str) -> bool:
        """Check if a file should be ignored based on .gitignore rules"""
        # Convert to forward slashes for consistent matching
        normalized_path = file_path.replace('\\', '/')
        
        # Track negation patterns separately
        negations = []
        regular_patterns = []
        
        for pattern in self.ignore_patterns:
            if pattern.startswith('!'):
                negations.append(pattern[1:])
            else:
                regular_patterns.append(pattern)
        
        # Check if file matches any regular pattern
        matches_ignore = any(self._matches_pattern(normalized_path, pattern) for pattern in regular_patterns)
        
        # Check if file matches any negation pattern (overrides ignore)
        matches_negation = any(self._matches_pattern(normalized_path, pattern) for pattern in negations)
        
        # File is ignored if it matches ignore pattern but not negation
        return matches_ignore and not matches_negation
    
    def get_filtered_files(self) -> List[str]:
        """Get list of all files in the directory, respecting .gitignore"""
        filtered_files = []
        
        for root, dirs, files in os.walk(self.root_path):
            # Convert to relative path
            rel_root = os.path.relpath(root, self.root_path)
            if rel_root == '.':
                rel_root = ''
            
            # Filter directories based on .gitignore
            dirs_to_remove = []
            for dir_name in dirs:
                dir_path = os.path.join(rel_root, dir_name) if rel_root else dir_name
                if self.should_ignore(dir_path + '/'):
                    dirs_to_remove.append(dir_name)
            
            # Remove ignored directories from dirs list to prevent os.walk from entering them
            for dir_name in dirs_to_remove:
                dirs.remove(dir_name)
            
            # Filter files based on .gitignore
            for file_name in files:
                file_path = os.path.join(rel_root, file_name) if rel_root else file_name
                if not self.should_ignore(file_path):
                    filtered_files.append(file_path.replace('\\', '/'))
        
        return sorted(filtered_files)


def get_filtered_files(agent_path: Path) -> List[str]:
    """
    Get list of files in agent directory respecting .gitignore
    
    Args:
        agent_path: Path to agent directory
        
    Returns:
        List of relative file paths (forward slashes)
    """
    filter_obj = GitignoreFilter(agent_path)
    return filter_obj.get_filtered_files()


def should_ignore_file(agent_path: Path, file_path: str) -> bool:
    """
    Check if a specific file should be ignored
    
    Args:
        agent_path: Path to agent directory
        file_path: Relative file path to check
        
    Returns:
        True if file should be ignored
    """
    filter_obj = GitignoreFilter(agent_path)
    return filter_obj.should_ignore(file_path)
