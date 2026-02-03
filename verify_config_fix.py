
from config_system import config, LanguageConfig
import sys

print(f"Config loaded. Language type: {type(config.language)}")
if isinstance(config.language, LanguageConfig):
    print(f"SUCCESS: config.language is LanguageConfig, ui_language={config.language.ui_language}")
else:
    print(f"FAILURE: config.language is {type(config.language)}")
    sys.exit(1)

print(f"Appearance type: {type(config.appearance)}")
print(f"AI Model default: {config.ai_model.default_model}")
