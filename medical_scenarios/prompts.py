"""
Predefined prompts for real-case medical scenarios.
Used by run_queries_report.py to drive RAG + optional LLM.
"""

# Real-case style prompts that the indexed medical scenarios should support
MEDICAL_PROMPTS = [
    "What are the recommended steps for hand hygiene before patient contact?",
    "When should a patient be referred to the emergency department?",
    "What information must be documented when admitting a patient?",
    "How should medication allergies be recorded and communicated?",
    "What are the standard precautions for infection control?",
    "What must be included in a discharge summary?",
    "How should vital signs monitoring and escalation be performed?",
]

# Short IDs for report lines
PROMPT_IDS = [
    "hand_hygiene",
    "emergency_referral",
    "admission_documentation",
    "medication_allergies",
    "infection_control",
    "discharge_summary",
    "vital_signs_monitoring",
]
