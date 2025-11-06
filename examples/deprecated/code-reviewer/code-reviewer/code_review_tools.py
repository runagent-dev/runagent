"""
Code Review Tools for Letta Agent
Provides specialized analysis functions for code quality, security, and improvements
"""

def analyze_code_quality(code: str, language: str = "auto") -> dict:
    """
    Analyze code quality including readability, complexity, and best practices.
    
    Args:
        code (str): The source code to analyze
        language (str): Programming language (auto-detect if not specified)
    
    Returns:
        dict: Quality analysis results
    """
    # ALL IMPORTS MUST BE INSIDE THE FUNCTION FOR LETTA
    import re
    import ast
    
    def _detect_language_internal(code: str) -> str:
        """Auto-detect programming language from code content"""
        code_lower = code.lower()
        
        # Rust indicators
        if any(keyword in code for keyword in ['fn ', 'let ', 'mut ', 'impl ', 'struct ', 'enum ', 'match ']):
            return "rust"
        
        # Python indicators
        if any(keyword in code for keyword in ['def ', 'import ', 'from ', 'class ', '__init__']):
            return "python"
        
        # JavaScript/TypeScript indicators
        if any(keyword in code for keyword in ['function ', 'const ', 'let ', 'var ', '=>', 'console.log']):
            return "javascript"
        
        return "unknown"

    def _analyze_python_quality_internal(code: str) -> dict:
        """Python-specific quality analysis"""
        import ast
        import re
        
        issues = []
        strengths = []
        
        try:
            # Try to parse as AST for deeper analysis
            tree = ast.parse(code)
            
            # Check for list comprehensions (good)
            if any(isinstance(node, ast.ListComp) for node in ast.walk(tree)):
                strengths.append("Uses list comprehensions for concise code")
            
            # Check for docstrings
            functions = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
            documented_functions = 0
            for func in functions:
                if (ast.get_docstring(func)):
                    documented_functions += 1
            
            if documented_functions > 0:
                strengths.append(f"{documented_functions}/{len(functions)} functions have docstrings")
            elif len(functions) > 0:
                issues.append("Functions lack docstrings")
                
        except SyntaxError:
            issues.append("Code contains syntax errors")
        
        # PEP 8 style checks
        if re.search(r'def\s+[A-Z]', code):
            issues.append("Function names should be snake_case (PEP 8)")
        
        if re.search(r'class\s+[a-z]', code):
            issues.append("Class names should be PascalCase (PEP 8)")
        
        return {"issues": issues, "strengths": strengths}

    def _analyze_rust_quality_internal(code: str) -> dict:
        """Rust-specific quality analysis"""
        import re
        
        issues = []
        strengths = []
        
        # Check for proper error handling
        if 'Result<' in code or '?' in code:
            strengths.append("Uses Result type for error handling")
        elif 'unwrap()' in code:
            issues.append("Consider using proper error handling instead of unwrap()")
        
        # Check for documentation
        if '///' in code:
            strengths.append("Contains documentation comments")
        
        # Check for ownership patterns
        if '&mut ' in code:
            strengths.append("Uses mutable references appropriately")
        
        # Check naming conventions
        if re.search(r'fn\s+[A-Z]', code):
            issues.append("Function names should be snake_case")
        
        return {"issues": issues, "strengths": strengths}

    def _analyze_js_quality_internal(code: str) -> dict:
        """JavaScript-specific quality analysis"""
        issues = []
        strengths = []
        
        # Check for modern JS features
        if '=>' in code:
            strengths.append("Uses arrow functions")
        
        if 'const ' in code or 'let ' in code:
            strengths.append("Uses modern variable declarations")
        elif 'var ' in code:
            issues.append("Consider using 'let' or 'const' instead of 'var'")
        
        # Check for async patterns
        if 'async' in code and 'await' in code:
            strengths.append("Uses async/await for asynchronous operations")
        
        return {"issues": issues, "strengths": strengths}

    def _analyze_generic_quality_internal(code: str) -> dict:
        """Generic quality analysis for unknown languages"""
        issues = []
        strengths = []
        
        # Basic checks
        if len(code.split('\n')) > 100:
            issues.append("File is quite large - consider breaking into smaller modules")
        
        # Check for comments
        comment_ratio = len([line for line in code.split('\n') if line.strip().startswith('#')]) / len(code.split('\n'))
        if comment_ratio > 0.1:
            strengths.append("Well-commented code")
        elif comment_ratio < 0.05:
            issues.append("Could benefit from more comments")
        
        return {"issues": issues, "strengths": strengths}

    def _calculate_quality_score_internal(analysis: dict) -> int:
        """Calculate overall quality score 0-100"""
        base_score = 80
        
        # Deduct for issues
        issues_count = len(analysis.get("issues", []))
        base_score -= min(issues_count * 5, 40)
        
        # Add for strengths
        strengths_count = len(analysis.get("strengths", []))
        base_score += min(strengths_count * 3, 20)
        
        return max(0, min(100, base_score))
    
    try:
        # Auto-detect language if not specified
        if language == "auto":
            language = _detect_language_internal(code)
        
        analysis = {
            "language": language,
            "metrics": {},
            "issues": [],
            "strengths": [],
            "overall_score": 0
        }
        
        # Basic metrics
        lines = code.split('\n')
        analysis["metrics"] = {
            "total_lines": len(lines),
            "code_lines": len([line for line in lines if line.strip() and not line.strip().startswith('#')]),
            "comment_lines": len([line for line in lines if line.strip().startswith('#')]),
            "blank_lines": len([line for line in lines if not line.strip()]),
            "avg_line_length": sum(len(line) for line in lines) / len(lines) if lines else 0
        }
        
        # Language-specific analysis
        if language.lower() == "python":
            analysis.update(_analyze_python_quality_internal(code))
        elif language.lower() == "rust":
            analysis.update(_analyze_rust_quality_internal(code))
        elif language.lower() in ["javascript", "typescript"]:
            analysis.update(_analyze_js_quality_internal(code))
        else:
            analysis.update(_analyze_generic_quality_internal(code))
        
        # Calculate overall score
        analysis["overall_score"] = _calculate_quality_score_internal(analysis)
        
        return {
            "status": "success",
            "analysis": analysis,
            "message": f"Code quality analysis completed for {language}"
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error analyzing code quality: {str(e)}",
            "analysis": None
        }


def detect_security_issues(code: str, language: str = "auto") -> dict:
    """
    Detect potential security vulnerabilities in code.
    
    Args:
        code (str): The source code to analyze
        language (str): Programming language
    
    Returns:
        dict: Security analysis results
    """
    # ALL IMPORTS MUST BE INSIDE THE FUNCTION FOR LETTA
    import re
    
    def _detect_language_security_internal(code: str) -> str:
        """Auto-detect programming language from code content"""
        code_lower = code.lower()
        
        # Rust indicators
        if any(keyword in code for keyword in ['fn ', 'let ', 'mut ', 'impl ', 'struct ', 'enum ', 'match ']):
            return "rust"
        
        # Python indicators
        if any(keyword in code for keyword in ['def ', 'import ', 'from ', 'class ', '__init__']):
            return "python"
        
        # JavaScript/TypeScript indicators
        if any(keyword in code for keyword in ['function ', 'const ', 'let ', 'var ', '=>', 'console.log']):
            return "javascript"
        
        return "unknown"

    def _calculate_risk_level_internal(severity_counts: dict) -> str:
        """Calculate overall risk level from security issues"""
        if severity_counts["critical"] > 0:
            return "CRITICAL"
        elif severity_counts["high"] > 2:
            return "HIGH"
        elif severity_counts["high"] > 0 or severity_counts["medium"] > 3:
            return "MEDIUM"
        elif severity_counts["medium"] > 0 or severity_counts["low"] > 0:
            return "LOW"
        else:
            return "MINIMAL"
    
    try:
        if language == "auto":
            language = _detect_language_security_internal(code)
        
        security_issues = []
        severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        
        # Common security patterns across languages
        patterns = [
            (r'password\s*=\s*["\'][^"\']*["\']', "hardcoded_password", "critical", "Hardcoded password detected"),
            (r'api_key\s*=\s*["\'][^"\']*["\']', "hardcoded_api_key", "high", "Hardcoded API key detected"),
            (r'eval\s*\(', "code_injection", "critical", "Use of eval() function - code injection risk"),
            (r'exec\s*\(', "code_execution", "critical", "Use of exec() function - arbitrary code execution"),
            (r'system\s*\(', "command_injection", "high", "System command execution - injection risk"),
            (r'subprocess\.call\s*\(', "subprocess_risk", "medium", "Subprocess call - validate inputs"),
            (r'open\s*\(["\'][^"\']*["\'].*["\']w["\']', "file_write", "medium", "File write operation - validate paths"),
            (r'sql.*\+.*\+', "sql_injection", "high", "Potential SQL injection - use parameterized queries"),
        ]
        
        # Language-specific security checks
        if language.lower() == "rust":
            patterns.extend([
                (r'unsafe\s*\{', "unsafe_block", "high", "Unsafe block - ensure memory safety"),
                (r'transmute\s*\(', "transmute_usage", "medium", "Memory transmute - verify type safety"),
                (r'ptr::', "raw_pointer", "medium", "Raw pointer usage - ensure safety"),
            ])
        elif language.lower() == "python":
            patterns.extend([
                (r'pickle\.loads?\s*\(', "pickle_security", "high", "Pickle deserialization - untrusted data risk"),
                (r'input\s*\(', "input_validation", "low", "User input - validate and sanitize"),
                (r'os\.system\s*\(', "os_system", "critical", "OS system call - command injection risk"),
            ])
        
        # Scan for patterns
        for pattern, issue_type, severity, description in patterns:
            matches = re.finditer(pattern, code, re.IGNORECASE)
            for match in matches:
                line_num = code[:match.start()].count('\n') + 1
                security_issues.append({
                    "type": issue_type,
                    "severity": severity,
                    "description": description,
                    "line": line_num,
                    "code_snippet": match.group(0)
                })
                severity_counts[severity] += 1
        
        return {
            "status": "success",
            "security_analysis": {
                "language": language,
                "issues_found": len(security_issues),
                "issues": security_issues,
                "severity_breakdown": severity_counts,
                "risk_level": _calculate_risk_level_internal(severity_counts)
            },
            "message": f"Security analysis completed - found {len(security_issues)} potential issues"
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error detecting security issues: {str(e)}",
            "security_analysis": None
        }


def suggest_improvements(code: str, language: str = "auto", focus_area: str = "all") -> dict:
    """
    Suggest specific improvements for the code.
    
    Args:
        code (str): The source code to improve
        language (str): Programming language
        focus_area (str): Focus area (performance, readability, security, all)
    
    Returns:
        dict: Improvement suggestions
    """
    def _detect_language_suggestions_internal(code: str) -> str:
        """Auto-detect programming language from code content"""
        code_lower = code.lower()
        
        # Rust indicators
        if any(keyword in code for keyword in ['fn ', 'let ', 'mut ', 'impl ', 'struct ', 'enum ', 'match ']):
            return "rust"
        
        # Python indicators
        if any(keyword in code for keyword in ['def ', 'import ', 'from ', 'class ', '__init__']):
            return "python"
        
        # JavaScript/TypeScript indicators
        if any(keyword in code for keyword in ['function ', 'const ', 'let ', 'var ', '=>', 'console.log']):
            return "javascript"
        
        return "unknown"

    def _suggest_readability_improvements_internal(code: str, language: str):
        """Suggest readability improvements"""
        suggestions = []
        
        lines = code.split('\n')
        
        # Long line check
        long_lines = [i+1 for i, line in enumerate(lines) if len(line) > 100]
        if long_lines:
            suggestions.append({
                "category": "readability",
                "type": "line_length",
                "description": f"Consider breaking long lines (lines {', '.join(map(str, long_lines[:3]))}{'...' if len(long_lines) > 3 else ''})",
                "priority": "medium",
                "effort": "low"
            })
        
        # Nested complexity
        max_indent = max((len(line) - len(line.lstrip()) for line in lines if line.strip()), default=0)
        if max_indent > 16:
            suggestions.append({
                "category": "readability",
                "type": "complexity",
                "description": "Consider extracting nested logic into separate functions",
                "priority": "high",
                "effort": "medium"
            })
        
        return suggestions

    def _suggest_performance_improvements_internal(code: str, language: str):
        """Suggest performance improvements"""
        suggestions = []
        
        if language == "python":
            if '+ ""' in code or '+ str(' in code:
                suggestions.append({
                    "category": "performance",
                    "type": "string_operations",
                    "description": "Consider using f-strings or .join() for string concatenation",
                    "priority": "medium",
                    "effort": "low"
                })
        
        elif language == "rust":
            if '.clone()' in code:
                suggestions.append({
                    "category": "performance",
                    "type": "unnecessary_clones",
                    "description": "Review .clone() usage - consider borrowing instead",
                    "priority": "medium",
                    "effort": "medium"
                })
        
        return suggestions

    def _suggest_security_improvements_internal(code: str, language: str):
        """Suggest security improvements"""
        suggestions = []
        
        if 'password' in code.lower() and '=' in code:
            suggestions.append({
                "category": "security",
                "type": "credentials",
                "description": "Use environment variables or secure vaults for credentials",
                "priority": "critical",
                "effort": "low"
            })
        
        return suggestions

    def _suggest_structural_improvements_internal(code: str, language: str):
        """Suggest structural improvements"""
        suggestions = []
        
        lines = code.split('\n')
        if len(lines) > 200:
            suggestions.append({
                "category": "structure",
                "type": "file_size",
                "description": "Consider splitting this large file into smaller modules",
                "priority": "medium",
                "effort": "high"
            })
        
        return suggestions

    def _prioritize_suggestions_internal(suggestions):
        """Sort suggestions by priority and effort"""
        priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        effort_order = {"low": 0, "medium": 1, "high": 2}
        
        return sorted(suggestions, key=lambda x: (
            priority_order.get(x.get("priority", "low"), 3),
            effort_order.get(x.get("effort", "medium"), 1)
        ))
    
    try:
        if language == "auto":
            language = _detect_language_suggestions_internal(code)
        
        suggestions = []
        
        # General improvements
        if focus_area in ["all", "readability"]:
            suggestions.extend(_suggest_readability_improvements_internal(code, language))
        
        if focus_area in ["all", "performance"]:
            suggestions.extend(_suggest_performance_improvements_internal(code, language))
        
        if focus_area in ["all", "security"]:
            suggestions.extend(_suggest_security_improvements_internal(code, language))
        
        if focus_area in ["all", "structure"]:
            suggestions.extend(_suggest_structural_improvements_internal(code, language))
        
        # Prioritize suggestions
        prioritized = _prioritize_suggestions_internal(suggestions)
        
        return {
            "status": "success",
            "improvements": {
                "language": language,
                "focus_area": focus_area,
                "total_suggestions": len(prioritized),
                "suggestions": prioritized,
                "quick_wins": [s for s in prioritized if s.get("effort") == "low"],
                "major_improvements": [s for s in prioritized if s.get("effort") == "high"]
            },
            "message": f"Generated {len(prioritized)} improvement suggestions"
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error generating suggestions: {str(e)}",
            "improvements": None
        }