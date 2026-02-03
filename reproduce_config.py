
from config_system import AppConfig, LanguageConfig
import json
import os

# Mock settings.json
with open('settings_test.json', 'w') as f:
    json.dump({"language": {"ui_language": "ro"}}, f)

# Patch SETTINGS_JSON path temporarily
import config_system
config_system.SETTINGS_JSON = config_system.BASE_DIR / 'settings_test.json'

config = AppConfig.load()
print(f"Type of config.language: {type(config.language)}")
if isinstance(config.language, dict):
    print("FAILURE: config.language is a dict!")
else:
    print(f"SUCCESS: config.language is {config.language}")
    print(f"Access check: {config.language.ui_language}")
