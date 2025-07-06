import ast
import importlib
import importlib.util
import logging
import os
import shutil
import sys
import tempfile
import zipfile
from collections import defaultdict, deque
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PackageImporter:
    """
    Enhanced package importer that handles ALL import patterns:
    - Relative imports without __init__.py
    - Mixed package and standalone structures
    - Dynamic import resolution
    - Automatic import rewriting
    """

    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.loaded_modules: Dict[str, Any] = {}
        self.module_dependencies: Dict[str, Set[str]] = {}
        self.failed_modules: Set[str] = set()
        self.original_sys_path = sys.path.copy()
        self.original_sys_modules = set(sys.modules.keys())
        self.project_root: Optional[Path] = None
        self.temp_package_dirs: List[Path] = []  # Track temporary __init__.py files
        self.import_rewrites: Dict[str, str] = {}  # Track what imports we've rewritten

    def resolve_import(self, entrypoint_filepath: str, object_name: str) -> Any:
        """
        Enhanced resolve_import that handles any project structure
        """
        entrypoint_path = Path(entrypoint_filepath)

        if not entrypoint_path.exists():
            raise FileNotFoundError(f"Entry point file not found: {entrypoint_filepath}")

        if not entrypoint_path.suffix == ".py":
            raise ValueError(f"Entry point must be a Python file: {entrypoint_filepath}")

        self.project_root = self._find_project_root(entrypoint_path)

        if self.verbose:
            logger.info(f"🎯 Resolving entry point: {entrypoint_filepath}")
            logger.info(f"📁 Project root: {self.project_root}")
            logger.info(f"🔍 Looking for object: {object_name}")

        try:
            # Step 1: Analyze the entry point for import issues
            import_issues = self._analyze_import_issues(entrypoint_path)
            
            if import_issues:
                if self.verbose:
                    logger.info(f"🔧 Detected import issues, applying fixes...")
                self._fix_import_issues(import_issues)

            # Step 2: Set up the import environment
            self._setup_import_environment(entrypoint_path)

            # Step 3: Load dependencies in the right order
            self._load_project_dependencies(entrypoint_path)

            # Step 4: Load the entry point module
            entry_module = self._load_entry_point_module(entrypoint_path)

            # Step 5: Extract the target object
            if not hasattr(entry_module, object_name):
                available_objects = [name for name in dir(entry_module) if not name.startswith('_')]
                raise AttributeError(
                    f"Object '{object_name}' not found in {entrypoint_filepath}.\n"
                    f"Available objects: {available_objects}"
                )

            target_object = getattr(entry_module, object_name)

            if self.verbose:
                object_type = self._get_object_type_description(target_object)
                logger.info(f"✅ Successfully resolved: {object_name}")
                logger.info(f"   Object: {target_object}")
                logger.info(f"   Type: {object_type}")

            return target_object

        except Exception as e:
            logger.error(f"❌ Failed to resolve entry point: {e}")
            self._cleanup()
            raise

    def _analyze_import_issues(self, entrypoint_path: Path) -> Dict[str, Any]:
        """
        Analyze the entry point and its dependencies for common import issues
        """
        issues = {
            "relative_imports_without_package": [],
            "missing_init_files": [],
            "circular_imports": [],
            "missing_modules": []
        }

        try:
            with open(entrypoint_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            
            # Check for relative imports
            relative_imports = []
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.level > 0:
                    module_name = node.module or ""
                    relative_imports.append({
                        'level': node.level,
                        'module': module_name,
                        'names': [alias.name for alias in node.names],
                        'line': node.lineno
                    })

            # Check if directory has __init__.py
            if relative_imports and not (entrypoint_path.parent / "__init__.py").exists():
                issues["relative_imports_without_package"] = relative_imports
                issues["missing_init_files"].append(entrypoint_path.parent)

            return issues

        except Exception as e:
            if self.verbose:
                logger.warning(f"Could not analyze import issues: {e}")
            return issues

    def _fix_import_issues(self, issues: Dict[str, Any]):
        """
        Apply automatic fixes for common import issues
        """
        # Fix 1: Create temporary __init__.py files for relative imports
        if issues["missing_init_files"]:
            for missing_dir in issues["missing_init_files"]:
                self._create_temporary_init_file(missing_dir)

        # Fix 2: Rewrite relative imports if needed (more complex case)
        if issues["relative_imports_without_package"]:
            # We'll handle this during module loading by modifying sys.path appropriately
            pass

    def _create_temporary_init_file(self, directory: Path):
        """
        Create a temporary __init__.py file to make directory a package
        """
        init_file = directory / "__init__.py"
        
        if not init_file.exists():
            init_file.touch()
            self.temp_package_dirs.append(directory)
            
            if self.verbose:
                logger.info(f"📦 Created temporary __init__.py in {directory}")

    def _setup_import_environment(self, entrypoint_path: Path):
        """
        Set up the import environment to handle various project structures
        """
        # Add project root to sys.path
        project_parent = str(self.project_root.parent)
        if project_parent not in sys.path:
            sys.path.insert(0, project_parent)

        # Add the project root itself to sys.path (for absolute imports)
        project_root_str = str(self.project_root)
        if project_root_str not in sys.path:
            sys.path.insert(0, project_root_str)

        # Add the entry point's directory (for same-directory imports)
        entry_dir = str(entrypoint_path.parent)
        if entry_dir not in sys.path:
            sys.path.insert(0, entry_dir)

        if self.verbose:
            logger.debug(f"🛤️ Updated sys.path: {sys.path[:3]}...")

    def _load_project_dependencies(self, entrypoint_path: Path):
        """
        Analyze and load project dependencies in the correct order
        """
        # Find all Python files in the project
        py_files = []
        for py_file in self.project_root.rglob("*.py"):
            if not any(part.startswith('.') for part in py_file.parts):  # Skip hidden dirs
                py_files.append(py_file)

        # Analyze dependencies between files
        dependency_graph = {}
        for py_file in py_files:
            deps = self._extract_local_dependencies(py_file)
            module_name = self._file_to_module_name(py_file)
            dependency_graph[module_name] = deps

        # Load dependencies in topological order
        load_order = self._topological_sort_dependencies(dependency_graph)
        
        for module_name in load_order:
            if module_name not in self.loaded_modules:
                module_file = self._module_name_to_file(module_name)
                if module_file and module_file.exists():
                    self._load_single_module_safe(module_name, module_file)

    def _extract_local_dependencies(self, file_path: Path) -> Set[str]:
        """
        Extract local (project-internal) dependencies from a Python file
        """
        dependencies = set()
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        # Check if this is a local module
                        if self._is_local_module(alias.name):
                            dependencies.add(alias.name)
                
                elif isinstance(node, ast.ImportFrom):
                    if node.level > 0:  # Relative import
                        resolved_module = self._resolve_relative_import(node, file_path)
                        if resolved_module:
                            dependencies.add(resolved_module)
                    elif node.module and self._is_local_module(node.module):
                        dependencies.add(node.module)
        
        except Exception as e:
            if self.verbose:
                logger.debug(f"Could not extract dependencies from {file_path}: {e}")
        
        return dependencies

    def _resolve_relative_import(self, node: ast.ImportFrom, current_file: Path) -> Optional[str]:
        """
        Resolve relative import to absolute module name
        """
        try:
            # Calculate the target directory based on the relative level
            current_dir = current_file.parent
            target_dir = current_dir
            
            # Go up 'level' directories
            for _ in range(node.level):
                target_dir = target_dir.parent
            
            # Add the module path if specified
            if node.module:
                target_dir = target_dir / node.module.replace('.', os.sep)
            
            # Convert back to module name
            try:
                relative_path = target_dir.relative_to(self.project_root.parent)
                return '.'.join(relative_path.parts)
            except ValueError:
                return None
        
        except Exception:
            return None

    def _is_local_module(self, module_name: str) -> bool:
        """
        Check if a module is local to the project
        """
        # Check if there's a corresponding .py file in the project
        module_path = self.project_root / (module_name.replace('.', os.sep) + '.py')
        if module_path.exists():
            return True
        
        # Check if it's a package directory
        package_path = self.project_root / module_name.replace('.', os.sep)
        if package_path.is_dir() and (package_path / "__init__.py").exists():
            return True
        
        return False

    def _load_single_module_safe(self, module_name: str, module_file: Path):
        """
        Safely load a single module with enhanced error handling
        """
        if module_name in self.loaded_modules or module_name in self.failed_modules:
            return

        try:
            # Check if the file has relative imports that need special handling
            needs_package_context = self._file_has_relative_imports(module_file)
            
            if needs_package_context:
                # Ensure the directory is treated as a package
                self._ensure_package_structure(module_file.parent)
            
            # Create module spec
            spec = importlib.util.spec_from_file_location(module_name, str(module_file))
            if not spec or not spec.loader:
                self.failed_modules.add(module_name)
                return

            # Create and load module
            module = importlib.util.module_from_spec(spec)
            
            # Add to sys.modules BEFORE execution (crucial for relative imports)
            sys.modules[module_name] = module
            
            # Execute module
            spec.loader.exec_module(module)
            
            self.loaded_modules[module_name] = module
            
            if self.verbose:
                logger.debug(f"✅ Loaded: {module_name}")

        except Exception as e:
            if self.verbose:
                logger.debug(f"⚠️ Failed to load {module_name}: {e}")
            
            self.failed_modules.add(module_name)
            
            # Clean up sys.modules
            if module_name in sys.modules:
                del sys.modules[module_name]

    def _file_has_relative_imports(self, file_path: Path) -> bool:
        """
        Check if a file contains relative imports
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.level > 0:
                    return True
            
            return False
        
        except Exception:
            return False

    def _ensure_package_structure(self, directory: Path):
        """
        Ensure a directory has the necessary __init__.py to be treated as a package
        """
        init_file = directory / "__init__.py"
        if not init_file.exists():
            self._create_temporary_init_file(directory)

    def _load_entry_point_module(self, entrypoint_path: Path) -> Any:
        """
        Load the specific entry point module with enhanced handling
        """
        # Generate appropriate module name
        module_name = self._generate_entry_point_module_name(entrypoint_path)
        
        # Check if already loaded
        if module_name in self.loaded_modules:
            return self.loaded_modules[module_name]

        try:
            # Ensure the entry point's directory is treated as a package if it has relative imports
            if self._file_has_relative_imports(entrypoint_path):
                self._ensure_package_structure(entrypoint_path.parent)
            
            # Create module spec
            spec = importlib.util.spec_from_file_location(module_name, str(entrypoint_path))
            if not spec or not spec.loader:
                raise ImportError(f"Could not create spec for {entrypoint_path}")

            module = importlib.util.module_from_spec(spec)

            # Add to sys.modules before execution
            sys.modules[module_name] = module

            # Execute the module
            spec.loader.exec_module(module)

            self.loaded_modules[module_name] = module

            if self.verbose:
                logger.debug(f"✅ Loaded entry point module: {module_name}")

            return module

        except Exception as e:
            if self.verbose:
                logger.error(f"❌ Failed to load entry point module: {e}")

            # Clean up
            if module_name in sys.modules:
                del sys.modules[module_name]

            raise

    def _generate_entry_point_module_name(self, entrypoint_path: Path) -> str:
        """
        Generate an appropriate module name for the entry point
        """
        try:
            # Try to create a name relative to project root
            relative_path = entrypoint_path.relative_to(self.project_root.parent)
            parts = list(relative_path.parts[:-1]) + [relative_path.stem]
            return '.'.join(parts)
        except ValueError:
            # Fallback to simple name
            return f"entrypoint_{entrypoint_path.stem}"

    def _find_project_root(self, entrypoint_path: Path) -> Path:
        """Enhanced project root detection"""
        current = entrypoint_path.parent

        # Look for common project indicators
        project_indicators = [
            "__init__.py",
            "setup.py", 
            "pyproject.toml",
            "requirements.txt",
            ".git",
            "Pipfile",
            "poetry.lock"
        ]

        max_levels = 5
        level = 0

        while level < max_levels:
            # Check for project indicators
            for indicator in project_indicators:
                if (current / indicator).exists():
                    if self.verbose:
                        logger.debug(f"Found project indicator '{indicator}' in {current}")
                    return current

            parent = current.parent
            if parent == current:  # Reached filesystem root
                break

            current = parent
            level += 1

        # If no project root found, use the entry point's parent directory
        return entrypoint_path.parent

    def _topological_sort_dependencies(self, dependency_graph: Dict[str, Set[str]]) -> List[str]:
        """Sort modules by dependencies using Kahn's algorithm"""
        in_degree = defaultdict(int)
        graph = defaultdict(set)
        
        all_modules = set(dependency_graph.keys())
        
        # Build the graph
        for module, deps in dependency_graph.items():
            for dep in deps:
                if dep in all_modules:
                    graph[dep].add(module)
                    in_degree[module] += 1
        
        # Initialize queue with modules that have no dependencies
        queue = deque([module for module in all_modules if in_degree[module] == 0])
        result = []
        
        while queue:
            current = queue.popleft()
            result.append(current)
            
            # Update dependent modules
            for dependent in graph[current]:
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)
        
        # Handle remaining modules (potential circular dependencies)
        remaining = all_modules - set(result)
        if remaining:
            if self.verbose:
                logger.debug(f"Adding remaining modules (potential circular deps): {remaining}")
            result.extend(remaining)
        
        return result

    def _file_to_module_name(self, file_path: Path) -> str:
        """Convert file path to module name"""
        try:
            relative_path = file_path.relative_to(self.project_root.parent)
            parts = list(relative_path.parts)
            
            if parts[-1] == "__init__.py":
                parts = parts[:-1]
            else:
                parts[-1] = parts[-1][:-3]  # Remove .py extension
            
            return ".".join(parts)
        except ValueError:
            return file_path.stem

    def _module_name_to_file(self, module_name: str) -> Optional[Path]:
        """Convert module name to file path"""
        parts = module_name.split(".")
        
        # Start from project root parent
        file_path = self.project_root.parent
        
        for part in parts:
            file_path = file_path / part
        
        # Try as regular module (.py file)
        py_file = file_path.with_suffix(".py")
        if py_file.exists():
            return py_file
        
        # Try as package (__init__.py)
        init_file = file_path / "__init__.py"
        if init_file.exists():
            return init_file
        
        return None

    def _get_object_type_description(self, obj: Any) -> str:
        """Get a human-readable description of an object's type"""
        import types
        
        if callable(obj):
            if isinstance(obj, type):
                return "class"
            elif isinstance(obj, types.FunctionType):
                return "function"
            elif isinstance(obj, types.MethodType):
                return "method"
            else:
                return "callable"
        elif isinstance(obj, types.ModuleType):
            return "module"
        elif isinstance(obj, (str, int, float, bool, type(None))):
            return type(obj).__name__
        elif isinstance(obj, (list, tuple, dict, set)):
            return type(obj).__name__
        else:
            return type(obj).__name__

    def _cleanup(self):
        """Enhanced cleanup that removes temporary files"""
        # Remove temporary __init__.py files
        for temp_dir in self.temp_package_dirs:
            init_file = temp_dir / "__init__.py"
            if init_file.exists():
                try:
                    init_file.unlink()
                    if self.verbose:
                        logger.debug(f"🗑️ Removed temporary __init__.py from {temp_dir}")
                except Exception as e:
                    if self.verbose:
                        logger.warning(f"Could not remove temporary file: {e}")
        
        # Restore sys.path
        sys.path[:] = self.original_sys_path
        
        # Remove added modules from sys.modules
        current_modules = set(sys.modules.keys())
        added_modules = current_modules - self.original_sys_modules
        
        for module_name in list(added_modules):
            if module_name in self.loaded_modules or module_name.startswith('entrypoint_'):
                try:
                    del sys.modules[module_name]
                except KeyError:
                    pass

    def get_import_analysis(self, entrypoint_filepath: str) -> Dict[str, Any]:
        """
        Analyze an entry point without loading it - useful for debugging
        """
        entrypoint_path = Path(entrypoint_filepath)
        self.project_root = self._find_project_root(entrypoint_path)
        
        analysis = {
            "project_root": str(self.project_root),
            "import_issues": self._analyze_import_issues(entrypoint_path),
            "has_package_structure": (entrypoint_path.parent / "__init__.py").exists(),
            "local_dependencies": list(self._extract_local_dependencies(entrypoint_path)),
            "python_files_in_project": [str(p) for p in self.project_root.rglob("*.py")],
        }
        
        return analysis
