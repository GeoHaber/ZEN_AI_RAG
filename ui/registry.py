# -*- coding: utf-8 -*-
"""
ui/registry.py - Centralized UI Interaction Registry
Defines the IDs for all interactive elements to prevent dead links
and enable automatic chaos/monkey testing.
"""


class UI_IDS:
    """UI_IDS class."""

    # --- Sidebar / Drawer ---
    BTN_NEW_CHAT = "ui-btn-new-chat"
    BTN_SETTINGS = "ui-btn-settings"
    BTN_SCAN_KB = "ui-btn-scan-kb"
    BTN_EVAL_JUDGE = "ui-btn-eval-judge"
    SW_DARK_MODE = "ui-sw-dark-mode"
    EXP_RAG_SOURCES = "ui-exp-rag-sources"
    BTN_START_TOUR = "ui-btn-start-tour"

    # --- Chat Input ---
    INPUT_CHAT = "ui-input-chat"
    BTN_SEND = "ui-btn-send"
    BTN_VOICE = "ui-btn-voice"
    BTN_ATTACH = "ui-btn-attach"

    # --- Settings Dialog ---
    SET_LANGUAGE = "ui-set-language"
    SET_DARK_MODE = "ui-set-dark-mode"
    SET_FONT_SIZE = "ui-set-font-size"
    SET_SWARM_COT = "ui-set-swarm-cot"
    SET_TTS_ENABLE = "ui-set-tts-enable"
    SET_RAG_ENABLE = "ui-set-rag-enable"
    BTN_SET_SAVE = "ui-btn-set-save"
    BTN_SET_RESET = "ui-btn-set-reset"

    # --- Model / System Dialogs ---
    BTN_DOWNLOAD_MODEL = "ui-btn-download-model"
    BTN_UPDATE_ENGINE = "ui-btn-update-engine"
    BTN_CLOSE_DIALOG = "ui-btn-close-dialog"
    BTN_SWARM = "ui-btn-swarm-manager"
    BTN_SCAN = "ui-btn-scan-trigger"
    BTN_JUDGE = "ui-btn-intelligence-judge"

    # --- Batch Analysis ---
    BTN_BATCH_MENU = "ui-btn-batch-menu"
    BTN_BATCH_START = "ui-btn-batch-start"
    INPUT_BATCH_FILES = "ui-input-batch-files"
    EXP_BATCH_STATUS = "ui-exp-batch-status"


# Metadata map for the LLM to understand what each ID does
UI_METADATA = {
    UI_IDS.BTN_NEW_CHAT: "Clear chat history and start a fresh conversation.",
    UI_IDS.BTN_SETTINGS: "Open the main configuration and user preferences dialog.",
    UI_IDS.BTN_SCAN_KB: "Manual trigger to scan and index the knowledge base.",
    UI_IDS.BTN_EVAL_JUDGE: "Open the Intelligence Judge to run benchmarks.",
    UI_IDS.SW_DARK_MODE: "Toggle the application color theme between light and dark.",
    UI_IDS.BTN_VOICE: "Initialize voice recording for speech-to-text input.",
    UI_IDS.BTN_BATCH_MENU: "Expand the Batch Analysis and Code Review section.",
    UI_IDS.BTN_BATCH_START: "Start a background analysis job for the selected files.",
    UI_IDS.BTN_CLOSE_DIALOG: "Close the currently active modal or dialog window.",
    UI_IDS.BTN_SWARM: "Open the Swarm Control Center.",
    UI_IDS.BTN_SCAN: "Manual trigger for RAG scanning.",
    UI_IDS.BTN_JUDGE: "Open the Intelligence Judge quality tab.",
    UI_IDS.BTN_START_TOUR: "Start the interactive guided tour.",
}

# List of all IDs that should be "poked" during a monkey test
MONKEY_TARGETS = list(UI_METADATA.keys())
