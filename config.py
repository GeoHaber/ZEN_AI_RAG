# -*- coding: utf-8 -*-
"""
config.py - Legacy Bridge for config_system
Allows old files to 'import config' without breaking.
"""
import os
from pathlib import Path
from config_system import config, EMOJI, get_settings, is_dark_mode, set_dark_mode

# Re-export core constants for files using 'from config import ...'
BASE_DIR = config.BASE_DIR
MODEL_DIR = config.MODEL_DIR
BIN_DIR = config.BIN_DIR
LOG_FILE = config.log_file

# Add any other missing attributes that legacy code expects
# MAX_FILE_SIZE = config.MAX_FILE_SIZE
# ... etc
