import logging
from logging.config import dictConfig
import os

os.makedirs("logs", exist_ok=True)

dictConfig(
    {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "[%(asctime)s] %(levelname)s %(filename)s %(funcName)s() > %(message)s",
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
                "formatter": "default",
            },
            "appLogs": {
                "class": "logging.handlers.RotatingFileHandler",
                "filename": "logs/appLogs.log",
                "maxBytes": 1000000,
                "backupCount": 10,
                "formatter": "default",
                "encoding": "utf-8"
            }
        },
        "loggers": {
            "appLogs": {
                "level": "INFO",
                "handlers": ["console", "appLogs"],
            },
        },
    }
)

logger = logging.getLogger("appLogs")