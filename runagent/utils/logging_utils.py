"""Utility functions for controlling log verbosity"""
import os
from typing import Optional

def is_verbose_logging_enabled(debug_mode: Optional[bool] = None) -> bool:
    """
    Check if verbose logging should be enabled.
    
    Verbose logging is enabled when:
    - DISABLE_TRY_CATCH environment variable is set
    - debug_mode is explicitly True
    
    Args:
        debug_mode: Optional debug mode flag (typically from LocalServer.debug)
        
    Returns:
        True if verbose logging should be enabled, False otherwise
    """
    # Check environment variable first
    if os.getenv('DISABLE_TRY_CATCH'):
        return True
    
    # Check debug mode if provided
    if debug_mode is True:
        return True
    
    return False
