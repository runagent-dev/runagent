import logging
import asyncio
from datetime import datetime
from typing import Optional, List, Dict, Any, Callable


class DatabaseLogHandler(logging.Handler):
    """Custom logging handler that sends logs to local database and middleware - FIXED VERSION"""
    
    def __init__(self, db_service, agent_id: str, middleware_sync=None, sync_check_callback: Callable = None):
        super().__init__()
        self.db_service = db_service
        self.agent_id = agent_id 
        self.middleware_sync = middleware_sync
        self.log_buffer: List[Dict[str, Any]] = []
        self.max_buffer_size = 10
        self.sync_enabled = (
            middleware_sync and 
            hasattr(middleware_sync, 'is_sync_enabled') and 
            middleware_sync.is_sync_enabled()
        )
        
        # NEW: Callback to check if agent is synced to middleware
        self.sync_check_callback = sync_check_callback
                
    def emit(self, record):
        """Handle log emission to both local database and middleware - FIXED VERSION"""
        try:
            # Format the log message
            formatted_message = self.format(record)
            
            # ALWAYS store in local database first
            try:
                self.db_service.record_agent_log(
                    agent_id=self.agent_id,
                    log_level=record.levelname,
                    message=formatted_message,
                    execution_id=getattr(record, 'execution_id', None)
                )
            except Exception as log_error:
                # If local logging fails, print to console as fallback
                print(f"Local log storage failed: {log_error}")
            
            # Only try middleware sync if conditions are met
            if self._should_sync_to_middleware():
                log_entry = {
                    'agent_id': self.agent_id,
                    'log_level': record.levelname,
                    'message': formatted_message,
                    'execution_id': getattr(record, 'execution_id', None),
                    'timestamp': datetime.fromtimestamp(record.created)
                }
                
                self.log_buffer.append(log_entry)
                
                # Send buffered logs when buffer is full or on ERROR/CRITICAL
                if (len(self.log_buffer) >= self.max_buffer_size or 
                    record.levelno >= logging.ERROR):
                    self._flush_logs_to_middleware()
                    
        except Exception as e:
            # Don't let logging errors break the application
            print(f"Log handler error: {e}")
    
    def _should_sync_to_middleware(self) -> bool:
        """Check if we should sync to middleware"""
        if not self.sync_enabled:
            return False
        
        if self.sync_check_callback:
            try:
                agent_synced = self.sync_check_callback()
                if not agent_synced:
                    # Agent not synced yet, don't try to send logs
                    return False
            except Exception:
                # If callback fails, don't sync
                return False
        
        return True
    
    def _flush_logs_to_middleware(self):
        """Send buffered logs to middleware"""
        if not self.log_buffer:
            return
            
        # Double-check sync conditions
        if not self._should_sync_to_middleware():
            print(f"Skipping middleware sync - agent not ready (buffer: {len(self.log_buffer)} logs)")
            # Keep logs in buffer for later
            return
            
        try:
            # Create a copy of buffer and clear it immediately
            logs_to_sync = self.log_buffer.copy()
            self.log_buffer.clear()
            
            print(f"🔍 Flushing {len(logs_to_sync)} logs to middleware for agent_id: {self.agent_id}")
            
            # Try to sync logs asynchronously
            if hasattr(self.middleware_sync, 'sync_agent_logs'):
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # If we're in an async context, schedule for later
                        asyncio.create_task(
                            self.middleware_sync.sync_agent_logs(logs_to_sync)
                        )
                    else:
                        # Run in the current loop
                        loop.run_until_complete(
                            self.middleware_sync.sync_agent_logs(logs_to_sync)
                        )
                except RuntimeError:
                    # No event loop, create a new one
                    asyncio.run(self.middleware_sync.sync_agent_logs(logs_to_sync))
                except Exception as e:
                    print(f"Middleware log sync failed: {e}")
                    # Put logs back in buffer for retry
                    self.log_buffer.extend(logs_to_sync)
            
        except Exception as e:
            print(f"Error flushing logs to middleware: {e}")
            # Put logs back in buffer for retry
            self.log_buffer.extend(logs_to_sync)
    
    def force_flush(self):
        """Force flush all remaining logs - only if agent is synced"""
        if self.log_buffer and self._should_sync_to_middleware():
            print(f"🔍 Force flushing {len(self.log_buffer)} remaining logs for agent_id: {self.agent_id}")
            self._flush_logs_to_middleware()
        elif self.log_buffer:
            print(f"🔍 Keeping {len(self.log_buffer)} logs local - agent not synced to middleware")
    
    def close(self):
        """Close handler and flush remaining logs"""
        self.force_flush()
        super().close()