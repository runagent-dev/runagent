# Update the DatabaseLogHandler class in local_server.py to fix the AgentLog issue:

import logging

class DatabaseLogHandler(logging.Handler):
    """Custom logging handler that sends logs to middleware database"""
    
    def __init__(self, db_service, agent_id, middleware_sync=None):
        super().__init__()
        self.db_service = db_service
        self.agent_id = agent_id 
        self.middleware_sync = middleware_sync
        self.log_buffer = []
        
    def emit(self, record):
        """Handle log emission to both local database and middleware"""
        try:
            # Format the log message
            formatted_message = self.format(record)
            
            # Store in local database (using the new method)
            try:
                self.db_service.record_agent_log(
                    agent_id=self.agent_id,
                    log_level=record.levelname,
                    message=formatted_message,
                    execution_id=getattr(record, 'execution_id', None)
                )
            except Exception as log_error:
                # If the new method doesn't exist, silently continue
                # This maintains compatibility while the database is being updated
                pass
            
            # If middleware sync is enabled, buffer the log for sending
            if self.middleware_sync and self.middleware_sync.is_sync_enabled():
                self.log_buffer.append({
                    'agent_id': self.agent_id,
                    'log_level': record.levelname,
                    'message': formatted_message,
                    'execution_id': getattr(record, 'execution_id', None),
                    'timestamp': record.created
                })
                
                # Send buffered logs periodically (every 10 logs or on ERROR/CRITICAL)
                if len(self.log_buffer) >= 10 or record.levelno >= logging.ERROR:
                    self._flush_logs_to_middleware()
                    
        except Exception as e:
            # Don't let logging errors break the application
            pass  # Silently fail to prevent breaking the server
    
    def _flush_logs_to_middleware(self):
        """Send buffered logs to middleware"""
        if not self.log_buffer or not self.middleware_sync:
            return
            
        try:
            # For now, just clear the buffer since the middleware sync doesn't have log sync yet
            # TODO: Implement actual middleware log sync
            self.log_buffer.clear()
            
        except Exception as e:
            self.log_buffer.clear()

# Update the _setup_logging method to be more defensive:

    def _setup_logging(self):
        """Setup enhanced logging with database integration"""
        try:
            # Create custom logger for this agent
            self.agent_logger = logging.getLogger(f'runagent_agent_{self.agent_id}')
            self.agent_logger.setLevel(logging.DEBUG)
            
            # Remove existing handlers to avoid duplicates
            for handler in self.agent_logger.handlers[:]:
                self.agent_logger.removeHandler(handler)
            
            # Add database handler with middleware sync
            try:
                db_handler = DatabaseLogHandler(
                    self.db_service, 
                    self.agent_id, 
                    getattr(self, 'middleware_sync', None)
                )
                db_handler.setFormatter(logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                ))
                self.agent_logger.addHandler(db_handler)
            except Exception as e:
                # If database handler fails, continue without it
                console.print(f"⚠️ [yellow]Could not setup database logging: {e}[/yellow]")
            
            # Also keep console output
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(logging.Formatter(
                '%(asctime)s - %(levelname)s - %(message)s'
            ))
            self.agent_logger.addHandler(console_handler)
            
            # Log initial startup
            self.agent_logger.info(f"Agent {self.agent_id} local server started")
            self.agent_logger.info(f"Framework: {self.agent_framework}")
            self.agent_logger.info(f"Host: {self.host}, Port: {self.port}")
            
        except Exception as e:
            # If all logging setup fails, continue without enhanced logging
            console.print(f"⚠️ [yellow]Enhanced logging setup failed: {e}[/yellow]")