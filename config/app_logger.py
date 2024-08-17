import logging
from logging.config import dictConfig
import os

# Ensure the logs directory exists
os.makedirs("logs", exist_ok=True)

# Enhanced logging configuration
dictConfig(
    {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "detailed": {
                "format": (
                    "[%(asctime)s] %(levelname)s in %(module)s: "
                    "%(message)s (Func: %(funcName)s, Line: %(lineno)d, "
                    "Thread: %(threadName)s)"
                ),
            },
            "simple": {
                "format": "[%(asctime)s] %(levelname)s: %(message)s",
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
                "formatter": "simple",
            },
            "fileHandler": {
                "class": "logging.handlers.RotatingFileHandler",
                "filename": "logs/appLogs.log",
                "maxBytes": 1000000,
                "backupCount": 10,
                "formatter": "detailed",
                "encoding": "utf-8",
            },
            "errorFileHandler": {
                "class": "logging.handlers.RotatingFileHandler",
                "filename": "logs/errorLogs.log",
                "maxBytes": 500000,
                "backupCount": 5,
                "formatter": "detailed",
                "level": "ERROR",
                "encoding": "utf-8",
            },
        },
        "loggers": {
            "appLogs": {
                "level": "DEBUG",
                "handlers": ["console", "fileHandler", "errorFileHandler"],
                "propagate": False,
            },
        },
        "root": {
            "level": "WARNING",
            "handlers": ["console", "fileHandler"],
        },
    }
)

# Get logger
logger = logging.getLogger("appLogs")
