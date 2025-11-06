"""
Document processing utilities and helpers
"""

import os
from typing import List, Dict, Optional
from pathlib import Path
from loguru import logger


class DocumentProcessor:
    """Utilities for document processing and validation"""
    
    SUPPORTED_EXTENSIONS = {
        'text': ['.txt', '.md'],
        'pdf': ['.pdf'],
        'office': ['.doc', '.docx', '.ppt', '.pptx', '.xls', '.xlsx'],
        'image': ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.gif', '.webp']
    }
    
    @classmethod
    def get_all_supported_extensions(cls) -> List[str]:
        """Get all supported file extensions"""
        extensions = []
        for ext_list in cls.SUPPORTED_EXTENSIONS.values():
            extensions.extend(ext_list)
        return extensions
    
    @classmethod
    def validate_file(cls, file_path: str) -> Dict[str, any]:
        """
        Validate if file exists and is supported
        
        Returns:
            dict: {
                'valid': bool,
                'exists': bool,
                'supported': bool,
                'extension': str,
                'type': str,
                'size': int (in bytes),
                'error': Optional[str]
            }
        """
        result = {
            'valid': False,
            'exists': False,
            'supported': False,
            'extension': None,
            'type': None,
            'size': 0,
            'error': None
        }
        
        # Check if file exists
        if not os.path.exists(file_path):
            result['error'] = f"File not found: {file_path}"
            return result
        
        result['exists'] = True
        
        # Check if it's a file (not directory)
        if not os.path.isfile(file_path):
            result['error'] = f"Path is not a file: {file_path}"
            return result
        
        # Get file extension
        extension = Path(file_path).suffix.lower()
        result['extension'] = extension
        
        # Check if extension is supported
        for doc_type, ext_list in cls.SUPPORTED_EXTENSIONS.items():
            if extension in ext_list:
                result['supported'] = True
                result['type'] = doc_type
                break
        
        if not result['supported']:
            result['error'] = f"Unsupported file extension: {extension}"
            return result
        
        # Get file size
        try:
            result['size'] = os.path.getsize(file_path)
        except Exception as e:
            result['error'] = f"Could not read file size: {e}"
            return result
        
        result['valid'] = True
        return result
    
    @classmethod
    def find_files_in_folder(
        cls,
        folder_path: str,
        extensions: Optional[List[str]] = None,
        recursive: bool = True
    ) -> List[str]:
        """
        Find all files with specified extensions in a folder
        
        Args:
            folder_path: Path to folder
            extensions: List of extensions to include (e.g., ['.pdf', '.docx'])
                       If None, includes all supported extensions
            recursive: Whether to search recursively
        
        Returns:
            List of file paths
        """
        if not os.path.exists(folder_path):
            logger.error(f"Folder not found: {folder_path}")
            return []
        
        if not os.path.isdir(folder_path):
            logger.error(f"Path is not a folder: {folder_path}")
            return []
        
        if extensions is None:
            extensions = cls.get_all_supported_extensions()
        
        # Normalize extensions to lowercase
        extensions = [ext.lower() if ext.startswith('.') else f'.{ext.lower()}' 
                     for ext in extensions]
        
        files = []
        
        if recursive:
            for root, _, filenames in os.walk(folder_path):
                for filename in filenames:
                    if Path(filename).suffix.lower() in extensions:
                        files.append(os.path.join(root, filename))
        else:
            for item in os.listdir(folder_path):
                item_path = os.path.join(folder_path, item)
                if os.path.isfile(item_path):
                    if Path(item).suffix.lower() in extensions:
                        files.append(item_path)
        
        logger.info(f"Found {len(files)} files in {folder_path}")
        return files
    
    @classmethod
    def get_file_info(cls, file_path: str) -> Dict:
        """Get detailed file information"""
        info = {
            'path': file_path,
            'name': os.path.basename(file_path),
            'directory': os.path.dirname(file_path),
            'exists': os.path.exists(file_path)
        }
        
        if info['exists']:
            stat = os.stat(file_path)
            info.update({
                'size': stat.st_size,
                'size_mb': round(stat.st_size / (1024 * 1024), 2),
                'extension': Path(file_path).suffix.lower(),
                'created': stat.st_ctime,
                'modified': stat.st_mtime,
            })
        
        return info
    
    @classmethod
    def validate_folder(cls, folder_path: str) -> Dict:
        """Validate folder and get statistics"""
        result = {
            'valid': False,
            'exists': False,
            'is_directory': False,
            'file_count': 0,
            'supported_files': 0,
            'total_size': 0,
            'files_by_type': {},
            'error': None
        }
        
        if not os.path.exists(folder_path):
            result['error'] = f"Folder not found: {folder_path}"
            return result
        
        result['exists'] = True
        
        if not os.path.isdir(folder_path):
            result['error'] = f"Path is not a directory: {folder_path}"
            return result
        
        result['is_directory'] = True
        
        # Count files
        try:
            all_extensions = cls.get_all_supported_extensions()
            
            for root, _, files in os.walk(folder_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    ext = Path(file).suffix.lower()
                    
                    result['file_count'] += 1
                    
                    if ext in all_extensions:
                        result['supported_files'] += 1
                        
                        # Track by type
                        if ext not in result['files_by_type']:
                            result['files_by_type'][ext] = 0
                        result['files_by_type'][ext] += 1
                        
                        # Add to total size
                        try:
                            result['total_size'] += os.path.getsize(file_path)
                        except:
                            pass
            
            result['valid'] = True
            
        except Exception as e:
            result['error'] = f"Error scanning folder: {e}"
        
        return result
    
    @classmethod
    def read_text_file(cls, file_path: str) -> Optional[str]:
        """Read text from a text file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except UnicodeDecodeError:
            # Try with different encoding
            try:
                with open(file_path, 'r', encoding='latin-1') as f:
                    return f.read()
            except Exception as e:
                logger.error(f"Failed to read file {file_path}: {e}")
                return None
        except Exception as e:
            logger.error(f"Failed to read file {file_path}: {e}")
            return None
    
    @classmethod
    def chunk_text(
        cls,
        text: str,
        chunk_size: int = 1000,
        overlap: int = 100
    ) -> List[str]:
        """
        Split text into chunks with overlap
        
        Args:
            text: Text to chunk
            chunk_size: Maximum chunk size in characters
            overlap: Overlap between chunks
        
        Returns:
            List of text chunks
        """
        if len(text) <= chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            
            # Try to break at sentence boundary
            if end < len(text):
                # Look for sentence endings
                for punct in ['. ', '! ', '? ', '\n\n']:
                    last_punct = text[start:end].rfind(punct)
                    if last_punct != -1:
                        end = start + last_punct + len(punct)
                        break
            
            chunks.append(text[start:end].strip())
            start = end - overlap
        
        return chunks
    
    @classmethod
    def estimate_processing_time(cls, file_path: str) -> Dict:
        """
        Estimate processing time for a file
        (Very rough estimate based on file size and type)
        """
        validation = cls.validate_file(file_path)
        
        if not validation['valid']:
            return {
                'estimated_seconds': 0,
                'error': validation['error']
            }
        
        size_mb = validation['size'] / (1024 * 1024)
        file_type = validation['type']
        
        # Rough estimates (seconds per MB)
        time_per_mb = {
            'text': 1,
            'pdf': 5,
            'office': 8,
            'image': 3
        }
        
        base_time = time_per_mb.get(file_type, 5)
        estimated_seconds = size_mb * base_time
        
        return {
            'estimated_seconds': round(estimated_seconds, 1),
            'size_mb': round(size_mb, 2),
            'file_type': file_type
        }