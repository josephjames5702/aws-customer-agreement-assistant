import os
import json
import logging
import re
from datetime import datetime

class StructuredJSONFormatter(logging.Formatter):
    """
    Custom formatter that outputs log records as JSON strings.
    Extracts all attributes and redacts potential keys/secrets.
    """
    def format(self, record):
        log_record = {
            "timestamp": datetime.utcfromtimestamp(record.created).isoformat() + "Z",
            "level": record.levelname,
            "message": self.redact_secrets(record.getMessage()),
            "logger": record.name,
        }
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)

        # Standard logger fields to filter out of the custom extra dictionary
        standard_attrs = {
            'args', 'asctime', 'created', 'exc_info', 'exc_text', 'filename',
            'funcName', 'levelname', 'levelno', 'lineno', 'module',
            'msecs', 'message', 'msg', 'name', 'pathname', 'process',
            'processName', 'relativeCreated', 'stack_info', 'thread', 'threadName'
        }
        
        # Include custom extra fields if provided
        for key, val in record.__dict__.items():
            if key not in standard_attrs and not key.startswith('_'):
                # Avoid logging secrets if any key name looks like password/token/key/secret
                if any(secret_term in key.lower() for secret_term in ["secret", "key", "token", "password", "auth"]):
                    log_record[key] = "********"
                else:
                    if isinstance(val, str):
                        log_record[key] = self.redact_secrets(val)
                    else:
                        log_record[key] = val
                    
        return json.dumps(log_record)

    def redact_secrets(self, text: str) -> str:
        if not isinstance(text, str):
            return text
        # Redact HF API tokens
        text = re.sub(r'hf_[a-zA-Z0-9]{34}', '********', text)
        # Redact generic authorization bearer tokens or API key lookalikes
        text = re.sub(r'(?i)(bearer\s+|api[-_]?key\s*[:=]\s*|token\s*[:=]\s*)[a-zA-Z0-9_\-\.\+\=\/]{16,}', r'\1********', text)
        return text

def setup_logging():
    # Create logs directory if not exists
    os.makedirs("logs", exist_ok=True)
    
    # Configure root logger
    root_logger = logging.getLogger()
    # Clear existing handlers
    root_logger.handlers = []
    root_logger.setLevel(logging.INFO)
    
    formatter = StructuredJSONFormatter()
    
    # File Handler
    file_handler = logging.FileHandler("logs/app.log", encoding="utf-8")
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)
    
    # Console Handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)
    root_logger.addHandler(console_handler)

# Initialize logging configuration immediately on import
setup_logging()
logger = logging.getLogger("app")
