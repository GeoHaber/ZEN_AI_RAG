try:
    print("Importing config_system...")
    import config_system

    print("Importing utils...")
    import utils

    print("Importing nicegui...")
    from nicegui import ui, app

    print("Importing logging...")
    import logging

    print("Imports OK.")
except Exception as e:
    print(f"IMPORT ERROR: {e}")
    import traceback

    traceback.print_exc()
