

import os
import sys
import logging
import traceback
from datetime import datetime
from typing import Optional, Dict, Any, Union

# Default logging format
DEFAULT_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
DEFAULT_LOG_LEVEL = logging.INFO

# Log directory
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")

def ensure_log_dir():
    """Ensure the log directory exists."""
    if not os.path.exists(LOG_DIR):
        try:
            os.makedirs(LOG_DIR)
        except Exception as e:
            print(f"Warning: Failed to create log directory: {e}")

def get_file_handler(log_file: str, level: int = DEFAULT_LOG_LEVEL, 
                    format_str: str = DEFAULT_FORMAT, 
                    date_format: str = DEFAULT_DATE_FORMAT) -> logging.FileHandler:
    """
    Get a file handler for logging.
    
    Args:
        log_file: The name of the log file
        level: The logging level
        format_str: The logging format string
        date_format: The date format string
        
    Returns:
        A configured file handler
    """
    ensure_log_dir()
    log_path = os.path.join(LOG_DIR, log_file)
    handler = logging.FileHandler(log_path)
    handler.setLevel(level)
    formatter = logging.Formatter(format_str, date_format)
    handler.setFormatter(formatter)
    return handler

def get_console_handler(level: int = DEFAULT_LOG_LEVEL, 
                       format_str: str = DEFAULT_FORMAT,
                       date_format: str = DEFAULT_DATE_FORMAT) -> logging.StreamHandler:
    """
    Get a console handler for logging.
    
    Args:
        level: The logging level
        format_str: The logging format string
        date_format: The date format string
        
    Returns:
        A configured stream handler
    """
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    formatter = logging.Formatter(format_str, date_format)
    handler.setFormatter(formatter)
    return handler

def configure_logger(name: str, 
                   level: int = DEFAULT_LOG_LEVEL, 
                   log_to_file: bool = True,
                   log_to_console: bool = True,
                   log_file: Optional[str] = None,
                   format_str: str = DEFAULT_FORMAT,
                   date_format: str = DEFAULT_DATE_FORMAT) -> logging.Logger:
    """
    Configure a logger with the specified settings.
    
    Args:
        name: The name of the logger
        level: The logging level
        log_to_file: Whether to log to a file
        log_to_console: Whether to log to the console
        log_file: The name of the log file (defaults to name.log)
        format_str: The logging format string
        date_format: The date format string
        
    Returns:
        A configured logger
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Remove existing handlers if any
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Add file handler if requested
    if log_to_file:
        if log_file is None:
            log_file = f"{name.lower().replace('.', '_')}.log"
        file_handler = get_file_handler(log_file, level, format_str, date_format)
        logger.addHandler(file_handler)
    
    # Add console handler if requested
    if log_to_console:
        console_handler = get_console_handler(level, format_str, date_format)
        logger.addHandler(console_handler)
    
    return logger

def configure_app_logging(app_name: str, 
                         log_level: int = DEFAULT_LOG_LEVEL,
                         modules: Optional[Dict[str, int]] = None) -> Dict[str, logging.Logger]:
    """
    Configure logging for an entire application.
    
    Args:
        app_name: The name of the application
        log_level: The default logging level
        modules: A dictionary mapping module names to logging levels
        
    Returns:
        A dictionary mapping module names to configured loggers
    """
    ensure_log_dir()
    
    # Configure root logger
    root_logger = configure_logger(
        app_name, 
        level=log_level,
        log_file=f"{app_name.lower()}.log"
    )
    
    loggers = {app_name: root_logger}
    
    # Configure module loggers
    if modules:
        for module_name, module_level in modules.items():
            logger = configure_logger(
                f"{app_name}.{module_name}",
                level=module_level,
                log_file=f"{app_name.lower()}_{module_name.lower()}.log"
            )
            loggers[module_name] = logger
    
    return loggers

def log_exception(logger: logging.Logger, e: Exception, context: str = ""):
    """
    Log an exception with detailed traceback and context.
    
    Args:
        logger: The logger to use
        e: The exception to log
        context: Additional context to include in the log message
    """
    error_message = f"Exception: {str(e)}"
    if context:
        error_message = f"{context} - {error_message}"
    
    logger.error(error_message)
    logger.error(traceback.format_exc())

class RequestLogger:
    """
    Context manager for logging requests and responses.
    
    Example:
        with RequestLogger(logger, "API Request") as req_log:
            response = requests.get("https://api.example.com/endpoint")
            req_log.response = response
    """
    def __init__(self, logger: logging.Logger, context: str = ""):
        self.logger = logger
        self.context = context
        self.start_time = None
        self.response = None
        
    def __enter__(self):
        self.start_time = datetime.now()
        if self.context:
            self.logger.info(f"Starting {self.context}")
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = (datetime.now() - self.start_time).total_seconds()
        
        if exc_type is not None:
            self.logger.error(f"{self.context} failed after {duration:.2f}s: {exc_val}")
            return False
        
        if self.response:
            self.logger.info(f"{self.context} completed in {duration:.2f}s with status {getattr(self.response, 'status_code', 'unknown')}")
            
        return True
