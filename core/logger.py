import os
import sys
import logging
import json
from datetime import datetime
from typing import Optional
from .config import CONFIG


class StructuredFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log = {
            "time": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "module": record.name,
            "message": record.getMessage(),
        }
        if hasattr(record, "extra"):
            log["extra"] = record.extra
        if record.exc_info and record.exc_info[0]:
            log["exception"] = self.formatException(record.exc_info)
        return json.dumps(log)


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(getattr(logging, CONFIG.log_level.upper(), logging.INFO))

    fh = logging.FileHandler(
        os.path.join(CONFIG.log_dir, f"optinix_{datetime.now().strftime('%Y%m%d')}.log"),
        encoding="utf-8",
    )
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(StructuredFormatter())

    sh = logging.StreamHandler(sys.stdout)
    sh.setLevel(getattr(logging, CONFIG.log_level.upper(), logging.INFO))
    sh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))

    logger.addHandler(fh)
    logger.addHandler(sh)
    return logger


def cleanup_old_logs():
    import time
    now = time.time()
    cutoff = now - (CONFIG.log_retention_days * 86400)
    for f in os.listdir(CONFIG.log_dir):
        fp = os.path.join(CONFIG.log_dir, f)
        if os.path.isfile(fp) and f.startswith("optinix_"):
            try:
                if os.path.getmtime(fp) < cutoff:
                    os.remove(fp)
            except:
                pass
