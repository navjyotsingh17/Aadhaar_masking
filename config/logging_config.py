import logging, os
from datetime import datetime, timedelta

_logger_initialized = False

LOG_DIR = "logs"

def delete_old_logs(days=7):
    """
    Delete log files older than 'days' days.
    """
    now = datetime.now()

    for filename in os.listdir(LOG_DIR):
        if filename.endswith(".log"):
            filepath = os.path.join(LOG_DIR, filename)

            try:
                modified_time = datetime.fromtimestamp(os.path.getmtime(filepath))
                if now - modified_time > timedelta(days=days):
                    os.remove(filepath)
            except Exception as e:
                print(f"Unable to delete old log {filename}: {e}")


def setup_logger():
    global _logger_initialized

    if _logger_initialized:
        return logging.getLogger()

    os.makedirs(LOG_DIR, exist_ok=True)

    # Delete logs older than 7 days
    delete_old_logs(days=7)

    # Create new log file for every application run
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(LOG_DIR, f"python_app_{timestamp}.log")

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    

    logger.handlers.clear()   # Prevent duplicate handlers

    file_handler = logging.FileHandler(
        log_file,
        mode="w",
        encoding="utf-8"
    )

    formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)s in %(module)s: %(message)s"
    )

    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    _logger_initialized = True
    return logger
