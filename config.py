# config.py
import os
import json
import pandas as pd

# --- CONFIGURATIONS & DIRECTORIES ---
PERMIT_DB = 'database/permits.csv'
HAZARDS_DB = 'database/hazards.json'
CHECKPOINTS_DB = 'database/checkpoints.json' 
PERSONNEL_DB = 'database/personnel.json'
CONTRACTORS_DB = 'database/contractors.json'
LOCATIONS_DB = 'database/locations.json'

UPLOAD_FOLDER = 'static/uploads'
PERMIT_FOLDER = 'static/permits'
SIGNATURE_FOLDER = 'static/signatures'
SIGNATURE_DIR = "static/saved_signatures"

# Default Data
DEFAULT_PERSONNEL = {
    "Issuer": [{"name": "Alice Smith", "email": "alice.smith@example.com"}],
    "HSE Reviewer": [{"name": "Bob Jones", "email": "bob.jones@example.com"}],
    "Approver": [{"name": "Charlie Brown", "email": "charlie.b@example.com"}]
}
DEFAULT_CONTRACTORS = {
    "ABC Construction": [{"name": "John Doe", "email": "john.doe@abc.com"}, {"name": "Jane Smith", "email": "jane.smith@abc.com"}],
    "XYZ Engineering": [{"name": "Mike Johnson", "email": "mike.j@xyz.com"}]
}
DEFAULT_LOCATIONS = ["Plant A", "Zone 5", "Offshore Platform"]
DEFAULT_HAZARDS = {
    "Hot Work": [{"hazard": "Fire / Explosion", "control": "Fire extinguishers available and inspected"}],
    "Confined Space": [{"hazard": "Oxygen Deficiency", "control": "Continuous gas monitoring"}]
}
DEFAULT_CHECKPOINTS = {
    "Confined Space": [{"checkpoint_text": "Confined Space Entry Permit approved by authorized person"}]
}

def initialize_system():
    """Creates directories and initializes databases if they don't exist."""
    for folder in [UPLOAD_FOLDER, PERMIT_FOLDER, SIGNATURE_FOLDER, SIGNATURE_DIR, 'database']:
        os.makedirs(folder, exist_ok=True)

    if not os.path.exists(PERMIT_DB):
        pd.DataFrame(columns=[
            "permit_id", "contractor", "work_description", "type", "location", "status", "requestor_name", "requestor_email",
            "start_date", "start_time", "end_date", "end_time", "issuer", "hse_reviewer", "approver",               
            "gas_test_img", "hazards_json", "checkpoints_json", "issuer_comments", "hse_comments", "approver_comments",
            "issuer_time", "hse_time", "approver_time", "issuer_sign", "hse_sign", "approver_sign"
        ]).to_csv(PERMIT_DB, index=False)
    else:
        df = pd.read_csv(PERMIT_DB)
        new_cols = ["contractor", "work_description", "issuer_comments", "hse_comments", "approver_comments", "issuer_time", "hse_time", "approver_time", "issuer_sign", "hse_sign", "approver_sign"]
        for col in new_cols:
            if col not in df.columns:
                df[col] = ""
        df.to_csv(PERMIT_DB, index=False)

    def init_json(db_path, default_data):
        if not os.path.exists(db_path):
            with open(db_path, 'w') as f:
                json.dump(default_data, f, indent=4)

    init_json(PERSONNEL_DB, DEFAULT_PERSONNEL)
    init_json(CONTRACTORS_DB, DEFAULT_CONTRACTORS)
    init_json(LOCATIONS_DB, DEFAULT_LOCATIONS)
    init_json(HAZARDS_DB, DEFAULT_HAZARDS)
    init_json(CHECKPOINTS_DB, DEFAULT_CHECKPOINTS)