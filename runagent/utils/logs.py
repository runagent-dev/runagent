# runagent/utils/logs.py - ENHANCED with debug logging

import logging
import asyncio
from datetime import datetime
from typing import Optional, List, Dict, Any


class DatabaseLogHandler(logging.Handler):
    """Custom logging handler that sends logs to local database and middleware"""
    
    def __init__(self, db_service, agent_id: str, middleware_sync=None):
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
        
        # DEBUG: Print the agent ID being used
        print(f"🔍 DatabaseLogHandler initialized with agent_id: {self.agent_id}")
        
    def emit(self, record):
        """Handle log emission to both local database and middleware"""
        try:
            # Format the log message
            formatted_message = self.format(record)
            
            # Store in local database
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
            
            # If middleware sync is enabled, buffer the log
            if self.sync_enabled:
                log_entry = {
                    'agent_id': self.agent_id,  # Make sure we're using the correct agent_id
                    'log_level': record.levelname,
                    'message': formatted_message,
                    'execution_id': getattr(record, 'execution_id', None),
                    'timestamp': datetime.fromtimestamp(record.created)
                }
                
                self.log_buffer.append(log_entry)
                
                # DEBUG: Print agent ID being buffered
                if len(self.log_buffer) == 1:  # First log in buffer
                    print(f"🔍 Buffering log for agent_id: {self.agent_id}")
                
                # Send buffered logs when buffer is full or on ERROR/CRITICAL
                if (len(self.log_buffer) >= self.max_buffer_size or 
                    record.levelno >= logging.ERROR):
                    self._flush_logs_to_middleware()
                    
        except Exception as e:
            # Don't let logging errors break the application
            print(f"Log handler error: {e}")
    
    def _flush_logs_to_middleware(self):
        """Send buffered logs to middleware"""
        if not self.log_buffer or not self.sync_enabled:
            return
            
        try:
            # Create a copy of buffer and clear it immediately
            logs_to_sync = self.log_buffer.copy()
            self.log_buffer.clear()
            
            # DEBUG: Print what we're syncing
            print(f"🔍 Flushing {len(logs_to_sync)} logs to middleware for agent_id: {self.agent_id}")
            for i, log in enumerate(logs_to_sync[:3]):  # Show first 3 logs
                print(f"   Log {i+1}: agent_id={log['agent_id']}, level={log['log_level']}")
            
            # Try to sync logs asynchronously
            if hasattr(self.middleware_sync, 'sync_agent_logs'):
                # Schedule the async sync in a new task
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
            
        except Exception as e:
            print(f"Error flushing logs to middleware: {e}")
    
    def force_flush(self):
        """Force flush all remaining logs"""
        if self.log_buffer:
            print(f"🔍 Force flushing {len(self.log_buffer)} remaining logs for agent_id: {self.agent_id}")
            self._flush_logs_to_middleware()
    
    def close(self):
        """Close handler and flush remaining logs"""
        self.force_flush()
        super().close()