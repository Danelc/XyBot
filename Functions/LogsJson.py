import json
import os
import shutil
import logging
import logging.handlers

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.handlers.RotatingFileHandler("logs/XyBot.log", maxBytes=5*1024*1024, backupCount=5),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("XyBot")

def json_read(path):
    file_path = f"{path}.json"
    if not os.path.exists(file_path):
        # Create the file by copying from the default_files directory
        default_file_path = f"default_files/{os.path.basename(file_path)}"
        if os.path.exists(default_file_path):
            shutil.copy(default_file_path, file_path)
            logger.warning(f"Default file '{default_file_path}' used to create '{file_path}' as it was not found.")
        else:
            raise FileNotFoundError(f"Default file {default_file_path} not found.")
    
    with open(file_path, "r") as f:
        data = json.load(f)
    return data

def json_write(data, path):
    file_path = f"{path}.json"
    if not os.path.exists(file_path):
        default_file_path = f"default_files/{os.path.basename(file_path)}"
        if os.path.exists(default_file_path):
            shutil.copy(default_file_path, file_path)
            logger.warning(f"Default file '{default_file_path}' used to create '{file_path}' as it was not found.")
        else:
            raise FileNotFoundError(f"Default file '{default_file_path}' not found.")
    with open(file_path, "w") as f:
        data_json = json.dumps(data, indent=2)
        f.write(data_json)