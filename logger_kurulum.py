import logging
import os
from colorama import Fore, Style

def setup_logger(name):
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # Console Handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO) # Console'a sadece INFO ve üstünü bas

    # File Handler
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
        
    log_file = os.path.join(log_dir, "system.log")
    fh = logging.FileHandler(log_file, encoding='utf-8')
    fh.setLevel(logging.DEBUG) # Dosyaya her şeyi yaz

    # Formatters
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    
    # Console formatter without time but with colors
    class ColoredFormatter(logging.Formatter):
        def format(self, record):
            if record.levelno == logging.INFO:
                record.msg = f"{Fore.CYAN}{record.msg}{Style.RESET_ALL}"
            elif record.levelno == logging.WARNING:
                record.msg = f"{Fore.YELLOW}{record.msg}{Style.RESET_ALL}"
            elif record.levelno >= logging.ERROR:
                record.msg = f"{Fore.RED}{Style.BRIGHT}{record.msg}{Style.RESET_ALL}"
            return super().format(record)
            
    console_formatter = ColoredFormatter('[%(name)s] %(levelname)s: %(message)s')
    ch.setFormatter(console_formatter)

    # Add handlers
    if not logger.handlers:
        logger.addHandler(ch)
        logger.addHandler(fh)

    return logger
