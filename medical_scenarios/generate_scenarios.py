#!/usr/bin/env python3
"""
Generate medical scenario documents for RAG indexing.
Writes text files to medical_scenarios/data/.
"""

from pathlib import Path

# Project root = parent of medical_scenarios
SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

SCENARIOS = [
    {
        "id": "hand_hygiene",
        "title": "Hand Hygiene Protocol",
        "content": """
Hand hygiene before patient contact. Recommended steps:
1. Remove rings and wrist accessories.
2. Apply enough soap or alcohol-based rub to cover all hand surfaces.
3. Rub hands palm to palm, then back of hands, between fingers, and nails.
4. Minimum duration: 20 seconds for soap and water; follow product leaflet for alcohol rub.
5. Dry hands thoroughly with single-use towel or air dryer.
Perform hand hygiene before and after direct patient contact, after body fluid exposure risk, and after contact with patient surroundings.
""",
    },
    {
        "id": "emergency_referral",
        "title": "When to Refer to Emergency",
        "content": """
Refer a patient to the emergency department when:
- Acute chest pain or signs of myocardial infarction.
- Severe shortness of breath or respiratory distress.
- Suspected stroke (sudden weakness, speech difficulty, facial droop).
- Severe trauma, uncontrolled bleeding, or suspected fracture with neurovascular compromise.
- Altered consciousness, seizures, or severe headache with neurological signs.
- Suspected overdose or severe allergic reaction (anaphylaxis).
- Suicidal or homicidal ideation with intent or plan.
- Severe abdominal pain, especially with fever or vomiting blood.
When in doubt, discuss with on-call physician or use local triage guidelines.
""",
    },
    {
        "id": "admission_documentation",
        "title": "Admission Documentation Requirements",
        "content": """
On patient admission the following must be documented:
- Identity and demographic data; next of kin or emergency contact.
- Presenting complaint and history of present illness.
- Allergies and current medications (reconciliation).
- Vital signs and initial physical examination findings.
- Preliminary diagnosis and plan (investigations, treatment, level of care).
- Consent for treatment and, if applicable, consent for procedures.
- Nursing assessment and care plan.
- Time and signature of admitting clinician. All entries must be dated and signed.
""",
    },
    {
        "id": "medication_allergies",
        "title": "Recording and Communicating Medication Allergies",
        "content": """
Medication allergies must be recorded and communicated as follows:
- Document in the patient record: allergen name, reaction type (e.g. rash, anaphylaxis), and date if known.
- Enter in the pharmacy/EMR allergy module and mark as verified where possible.
- Display allergies prominently (e.g. wristband, chart cover, EHR banner).
- Re-check allergies at each encounter and before prescribing or administering any drug.
- Communicate allergies during handover and when transferring care.
- If reaction is unclear (e.g. intolerance vs allergy), document as reported and clarify with patient or family. Never dismiss an allergy without documentation.
""",
    },
    {
        "id": "infection_control",
        "title": "Standard Precautions for Infection Control",
        "content": """
Standard precautions apply to all patients regardless of diagnosis. They include:
- Hand hygiene before and after patient contact and after contact with potentially contaminated surfaces.
- Use of personal protective equipment (PPE): gloves for contact with body fluids or contaminated surfaces; gown and face protection when splash or spray is likely.
- Safe handling of sharps; no recapping; dispose in puncture-resistant containers.
- Respiratory hygiene and cough etiquette (tissue, mask if coughing).
- Environmental cleaning and disinfection of patient equipment and high-touch surfaces.
- Safe handling of linen and waste.
Transmission-based precautions (contact, droplet, airborne) are added when specific pathogens are known or suspected.
""",
    },
    # Extended content for larger index and more chunk diversity
    {
        "id": "hand_hygiene_extended",
        "title": "Hand Hygiene Protocol (Extended)",
        "content": """
Hand hygiene before patient contact is mandatory in all clinical areas. Recommended steps:
1. Remove rings and wrist accessories.
2. Apply enough soap or alcohol-based rub to cover all hand surfaces.
3. Rub hands palm to palm, then back of hands, between fingers, and nails.
4. Minimum duration: 20 seconds for soap and water; follow product leaflet for alcohol rub.
5. Dry hands thoroughly with single-use towel or air dryer.
Perform hand hygiene before and after direct patient contact, after body fluid exposure risk, and after contact with patient surroundings.
Audit and compliance monitoring are required. Training must be provided annually. Alcohol-based hand rub is preferred when hands are not visibly soiled.
""",
    },
    {
        "id": "discharge_summary",
        "title": "Discharge Summary Requirements",
        "content": """
A discharge summary must be completed for every patient leaving the hospital or care unit. It should include:
- Patient identification and admission date; discharge date and destination.
- Summary of admission diagnosis and principal diagnosis at discharge.
- Brief history of present illness and hospital course.
- Procedures performed and key investigations with results.
- Discharge medications with changes from admission; reconciliation.
- Allergies and relevant past medical history.
- Follow-up plan: appointments, referrals, pending results, patient instructions.
- Code status and advance directives if relevant.
- Signature of responsible clinician and date. Copy to primary care and patient as per policy.
""",
    },
    {
        "id": "vital_signs_monitoring",
        "title": "Vital Signs Monitoring and Escalation",
        "content": """
Vital signs (temperature, pulse, blood pressure, respiratory rate, oxygen saturation, and level of consciousness) must be monitored as per the patient's condition and local protocol. Frequency may be continuous, hourly, 4-hourly, or as prescribed. Abnormal values must be escalated using the early warning score (EWS) or equivalent: document the reading, calculate the score, and notify the responsible nurse or physician according to escalation thresholds. Critical values (e.g. systolic BP below 90 mmHg, SpO2 below 90%, GCS drop) require immediate action and documentation. Equipment must be calibrated and maintained. All readings are recorded in the patient record with time and signature.
""",
    },
    # Paraphrase / similar content to exercise cosine (near-duplicate) dedup
    {
        "id": "hand_hygiene_paraphrase",
        "title": "Hand Hygiene (Summary)",
        "content": """
Before and after patient contact, hand hygiene is required. Remove rings and wrist accessories; apply sufficient soap or alcohol-based rub to cover all hand surfaces; rub hands palm to palm, backs of hands, between fingers, and nails. At least 20 seconds for soap and water; for alcohol rub follow the product leaflet. Dry hands thoroughly with a single-use towel or air dryer. Hand hygiene is performed before and after direct patient contact, after risk of body fluid exposure, and after contact with patient surroundings. Compliance is monitored and audited.
""",
    },
]


def main():
    print("Generating medical scenario documents...")
    for s in SCENARIOS:
        path = DATA_DIR / f"{s['id']}.txt"
        text = (s["title"] + "\n\n" + s["content"].strip()).strip()
        path.write_text(text, encoding="utf-8")
        print(f"  Written: {path.name} ({len(text)} chars)")
    print(f"Done. {len(SCENARIOS)} files in {DATA_DIR}")


if __name__ == "__main__":
    main()
