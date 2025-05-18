# runagent/utils/file_handler.py
import os
import shutil
import tempfile
import typing as t


class FileHandler:
    """Utility class for handling files and directories"""
    
    @staticmethod
    def create_file(filename: str, content: str, folder_name: str = None) -> str:
        """
        Create a file with content
        
        Args:
            filename: Name of the file (can include path)
            content: Content to write to the file
            folder_name: Optional folder to create file in
            
        Returns:
            Path to created file
        """
        # If folder_name is provided, join it with filename
        if folder_name:
            os.makedirs(folder_name, exist_ok=True)
            file_path = os.path.join(folder_name, os.path.basename(filename))
        else:
            file_path = filename
            
            # Create directory if necessary
            directory = os.path.dirname(file_path)
            if directory and not os.path.exists(directory):
                os.makedirs(directory)
        
        # Write content to file
        with open(file_path, 'w') as f:
            f.write(content)
        
        return file_path
    
    @staticmethod
    def read_file(filename: str) -> t.Optional[str]:
        """
        Read file content
        
        Args:
            filename: Path to file
            
        Returns:
            File content or None if not found
        """
        if not os.path.exists(filename):
            return None
        
        with open(filename, 'r') as f:
            return f.read()
    
    @staticmethod
    def copy_directory(src: str, dst: str, exclude: t.List[str] = None) -> bool:
        """
        Copy a directory with exclusions
        
        Args:
            src: Source directory
            dst: Destination directory
            exclude: List of files or directories to exclude
            
        Returns:
            True if successful, False otherwise
        """
        if not os.path.exists(src):
            return False
        
        # Create destination directory if it doesn't exist
        os.makedirs(dst, exist_ok=True)
        
        exclude = exclude or []
        
        try:
            # Walk through the source directory
            for root, dirs, files in os.walk(src):
                # Create relative path
                rel_path = os.path.relpath(root, src)
                
                # Exclude directories
                for exclude_item in exclude:
                    if exclude_item in dirs:
                        dirs.remove(exclude_item)
                
                # Create destination directory
                if rel_path != '.':
                    os.makedirs(os.path.join(dst, rel_path), exist_ok=True)
                
                # Copy files
                for file in files:
                    # Skip excluded files
                    if file in exclude:
                        continue
                    
                    # Create full paths
                    src_file = os.path.join(root, file)
                    dst_file = os.path.join(dst, rel_path, file)
                    
                    # Copy file
                    shutil.copy2(src_file, dst_file)
            
            return True
            
        except Exception:
            return False
    
    @staticmethod
    def create_temp_directory() -> str:
        """
        Create a temporary directory
        
        Returns:
            Path to temporary directory
        """
        temp_dir = tempfile.mkdtemp(prefix="runagent_")
        return temp_dir
    
    @staticmethod
    def clean_directory(directory: str, keep_files: t.List[str] = None) -> bool:
        """
        Clean a directory by removing all files/subdirectories except those listed
        
        Args:
            directory: Directory to clean
            keep_files: List of files/directories to keep
            
        Returns:
            True if successful, False otherwise
        """
        if not os.path.exists(directory):
            return False
        
        keep_files = keep_files or []
        
        try:
            for item in os.listdir(directory):
                # Skip items in keep_files
                if item in keep_files:
                    continue
                
                # Create full path
                item_path = os.path.join(directory, item)
                
                # Remove file or directory
                if os.path.isfile(item_path):
                    os.remove(item_path)
                elif os.path.isdir(item_path):
                    shutil.rmtree(item_path)
            
            return True
            
        except Exception:
            return False
    
    @staticmethod
    def find_files(directory: str, extension: str = None, pattern: str = None) -> t.List[str]:
        """
        Find files in a directory matching extension or pattern
        
        Args:
            directory: Directory to search
            extension: File extension to match (e.g., '.py')
            pattern: Filename pattern to match
            
        Returns:
            List of matching file paths
        """
        if not os.path.exists(directory):
            return []
        
        matching_files = []
        
        import fnmatch
        
        for root, dirs, files in os.walk(directory):
            for file in files:
                # Check extension
                if extension and not file.endswith(extension):
                    continue
                
                # Check pattern
                if pattern and not fnmatch.fnmatch(file, pattern):
                    continue
                
                # Add to matching files
                matching_files.append(os.path.join(root, file))
        
        return matching_files
    
    @staticmethod
    def get_file_info(file_path: str) -> t.Dict[str, t.Any]:
        """
        Get information about a file
        
        Args:
            file_path: Path to file
            
        Returns:
            Dictionary with file information
        """
        if not os.path.exists(file_path):
            return {}
        
        import datetime
        
        stat = os.stat(file_path)
        
        return {
            'path': file_path,
            'name': os.path.basename(file_path),
            'size': stat.st_size,
            'size_human': FileHandler._human_readable_size(stat.st_size),
            'created': datetime.datetime.fromtimestamp(stat.st_ctime).isoformat(),
            'modified': datetime.datetime.fromtimestamp(stat.st_mtime).isoformat(),
            'is_directory': os.path.isdir(file_path)
        }
    
    @staticmethod
    def _human_readable_size(size_bytes: int) -> str:
        """
        Convert bytes to human-readable size
        
        Args:
            size_bytes: Size in bytes
            
        Returns:
            Human-readable size string
        """
        if size_bytes == 0:
            return "0 B"
        
        units = ["B", "KB", "MB", "GB", "TB", "PB"]
        unit_index = 0
        
        while size_bytes >= 1024 and unit_index < len(units) - 1:
            size_bytes /= 1024
            unit_index += 1
        
        return f"{size_bytes:.2f} {units[unit_index]}"