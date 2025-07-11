//! Import resolution utilities for Python modules
//! 
//! This module provides functionality to resolve Python imports and module paths
//! for agent execution. It handles dynamic import resolution similar to Python's
//! import system.

use crate::types::{RunAgentError, RunAgentResult};
use std::collections::HashMap;
use std::fs;
use std::path::{Path, PathBuf};

/// Import resolver for Python modules
pub struct ImportResolver {
    /// Base directory for the agent
    base_dir: PathBuf,
    /// Cache of resolved imports
    import_cache: HashMap<String, String>,
    /// Verbose logging flag
    verbose: bool,
}

impl ImportResolver {
    /// Create a new import resolver
    pub fn new<P: AsRef<Path>>(base_dir: P) -> RunAgentResult<Self> {
        let base_dir = base_dir.as_ref().to_path_buf();
        
        if !base_dir.exists() {
            return Err(RunAgentError::validation(format!(
                "Base directory does not exist: {}",
                base_dir.display()
            )));
        }

        Ok(Self {
            base_dir,
            import_cache: HashMap::new(),
            verbose: false,
        })
    }

    /// Create a new import resolver with verbose logging
    pub fn with_verbose<P: AsRef<Path>>(base_dir: P, verbose: bool) -> RunAgentResult<Self> {
        let mut resolver = Self::new(base_dir)?;
        resolver.verbose = verbose;
        Ok(resolver)
    }

    /// Resolve an import from a file path and module name
    pub fn resolve_import<P: AsRef<Path>>(
        &mut self,
        file_path: P,
        module_name: &str,
    ) -> RunAgentResult<ImportInfo> {
        let file_path = file_path.as_ref();
        let cache_key = format!("{}:{}", file_path.display(), module_name);

        // Check cache first
        if let Some(cached_path) = self.import_cache.get(&cache_key) {
            return Ok(ImportInfo {
                module_name: module_name.to_string(),
                file_path: PathBuf::from(cached_path),
                import_path: cached_path.clone(),
                is_builtin: false,
            });
        }

        if self.verbose {
            tracing::debug!("Resolving import: {} from {}", module_name, file_path.display());
        }

        let import_info = self.resolve_import_internal(file_path, module_name)?;
        
        // Cache the result
        self.import_cache.insert(cache_key, import_info.import_path.clone());
        
        Ok(import_info)
    }

    /// Internal import resolution logic
    fn resolve_import_internal<P: AsRef<Path>>(
        &self,
        file_path: P,
        module_name: &str,
    ) -> RunAgentResult<ImportInfo> {
        let file_path = file_path.as_ref();
        
        // Handle relative imports (starting with .)
        if module_name.starts_with('.') {
            return self.resolve_relative_import(file_path, module_name);
        }

        // Handle absolute imports
        self.resolve_absolute_import(module_name)
    }

    /// Resolve relative imports (e.g., .module, ..module)
    fn resolve_relative_import<P: AsRef<Path>>(
        &self,
        file_path: P,
        module_name: &str,
    ) -> RunAgentResult<ImportInfo> {
        let file_path = file_path.as_ref();
        let file_dir = file_path.parent().unwrap_or(&self.base_dir);
        
        // Count leading dots to determine relative level
        let dots = module_name.chars().take_while(|&c| c == '.').count();
        let actual_module = &module_name[dots..];
        
        // Go up the directory tree based on dot count
        let mut target_dir = file_dir.to_path_buf();
        for _ in 1..dots {
            target_dir = target_dir.parent()
                .ok_or_else(|| RunAgentError::validation("Cannot go above base directory"))?
                .to_path_buf();
        }

        // Look for the module in the target directory
        if actual_module.is_empty() {
            // Import the directory itself
            return Ok(ImportInfo {
                module_name: module_name.to_string(),
                file_path: target_dir.clone(),
                import_path: format!("relative:{}", target_dir.display()),
                is_builtin: false,
            });
        }

        self.find_module_in_directory(&target_dir, actual_module)
    }

    /// Resolve absolute imports
    fn resolve_absolute_import(&self, module_name: &str) -> RunAgentResult<ImportInfo> {
        // Check if it's a built-in module
        if self.is_builtin_module(module_name) {
            return Ok(ImportInfo {
                module_name: module_name.to_string(),
                file_path: PathBuf::new(),
                import_path: format!("builtin:{}", module_name),
                is_builtin: true,
            });
        }

        // Split module path (e.g., package.submodule)
        let parts: Vec<&str> = module_name.split('.').collect();
        
        // Start from base directory and navigate through module path
        let mut current_dir = self.base_dir.clone();
        
        for (i, part) in parts.iter().enumerate() {
            let potential_file = current_dir.join(format!("{}.py", part));
            let potential_dir = current_dir.join(part);
            let potential_init = potential_dir.join("__init__.py");

            if potential_file.exists() {
                // Found a .py file
                return Ok(ImportInfo {
                    module_name: module_name.to_string(),
                    file_path: potential_file.clone(),
                    import_path: potential_file.to_string_lossy().to_string(),
                    is_builtin: false,
                });
            } else if potential_init.exists() {
                // Found a package directory
                if i == parts.len() - 1 {
                    // This is the final part, return the package
                    return Ok(ImportInfo {
                        module_name: module_name.to_string(),
                        file_path: potential_init.clone(),
                        import_path: potential_init.to_string_lossy().to_string(),
                        is_builtin: false,
                    });
                } else {
                    // Continue searching in the package directory
                    current_dir = potential_dir;
                }
            } else if potential_dir.exists() && potential_dir.is_dir() {
                // Directory exists but no __init__.py, continue anyway
                current_dir = potential_dir;
            } else {
                return Err(RunAgentError::validation(format!(
                    "Cannot find module '{}' (looking for part '{}')",
                    module_name, part
                )));
            }
        }

        Err(RunAgentError::validation(format!(
            "Module '{}' not found",
            module_name
        )))
    }

    /// Find a module within a specific directory
    fn find_module_in_directory<P: AsRef<Path>>(
        &self,
        directory: P,
        module_name: &str,
    ) -> RunAgentResult<ImportInfo> {
        let directory = directory.as_ref();
        
        // Look for module.py
        let module_file = directory.join(format!("{}.py", module_name));
        if module_file.exists() {
            return Ok(ImportInfo {
                module_name: module_name.to_string(),
                file_path: module_file.clone(),
                import_path: module_file.to_string_lossy().to_string(),
                is_builtin: false,
            });
        }

        // Look for module/__init__.py
        let module_dir = directory.join(module_name);
        let module_init = module_dir.join("__init__.py");
        if module_init.exists() {
            return Ok(ImportInfo {
                module_name: module_name.to_string(),
                file_path: module_init.clone(),
                import_path: module_init.to_string_lossy().to_string(),
                is_builtin: false,
            });
        }

        Err(RunAgentError::validation(format!(
            "Module '{}' not found in directory '{}'",
            module_name,
            directory.display()
        )))
    }

    /// Check if a module is a Python built-in module
    fn is_builtin_module(&self, module_name: &str) -> bool {
        // Common Python built-in modules
        const BUILTIN_MODULES: &[&str] = &[
            "sys", "os", "time", "datetime", "json", "re", "math", "random",
            "collections", "itertools", "functools", "operator", "typing",
            "pathlib", "subprocess", "threading", "asyncio", "logging",
            "urllib", "http", "email", "xml", "sqlite3", "csv", "configparser",
            "argparse", "inspect", "importlib", "pkgutil", "traceback",
            "warnings", "weakref", "copy", "pickle", "base64", "hashlib",
            "hmac", "secrets", "uuid", "decimal", "fractions", "statistics",
            "enum", "dataclasses", "contextlib", "tempfile", "shutil",
            "glob", "fnmatch", "linecache", "fileinput", "zipfile", "tarfile",
            "gzip", "bz2", "lzma", "socket", "ssl", "select", "signal",
            "multiprocessing", "concurrent", "queue", "sched", "string",
            "struct", "codecs", "locale", "gettext", "calendar", "pprint",
            "reprlib", "textwrap", "unicodedata", "stringprep", "readline",
            "rlcompleter", "cmd", "shlex", "io", "bufferedwriter", "platform",
            "errno", "ctypes", "mmap", "winreg", "_winapi", "winsound",
            "posix", "pwd", "grp", "termios", "tty", "pty", "fcntl", "pipes",
            "resource", "nis", "syslog", "optparse", "getopt", "distutils",
            "venv", "zipapp", "faulthandler", "trace", "timeit", "cProfile",
            "profile", "pstats", "pdb", "doctest", "unittest", "test",
        ];

        // Check if the module (or its top-level package) is builtin
        let top_level = module_name.split('.').next().unwrap_or(module_name);
        BUILTIN_MODULES.contains(&top_level)
    }

    /// Get all Python files in the base directory recursively
    pub fn discover_modules(&self) -> RunAgentResult<Vec<ModuleInfo>> {
        let mut modules = Vec::new();
        self.discover_modules_recursive(&self.base_dir, String::new(), &mut modules)?;
        Ok(modules)
    }

    /// Recursively discover modules in a directory
    fn discover_modules_recursive(
        &self,
        dir: &Path,
        prefix: String,
        modules: &mut Vec<ModuleInfo>,
    ) -> RunAgentResult<()> {
        if !dir.exists() || !dir.is_dir() {
            return Ok(());
        }

        let entries = fs::read_dir(dir)
            .map_err(|e| RunAgentError::validation(format!("Cannot read directory: {}", e)))?;

        for entry in entries {
            let entry = entry
                .map_err(|e| RunAgentError::validation(format!("Cannot read entry: {}", e)))?;
            let path = entry.path();
            let name = entry.file_name().to_string_lossy().to_string();

            // Skip hidden files and __pycache__
            if name.starts_with('.') || name == "__pycache__" {
                continue;
            }

            if path.is_file() && name.ends_with(".py") {
                let module_name = name.trim_end_matches(".py").to_string();
                let full_name = if prefix.is_empty() {
                    module_name.clone()
                } else {
                    format!("{}.{}", prefix, module_name)
                };

                modules.push(ModuleInfo {
                    name: full_name,
                    file_path: path,
                    is_package: false,
                });
            } else if path.is_dir() {
                let init_file = path.join("__init__.py");
                let is_package = init_file.exists();
                
                let full_name = if prefix.is_empty() {
                    name.clone()
                } else {
                    format!("{}.{}", prefix, name)
                };

                if is_package {
                    modules.push(ModuleInfo {
                        name: full_name.clone(),
                        file_path: init_file,
                        is_package: true,
                    });
                }

                // Recurse into subdirectory
                self.discover_modules_recursive(&path, full_name, modules)?;
            }
        }

        Ok(())
    }

    /// Clear the import cache
    pub fn clear_cache(&mut self) {
        self.import_cache.clear();
    }

    /// Get cache statistics
    pub fn cache_stats(&self) -> CacheStats {
        CacheStats {
            total_entries: self.import_cache.len(),
            base_directory: self.base_dir.clone(),
        }
    }
}

/// Information about a resolved import
#[derive(Debug, Clone)]
pub struct ImportInfo {
    /// The original module name
    pub module_name: String,
    /// Path to the module file
    pub file_path: PathBuf,
    /// Import path string for caching
    pub import_path: String,
    /// Whether this is a built-in module
    pub is_builtin: bool,
}

/// Information about a discovered module
#[derive(Debug, Clone)]
pub struct ModuleInfo {
    /// Full module name (with dots)
    pub name: String,
    /// Path to the module file
    pub file_path: PathBuf,
    /// Whether this is a package (has __init__.py)
    pub is_package: bool,
}

/// Cache statistics
#[derive(Debug)]
pub struct CacheStats {
    /// Total number of cached entries
    pub total_entries: usize,
    /// Base directory being resolved from
    pub base_directory: PathBuf,
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;
    use tempfile::TempDir;

    fn create_test_module_structure() -> TempDir {
        let temp_dir = TempDir::new().unwrap();
        let base = temp_dir.path();

        // Create main.py
        fs::write(base.join("main.py"), "def run(): pass").unwrap();

        // Create package/
        fs::create_dir(base.join("package")).unwrap();
        fs::write(base.join("package/__init__.py"), "").unwrap();
        fs::write(base.join("package/module.py"), "def func(): pass").unwrap();

        // Create subpackage/
        fs::create_dir(base.join("package/subpackage")).unwrap();
        fs::write(base.join("package/subpackage/__init__.py"), "").unwrap();
        fs::write(base.join("package/subpackage/deep.py"), "def deep_func(): pass").unwrap();

        temp_dir
    }

    #[test]
    fn test_import_resolver_creation() {
        let temp_dir = TempDir::new().unwrap();
        let resolver = ImportResolver::new(temp_dir.path());
        assert!(resolver.is_ok());
    }

    #[test]
    fn test_builtin_module_detection() {
        let temp_dir = TempDir::new().unwrap();
        let resolver = ImportResolver::new(temp_dir.path()).unwrap();
        
        assert!(resolver.is_builtin_module("sys"));
        assert!(resolver.is_builtin_module("os"));
        assert!(resolver.is_builtin_module("json"));
        assert!(!resolver.is_builtin_module("custom_module"));
    }

    #[test]
    fn test_absolute_import_resolution() {
        let temp_dir = create_test_module_structure();
        let mut resolver = ImportResolver::new(temp_dir.path()).unwrap();

        // Test resolving main.py
        let result = resolver.resolve_import(temp_dir.path().join("main.py"), "main");
        assert!(result.is_ok());

        // Test resolving package
        let result = resolver.resolve_import(temp_dir.path().join("main.py"), "package");
        assert!(result.is_ok());

        // Test resolving package.module
        let result = resolver.resolve_import(temp_dir.path().join("main.py"), "package.module");
        assert!(result.is_ok());
    }

    #[test]
    fn test_module_discovery() {
        let temp_dir = create_test_module_structure();
        let resolver = ImportResolver::new(temp_dir.path()).unwrap();

        let modules = resolver.discover_modules().unwrap();
        assert!(!modules.is_empty());

        // Should find main.py
        assert!(modules.iter().any(|m| m.name == "main"));
        
        // Should find package
        assert!(modules.iter().any(|m| m.name == "package" && m.is_package));
        
        // Should find package.module
        assert!(modules.iter().any(|m| m.name == "package.module"));
    }

    #[test]
    fn test_cache_functionality() {
        let temp_dir = create_test_module_structure();
        let mut resolver = ImportResolver::new(temp_dir.path()).unwrap();

        // First resolution
        let result1 = resolver.resolve_import(temp_dir.path().join("main.py"), "main");
        assert!(result1.is_ok());

        // Second resolution should use cache
        let result2 = resolver.resolve_import(temp_dir.path().join("main.py"), "main");
        assert!(result2.is_ok());

        let stats = resolver.cache_stats();
        assert!(stats.total_entries > 0);

        resolver.clear_cache();
        let stats = resolver.cache_stats();
        assert_eq!(stats.total_entries, 0);
    }

    #[test]
    fn test_relative_import_resolution() {
        let temp_dir = create_test_module_structure();
        let mut resolver = ImportResolver::new(temp_dir.path()).unwrap();

        // Test relative import from package/module.py to package
        let module_file = temp_dir.path().join("package/module.py");
        let result = resolver.resolve_import(&module_file, ".subpackage");
        assert!(result.is_ok());
    }
}