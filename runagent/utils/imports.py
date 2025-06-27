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


class DependencyAnalyzer:
    """Analyzes Python files to extract import dependencies"""

    def __init__(self):
        self.import_patterns = {
            "relative": [],
            "absolute": [],
            "star": [],
            "conditional": [],
            "dynamic": [],
        }

    def analyze_file(self, file_path: Path, package_root: Path) -> Dict[str, Set[str]]:
        """Analyze a Python file for all import patterns"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            tree = ast.parse(content)
            current_module = self._get_module_path(file_path, package_root)

            dependencies = {
                "imports": set(),
                "from_imports": set(),
                "relative_imports": set(),
                "star_imports": set(),
                "conditional_imports": set(),
            }

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        dependencies["imports"].add(alias.name)

                elif isinstance(node, ast.ImportFrom):
                    self._process_from_import(node, current_module, dependencies)

                elif isinstance(node, ast.Try):
                    self._process_conditional_imports(node, dependencies)

            return dependencies

        except Exception as e:
            logger.warning(f"Could not analyze {file_path}: {e}")
            return {
                "imports": set(),
                "from_imports": set(),
                "relative_imports": set(),
                "star_imports": set(),
                "conditional_imports": set(),
            }

    def _get_module_path(self, file_path: Path, package_root: Path) -> str:
        """Convert file path to module path"""
        try:
            relative_path = file_path.relative_to(package_root.parent)
            parts = list(relative_path.parts)

            if parts[-1] == "__init__.py":
                parts = parts[:-1]
            else:
                parts[-1] = parts[-1][:-3]  # Remove .py

            return ".".join(parts)
        except ValueError:
            # File is not under package_root
            return file_path.stem

    def _process_from_import(
        self,
        node: ast.ImportFrom,
        current_module: str,
        dependencies: Dict[str, Set[str]],
    ):
        """Process 'from X import Y' statements"""
        if node.level > 0:  # Relative import
            target_module = self._resolve_relative_import(node, current_module)
            dependencies["relative_imports"].add(target_module)
        else:  # Absolute import
            if node.module:
                dependencies["from_imports"].add(node.module)

        # Check for star imports
        for alias in node.names:
            if alias.name == "*":
                module_name = node.module or target_module if node.level > 0 else None
                if module_name:
                    dependencies["star_imports"].add(module_name)

    def _resolve_relative_import(
        self, node: ast.ImportFrom, current_module: str
    ) -> str:
        """Resolve relative import to absolute module path"""
        parts = current_module.split(".")

        # Go up 'level' directories
        target_parts = parts[: -node.level] if node.level <= len(parts) else []

        if node.module:
            target_parts.extend(node.module.split("."))

        return ".".join(target_parts) if target_parts else ""

    def _process_conditional_imports(
        self, node: ast.Try, dependencies: Dict[str, Set[str]]
    ):
        """Process try/except import blocks"""
        for child in node.body:
            if isinstance(child, (ast.Import, ast.ImportFrom)):
                if isinstance(child, ast.Import):
                    for alias in child.names:
                        dependencies["conditional_imports"].add(alias.name)
                elif isinstance(child, ast.ImportFrom) and child.module:
                    dependencies["conditional_imports"].add(child.module)


class PackageImporter:
    """
    Enhanced package importer that resolves entry points to any Python object

    Usage:
        importer = PackageImporter()
        # For functions (backward compatibility)
        run_function = importer.resolve_import(entrypoint_filepath, "run")
        output = run_function(input)
        
        # For any object (new functionality)
        my_class = importer.resolve_import(entrypoint_filepath, "MyClass")
        my_variable = importer.resolve_import(entrypoint_filepath, "MY_CONSTANT")
        my_object = importer.resolve_object(entrypoint_filepath, "some_object")
    """

    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.dependency_analyzer = DependencyAnalyzer()
        self.loaded_modules: Dict[str, Any] = {}
        self.module_dependencies: Dict[str, Set[str]] = {}
        self.failed_modules: Set[str] = set()
        self.original_sys_path = sys.path.copy()
        self.original_sys_modules = set(sys.modules.keys())
        self.package_root: Optional[Path] = None
        self.package_name: str = ""
        self.project_root: Optional[Path] = None

    def resolve_import(self, entrypoint_filepath: str, object_name: str) -> Any:
        """
        Resolve an entry point file and return a specific object from it
        
        This method maintains backward compatibility while supporting any object type.
        It no longer restricts to callable objects only.

        Args:
            entrypoint_filepath: Path to the Python file containing the object
            object_name: Name of the object to extract (function, class, variable, etc.)

        Returns:
            The requested object (function, class, variable, etc.)

        Example:
            importer = PackageImporter()
            # Functions
            run_function = importer.resolve_import("./my_project/main.py", "run")
            result = run_function({"input": "data"})
            
            # Classes
            MyClass = importer.resolve_import("./my_project/models.py", "MyClass")
            instance = MyClass()
            
            # Variables/Constants
            config = importer.resolve_import("./my_project/config.py", "CONFIG")
        """
        entrypoint_path = Path(entrypoint_filepath)

        if not entrypoint_path.exists():
            raise FileNotFoundError(
                f"Entry point file not found: {entrypoint_filepath}"
            )

        if not entrypoint_path.suffix == ".py":
            raise ValueError(
                f"Entry point must be a Python file: {entrypoint_filepath}"
            )

        # Find the project root (look for directory containing the entrypoint or its parent with __init__.py)
        self.project_root = self._find_project_root(entrypoint_path)

        if self.verbose:
            logger.info(f"🎯 Resolving entry point: {entrypoint_filepath}")
            logger.info(f"📁 Project root: {self.project_root}")
            logger.info(f"🔍 Looking for object: {object_name}")

        try:
            # Add project root to sys.path
            project_parent = str(self.project_root.parent)
            if project_parent not in sys.path:
                sys.path.insert(0, project_parent)

            # Load the package structure if it exists
            if self._is_package_structure():
                self._load_package_structure()

            # Load the specific entry point module
            entry_module = self._load_entry_point_module(entrypoint_path)

            # Extract the object
            if not hasattr(entry_module, object_name):
                raise AttributeError(
                    f"Object '{object_name}' not found in {entrypoint_filepath}"
                )

            target_object = getattr(entry_module, object_name)

            if self.verbose:
                object_type = self._get_object_type_description(target_object)
                logger.info(f"✅ Successfully resolved: {object_name}")
                logger.info(f"   Object: {target_object}")
                logger.info(f"   Type: {object_type}")
                
                # Show docstring if available
                if hasattr(target_object, "__doc__") and target_object.__doc__:
                    doc_preview = target_object.__doc__.strip().split('\n')[0][:100]
                    logger.info(f"   Doc: {doc_preview}{'...' if len(doc_preview) == 100 else ''}")

            return target_object

        except Exception as e:
            logger.error(f"❌ Failed to resolve entry point: {e}")
            self._cleanup()
            raise

    def resolve_object(self, entrypoint_filepath: str, object_name: str) -> Any:
        """
        Alias for resolve_import for clearer semantics when importing non-callable objects
        
        Args:
            entrypoint_filepath: Path to the Python file containing the object
            object_name: Name of the object to extract

        Returns:
            The requested object
        """
        return self.resolve_import(entrypoint_filepath, object_name)

    def resolve_multiple(self, entrypoint_filepath: str, *object_names: str) -> Tuple[Any, ...]:
        """
        Resolve multiple objects from the same module efficiently
        
        Args:
            entrypoint_filepath: Path to the Python file containing the objects
            *object_names: Names of the objects to extract

        Returns:
            Tuple of the requested objects in the same order

        Example:
            importer = PackageImporter()
            func, MyClass, config = importer.resolve_multiple(
                "./my_project/main.py", "run", "MyClass", "CONFIG"
            )
        """
        if not object_names:
            raise ValueError("At least one object name must be provided")

        entrypoint_path = Path(entrypoint_filepath)

        if not entrypoint_path.exists():
            raise FileNotFoundError(
                f"Entry point file not found: {entrypoint_filepath}"
            )

        if not entrypoint_path.suffix == ".py":
            raise ValueError(
                f"Entry point must be a Python file: {entrypoint_filepath}"
            )

        # Find the project root
        self.project_root = self._find_project_root(entrypoint_path)

        if self.verbose:
            logger.info(f"🎯 Resolving multiple objects from: {entrypoint_filepath}")
            logger.info(f"📁 Project root: {self.project_root}")
            logger.info(f"🔍 Looking for objects: {', '.join(object_names)}")

        try:
            # Add project root to sys.path
            project_parent = str(self.project_root.parent)
            if project_parent not in sys.path:
                sys.path.insert(0, project_parent)

            # Load the package structure if it exists
            if self._is_package_structure():
                self._load_package_structure()

            # Load the specific entry point module
            entry_module = self._load_entry_point_module(entrypoint_path)

            # Extract all objects
            resolved_objects = []
            for object_name in object_names:
                if not hasattr(entry_module, object_name):
                    raise AttributeError(
                        f"Object '{object_name}' not found in {entrypoint_filepath}"
                    )
                
                target_object = getattr(entry_module, object_name)
                resolved_objects.append(target_object)

                if self.verbose:
                    object_type = self._get_object_type_description(target_object)
                    logger.info(f"✅ Resolved {object_name}: {object_type}")

            return tuple(resolved_objects)

        except Exception as e:
            logger.error(f"❌ Failed to resolve objects: {e}")
            self._cleanup()
            raise

    def list_available_objects(self, entrypoint_filepath: str) -> Dict[str, str]:
        """
        List all available objects in a module with their types
        
        Args:
            entrypoint_filepath: Path to the Python file to inspect

        Returns:
            Dictionary mapping object names to their type descriptions

        Example:
            importer = PackageImporter()
            objects = importer.list_available_objects("./my_project/main.py")
            print(objects)
            # {'run': 'function', 'MyClass': 'class', 'CONFIG': 'dict', ...}
        """
        entrypoint_path = Path(entrypoint_filepath)

        if not entrypoint_path.exists():
            raise FileNotFoundError(
                f"Entry point file not found: {entrypoint_filepath}"
            )

        try:
            # Set up the environment
            self.project_root = self._find_project_root(entrypoint_path)
            
            project_parent = str(self.project_root.parent)
            if project_parent not in sys.path:
                sys.path.insert(0, project_parent)

            if self._is_package_structure():
                self._load_package_structure()

            # Load the module
            entry_module = self._load_entry_point_module(entrypoint_path)

            # Get all public objects (not starting with _)
            available_objects = {}
            for name in dir(entry_module):
                if not name.startswith('_'):  # Skip private/magic methods
                    obj = getattr(entry_module, name)
                    obj_type = self._get_object_type_description(obj)
                    available_objects[name] = obj_type

            return available_objects

        except Exception as e:
            logger.error(f"❌ Failed to list objects: {e}")
            self._cleanup()
            raise

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
            elif isinstance(obj, types.BuiltinFunctionType):
                return "builtin_function"
            elif hasattr(obj, '__call__'):
                return "callable"
            else:
                return "callable_object"
        elif isinstance(obj, types.ModuleType):
            return "module"
        elif isinstance(obj, (str, int, float, bool, type(None))):
            return type(obj).__name__
        elif isinstance(obj, (list, tuple, dict, set)):
            return type(obj).__name__
        else:
            return type(obj).__name__

    def _find_project_root(self, entrypoint_path: Path) -> Path:
        """Find the root directory of the project"""
        current = entrypoint_path.parent

        # Look for common project indicators
        project_indicators = [
            "__init__.py",
            "setup.py",
            "pyproject.toml",
            "requirements.txt",
            ".git",
        ]

        # Start from the entry point directory and work upwards
        max_levels = 5  # Prevent infinite recursion
        level = 0

        while level < max_levels:
            # Check if current directory has project indicators
            for indicator in project_indicators:
                if (current / indicator).exists():
                    if self.verbose:
                        logger.debug(
                            f"Found project indicator '{indicator}' in {current}"
                        )
                    return current

            # Check if we've reached the filesystem root
            parent = current.parent
            if parent == current:
                break

            current = parent
            level += 1

        # If no project root found, use the entry point's parent directory
        return entrypoint_path.parent

    def _is_package_structure(self) -> bool:
        """Check if the project has a package structure"""
        # Look for __init__.py files indicating a package
        if (self.project_root / "__init__.py").exists():
            self.package_root = self.project_root
            self.package_name = self.project_root.name
            return True

        # Look for subdirectories with __init__.py
        for item in self.project_root.iterdir():
            if item.is_dir() and (item / "__init__.py").exists():
                self.package_root = item
                self.package_name = item.name
                return True

        return False

    def _load_package_structure(self):
        """Load the package structure if it exists"""
        if not self.package_root:
            return

        if self.verbose:
            logger.info(f"📦 Loading package structure: {self.package_name}")

        # Analyze dependencies
        self._analyze_package_structure()

        # Load in dependency order
        load_order = self._topological_sort()

        for module_name in load_order:
            if (
                module_name not in self.loaded_modules
                and module_name not in self.failed_modules
            ):
                self._load_single_module(module_name)

    def _load_entry_point_module(self, entrypoint_path: Path) -> Any:
        """Load the specific entry point module"""
        # Generate module name
        if self.package_root:
            try:
                relative_path = entrypoint_path.relative_to(self.package_root.parent)
                module_name = ".".join(relative_path.parts[:-1] + (relative_path.stem,))
            except ValueError:
                module_name = f"entrypoint_{entrypoint_path.stem}"
        else:
            module_name = f"entrypoint_{entrypoint_path.stem}"

        # Check if already loaded
        if module_name in self.loaded_modules:
            return self.loaded_modules[module_name]

        # Load the module
        try:
            spec = importlib.util.spec_from_file_location(
                module_name, str(entrypoint_path)
            )
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
                logger.warning(f"❌ Failed to load entry point module: {e}")

            # Clean up
            if module_name in sys.modules:
                del sys.modules[module_name]

            raise

    def _analyze_package_structure(self):
        """Analyze the package structure and dependencies"""
        if not self.package_root:
            return

        if self.verbose:
            logger.debug(f"🔍 Analyzing package structure: {self.package_name}")

        # Find all Python files
        py_files = list(self.package_root.rglob("*.py"))

        for py_file in py_files:
            if py_file.name.startswith("__pycache__"):
                continue

            module_name = self._file_to_module_name(py_file)
            dependencies = self.dependency_analyzer.analyze_file(
                py_file, self.package_root
            )

            # Resolve dependencies to full module names
            resolved_deps = set()
            for dep_type, deps in dependencies.items():
                for dep in deps:
                    if dep and dep.startswith(self.package_name):
                        resolved_deps.add(dep)

            self.module_dependencies[module_name] = resolved_deps

    def _file_to_module_name(self, file_path: Path) -> str:
        """Convert file path to module name"""
        try:
            relative_path = file_path.relative_to(self.package_root.parent)
            parts = list(relative_path.parts)

            if parts[-1] == "__init__.py":
                parts = parts[:-1]
            else:
                parts[-1] = parts[-1][:-3]  # Remove .py extension

            return ".".join(parts)
        except ValueError:
            return file_path.stem

    def _topological_sort(self) -> List[str]:
        """Sort modules by dependencies using Kahn's algorithm"""
        # Create dependency graph
        in_degree = defaultdict(int)
        graph = defaultdict(set)

        all_modules = set(self.module_dependencies.keys())

        # Add dependencies from analysis
        for module, deps in self.module_dependencies.items():
            for dep in deps:
                if dep in all_modules:
                    graph[dep].add(module)
                    in_degree[module] += 1

        # Initialize modules with no dependencies
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
                logger.debug(f"Potential circular dependencies: {remaining}")
            result.extend(remaining)

        return result

    def _load_single_module(self, module_name: str) -> Optional[Any]:
        """Load a single module"""
        if module_name in self.loaded_modules:
            return self.loaded_modules[module_name]

        if module_name in self.failed_modules:
            return None

        try:
            # Convert module name to file path
            file_path = self._module_name_to_file(module_name)

            if not file_path or not file_path.exists():
                self.failed_modules.add(module_name)
                return None

            # Create module spec
            spec = importlib.util.spec_from_file_location(module_name, str(file_path))
            if not spec or not spec.loader:
                self.failed_modules.add(module_name)
                return None

            # Create module
            module = importlib.util.module_from_spec(spec)

            # Add to sys.modules BEFORE execution (crucial for relative imports)
            sys.modules[module_name] = module

            # Execute module
            spec.loader.exec_module(module)

            self.loaded_modules[module_name] = module

            if self.verbose:
                logger.debug(f"✅ Loaded: {module_name}")

            return module

        except Exception as e:
            if self.verbose:
                logger.debug(f"⚠️  Failed to load {module_name}: {e}")

            self.failed_modules.add(module_name)

            # Remove from sys.modules if it was added
            if module_name in sys.modules:
                del sys.modules[module_name]

            return None

    def _module_name_to_file(self, module_name: str) -> Optional[Path]:
        """Convert module name to file path"""
        if not self.package_root:
            return None

        parts = module_name.split(".")

        # Start from package root parent
        file_path = self.package_root.parent

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

    def _cleanup(self):
        """Clean up sys.path and sys.modules"""
        # Restore sys.path
        sys.path[:] = self.original_sys_path

        # Remove added modules from sys.modules
        current_modules = set(sys.modules.keys())
        added_modules = current_modules - self.original_sys_modules

        for module_name in added_modules:
            if self.package_name and module_name.startswith(self.package_name):
                del sys.modules[module_name]

    def get_load_statistics(self) -> Dict[str, Any]:
        """Get statistics about the loading process"""
        total_attempted = len(self.module_dependencies)
        loaded_count = len(self.loaded_modules)
        failed_count = len(self.failed_modules)

        return {
            "total_modules": total_attempted,
            "loaded_successfully": loaded_count,
            "failed_to_load": failed_count,
            "success_rate": (
                f"{(loaded_count / total_attempted * 100):.1f}%"
                if total_attempted > 0
                else "100%"
            ),
            "project_root": str(self.project_root) if self.project_root else None,
            "package_name": self.package_name,
            "loaded_modules": list(self.loaded_modules.keys()),
            "failed_modules": list(self.failed_modules),
        }


# Example usage and backward compatibility demonstration
if __name__ == "__main__":
    # Initialize the importer
    importer = PackageImporter()
    
    # Example 1: Import a function (backward compatible)
    try:
        run_func = importer.resolve_import("./my_project/main.py", "run")
        print(f"Imported function: {run_func}")
    except Exception as e:
        print(f"Could not import function: {e}")
    
    # Example 2: Import a class
    try:
        MyClass = importer.resolve_import("./my_project/models.py", "MyClass")
        print(f"Imported class: {MyClass}")
    except Exception as e:
        print(f"Could not import class: {e}")
    
    # Example 3: Import a variable/constant
    try:
        config = importer.resolve_import("./my_project/config.py", "CONFIG")
        print(f"Imported config: {config}")
    except Exception as e:
        print(f"Could not import config: {e}")
    
    # Example 4: Import multiple objects at once
    try:
        func, cls, var = importer.resolve_multiple(
            "./my_project/main.py", "run", "MyClass", "CONSTANT"
        )
        print(f"Imported multiple: {func}, {cls}, {var}")
    except Exception as e:
        print(f"Could not import multiple: {e}")
    
    # Example 5: List available objects
    try:
        available = importer.list_available_objects("./my_project/main.py")
        print(f"Available objects: {available}")
    except Exception as e:
        print(f"Could not list objects: {e}")