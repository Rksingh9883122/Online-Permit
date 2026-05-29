import streamlit as st
import pandas as pd
import plotly.express as px  
import os
import ast
import smtplib
import json
import copy
from datetime import datetime
from email.message import EmailMessage
from fpdf import FPDF
from werkzeug.utils import secure_filename
import sqlite3
import secrets

# --- PAGE CONFIG ---
st.set_page_config(page_title="Digital Permit System", layout="wide")
query_params = st.query_params

open_permit_id = query_params.get("permit_id")
open_role = query_params.get("role")

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

EMAIL_ADDRESS = st.secrets["EMAIL_ADDRESS"]
EMAIL_PASSWORD = st.secrets["EMAIL_PASSWORD"]


print("File path:", PERMIT_DB)
print("File path:", HAZARDS_DB)

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PERMIT_FOLDER, exist_ok=True)
os.makedirs(SIGNATURE_FOLDER, exist_ok=True)
os.makedirs(SIGNATURE_DIR, exist_ok=True)
os.makedirs('database', exist_ok=True)

# Initialize Permits Database
if not os.path.exists(PERMIT_DB):
    pd.DataFrame(columns=[
        "permit_id", "contractor", "work_description", "type", "location", "status", "requestor_name", "requestor_email",
        "start_date", "start_time", "end_date", "end_time", 
        "issuer", "hse_reviewer", "approver",               
        "gas_test_img", "hazards_json", "checkpoints_json",
        "issuer_comments", "hse_comments", "approver_comments",
        "issuer_time", "hse_time", "approver_time",
        "issuer_sign", "hse_sign", "approver_sign"
    ]).to_csv(PERMIT_DB, index=False)
else:
    df = pd.read_csv(PERMIT_DB)
    new_cols = ["contractor", "work_description", "issuer_comments", "hse_comments", "approver_comments", "issuer_time", "hse_time", "approver_time", "issuer_sign", "hse_sign", "approver_sign"]
    for col in new_cols:
        if col not in df.columns:
            df[col] = ""
    df.to_csv(PERMIT_DB, index=False)

# --- MASTER DATABASES ---
DEFAULT_PERSONNEL = {
    "Issuer": [{"name": "Alice Smith", "email": "alice.smith@example.com"}],
    "HSE Reviewer": [{"name": "Bob Jones", "email": "bob.jones@example.com"}],
    "Approver": [{"name": "Charlie Brown", "email": "charlie.b@example.com"}]
}
if not os.path.exists(PERSONNEL_DB):
    with open(PERSONNEL_DB, 'w') as f:
        json.dump(DEFAULT_PERSONNEL, f, indent=4)
if 'personnel' not in st.session_state:
    with open(PERSONNEL_DB, 'r') as f:
        st.session_state.personnel = json.load(f)

DEFAULT_CONTRACTORS = {
    "ABC Construction": [
        {"name": "John Doe", "email": "john.doe@abc.com"},
        {"name": "Jane Smith", "email": "jane.smith@abc.com"}
    ],
    "XYZ Engineering": [
        {"name": "Mike Johnson", "email": "mike.j@xyz.com"}
    ]
}
if not os.path.exists(CONTRACTORS_DB):
    with open(CONTRACTORS_DB, 'w') as f:
        json.dump(DEFAULT_CONTRACTORS, f, indent=4)
if 'contractors' not in st.session_state:
    with open(CONTRACTORS_DB, 'r') as f:
        st.session_state.contractors = json.load(f)

DEFAULT_LOCATIONS = ["Plant A", "Zone 5", "Offshore Platform"]
if not os.path.exists(LOCATIONS_DB):
    with open(LOCATIONS_DB, 'w') as f:
        json.dump(DEFAULT_LOCATIONS, f, indent=4)
if 'locations' not in st.session_state:
    with open(LOCATIONS_DB, 'r') as f:
        st.session_state.locations = json.load(f)

DEFAULT_HAZARDS = {
    "Hot Work": [
        {"hazard": "Fire / Explosion", "control": "Fire extinguishers available and inspected"},
        {"hazard": "Burn Injuries", "control": "Use heat-resistant gloves and PPE"}
    ],
    "Confined Space": [
        {"hazard": "Oxygen Deficiency", "control": "Continuous gas monitoring"},
        {"hazard": "Toxic Gas Exposure", "control": "Pre-entry gas testing and ventilation"}
    ]
}
if not os.path.exists(HAZARDS_DB):
    with open(HAZARDS_DB, 'w') as f:
        json.dump(DEFAULT_HAZARDS, f, indent=4)
with open(HAZARDS_DB, 'r') as f:
    HAZARDS_MAP = json.load(f)

DEFAULT_CHECKPOINTS = {
    "Confined Space": [
        {"checkpoint_text": "Confined Space Entry Permit approved by authorized person"},
        {"checkpoint_text": "Atmosphere tested: Oxygen 19.5%-23.5%, LEL <10%, Toxics within limits"}
    ]
}
if not os.path.exists(CHECKPOINTS_DB):
    with open(CHECKPOINTS_DB, 'w') as f:
        json.dump(DEFAULT_CHECKPOINTS, f, indent=4)
with open(CHECKPOINTS_DB, 'r') as f:
    CHECKPOINTS_MAP = json.load(f)

# --- PDF GENERATOR ---
class PermitPDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 16)
        self.cell(0, 10, 'APPROVED WORK PERMIT', 1, 1, 'C')
        self.ln(5)
        
    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()} of {{nb}}', 0, 0, 'C')

def clean_text(text):
    if text is None or pd.isna(text):
        return ""
    return str(text).encode('latin-1', 'ignore').decode('latin-1')

def generate_permit_pdf(permit_row):
    pdf = PermitPDF()
    pdf.alias_nb_pages() 
    pdf.add_page()
    
    # Header Info
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, clean_text(f"Permit ID: {permit_row['permit_id']}"), 0, 1)
    pdf.set_font('Arial', '', 11)
    pdf.cell(0, 8, clean_text(f"Contractor: {permit_row.get('contractor', 'N/A')} | Location: {permit_row['location']}"), 0, 1)
    pdf.cell(0, 8, clean_text(f"Start: {permit_row.get('start_date', '')} {permit_row.get('start_time', '')} | End: {permit_row.get('end_date', '')} {permit_row.get('end_time', '')}"), 0, 1)
    pdf.cell(0, 8, clean_text(f"Requestor: {permit_row['requestor_name']} ({permit_row['requestor_email']})"), 0, 1)
    pdf.ln(2)
    
    # Work Description Block
    pdf.set_font('Arial', 'B', 11)
    pdf.cell(0, 8, "Work Description:", 0, 1)
    pdf.set_font('Arial', '', 11)
    pdf.multi_cell(0, 8, clean_text(f"{permit_row.get('work_description', 'N/A')}"))
    pdf.ln(5)

    # Hazards Section
    pdf.set_font('Arial', 'B', 12)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 10, "Hazards & Control Measures:", 0, 1)
    
    try:
        data = ast.literal_eval(permit_row['hazards_json'])
        for p_type, hazards in data.items():
            pdf.set_fill_color(220, 220, 220)
            pdf.set_font('Arial', 'B', 10)
            pdf.cell(0, 8, clean_text(f" TYPE: {p_type.upper()} "), 1, 1, 'L', True)
            pdf.set_font('Arial', '', 10)
            
            for hIdx, h in enumerate(hazards):
                pdf.set_text_color(255, 0, 0) 
                text = f"#{hIdx+1}. Hazard: {h['hazard']} | PIC: {h['resp_name']} ({h['resp_cell']})"
                pdf.cell(0, 8, clean_text(text), 0, 1)
                
                pdf.set_text_color(0, 0, 139) 
                pdf.set_fill_color(240, 240, 240)
                pdf.multi_cell(0, 8, clean_text(f"    Control Measure: {h['control']}"), 1, 'L', True)
                
                pdf.set_text_color(0, 0, 0) 
                pdf.ln(2)
            pdf.ln(2)
    except Exception as e:
        pdf.set_text_color(0, 0, 0)
        pdf.cell(0, 10, clean_text(f"Error loading hazards: {e}"), 1, 1)

    # Checkpoint Section
    pdf.ln(5)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, "Checkpoint Compliance:", 0, 1)
    
    try:
        checkpoints_data = ast.literal_eval(permit_row['checkpoints_json'])
        headers = ['S.No', 'Critical Checkpoint Statement', 'Response']
        widths = [10, 140, 40]
        pdf.set_font('Arial', 'B', 9)
        pdf.set_fill_color(200, 200, 200)
        for i in range(len(headers)):
            pdf.cell(widths[i], 10, headers[i], 1, 0, 'C', True)
        pdf.ln()
        
        pdf.set_font('Arial', '', 9)
        
        for p_type, section_checkpoints in checkpoints_data.items():
            pdf.set_font('Arial', 'B', 9)
            pdf.set_fill_color(245, 245, 245)
            pdf.cell(0, 8, clean_text(f"--- {p_type.upper()} ---"), 1, 1, 'L', True)
            pdf.set_font('Arial', '', 9)
            
            for hIdx, item in enumerate(section_checkpoints):
                pdf.cell(widths[0], 10, str(hIdx+1), 1, 0, 'C')
                start_x = pdf.get_x()
                start_y = pdf.get_y()
                pdf.multi_cell(widths[1], 10, clean_text(item['checkpoint_text']), 1, 'L')
                end_x = pdf.get_x()
                end_y = pdf.get_y()
                pdf.set_xy(start_x + widths[1], start_y)
                pdf.cell(widths[2], (end_y - start_y), clean_text(item['answer']), 1, 0, 'C')
                pdf.ln()
            pdf.ln(2)
    except Exception as e:
        pdf.cell(0, 10, clean_text(f"Error loading checkpoints: {e}"), 1, 1)

    # Approvals & Signatures Section
    pdf.add_page()
    pdf.set_font('Arial', 'B', 14)
    pdf.cell(0, 10, "APPROVALS & SIGNATURES", 0, 1)
    pdf.ln(5)

    def add_signature_block(role, name, comments, time_signed, sign_path):
        pdf.set_font('Arial', 'B', 11)
        pdf.cell(0, 8, clean_text(f"{role}: {name}"), 0, 1)
        pdf.set_font('Arial', '', 10)
        pdf.cell(0, 6, clean_text(f"Time Signed: {time_signed if pd.notna(time_signed) and time_signed else 'Pending'}"), 0, 1)
        pdf.multi_cell(0, 6, clean_text(f"Comments: {comments if pd.notna(comments) and comments else 'None'}"))
        
        if pd.notna(sign_path) and sign_path and os.path.exists(str(sign_path)):
            try:
                pdf.image(str(sign_path), x=15, y=pdf.get_y() + 2, h=15)
                pdf.ln(20) 
            except Exception as e:
                pdf.cell(0, 6, clean_text(f"(Could not load signature image: {e})"), 0, 1)
        else:
            pdf.ln(5)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(5)

    add_signature_block("Issuer", permit_row.get('issuer', 'N/A'), permit_row.get('issuer_comments', ''), permit_row.get('issuer_time', ''), permit_row.get('issuer_sign', ''))
    add_signature_block("HSE Reviewer", permit_row.get('hse_reviewer', 'N/A'), permit_row.get('hse_comments', ''), permit_row.get('hse_time', ''), permit_row.get('hse_sign', ''))
    add_signature_block("Final Approver", permit_row.get('approver', 'N/A'), permit_row.get('approver_comments', ''), permit_row.get('approver_time', ''), permit_row.get('approver_sign', ''))

    # Attachments Embedding Section
    pdf.add_page()
    pdf.set_font('Arial', 'B', 14)
    pdf.cell(0, 10, "ATTACHED SUPPORTING DOCUMENTS", 0, 1)
    pdf.ln(5)
    
    has_attachments = False
    try:
        checkpoints_data = ast.literal_eval(permit_row['checkpoints_json'])
        for p_type, section_checkpoints in checkpoints_data.items():
            for item in section_checkpoints:
                if 'attached_docs' in item and item['attached_docs']:
                    for doc in item['attached_docs']:
                        has_attachments = True
                        doc_path = doc['path']
                        doc_name = doc['name']
                        ext = os.path.splitext(doc_path)[1].lower()
                        
                        pdf.set_font('Arial', 'B', 10)
                        pdf.cell(0, 8, clean_text(f"Checkpoint Reference: {item['checkpoint_text'][:75]}..."), 0, 1)
                        pdf.set_font('Arial', '', 10)
                        pdf.cell(0, 8, clean_text(f"File Name: {doc_name}"), 0, 1)
                        
                        # Embed if image
                        if ext in ['.jpg', '.jpeg', '.png'] and os.path.exists(doc_path):
                            if pdf.get_y() > 240:
                                pdf.add_page()
                            try:
                                # Render as 2 x 2 inches (50.8 mm)
                                pdf.image(doc_path, x=15, w=50.8, h=50.8)
                                pdf.ln(50.8 + 5)
                            except Exception as e:
                                pdf.cell(0, 8, clean_text(f"(Error rendering image: {e})"), 0, 1)
                        else:
                            pdf.set_text_color(100, 100, 100)
                            pdf.cell(0, 8, "(This document type cannot be embedded physically. Please view external file)", 0, 1)
                            pdf.set_text_color(0, 0, 0)
                            pdf.ln(5)
                        
                        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
                        pdf.ln(5)
    except Exception as e:
         pdf.cell(0, 10, clean_text(f"Error checking attachments: {e}"), 0, 1)
         
    if not has_attachments:
        pdf.set_font('Arial', '', 11)
        pdf.cell(0, 10, "No attachments were provided for this permit.", 0, 1)

    # Revalidation Log Section
    pdf.add_page()
    pdf.set_font('Arial', 'B', 14)
    pdf.cell(0, 10, "APPROVED WORK PERMIT & REVALIDATION", 1, 1, 'C')
    pdf.ln(5)
    
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, "DAILY REVALIDATION LOG (OFFLINE)", 0, 1, 'C')
    pdf.ln(5)
    
    col_widths = [30, 30, 43, 43, 44]
    headers = ["Date", "Shift", "Issuer Sign", "HSE Sign", "Approver Sign"]
    
    pdf.set_font('Arial', 'B', 11)
    for i in range(len(headers)):
        pdf.cell(col_widths[i], 10, headers[i], 1, 0, 'C')
    pdf.ln()
    
    pdf.set_font('Arial', '', 11)
    for _ in range(7):
        for i in range(len(headers)):
            pdf.cell(col_widths[i], 15, "", 1, 0, 'C') 
        pdf.ln()

    file_path = os.path.join(PERMIT_FOLDER, f"Permit_{permit_row['permit_id']}.pdf")
    pdf.output(file_path)
    return file_path

# --- EMAIL HELPER ---
def extract_email(person_string):
    if "(" in person_string and ")" in person_string:
        return person_string.split("(")[-1].split(")")[0].strip()
    return None

def send_workflow_email(recipient_email, subject, body, pdf_path=None):
    if not recipient_email:
        return
        
    EMAIL_ADDRESS = "rksingh9883122@gmail.com"
    EMAIL_PASSWORD = "cbkw xsus zyht ryso"

    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = EMAIL_ADDRESS
    msg['To'] = recipient_email
    msg.set_content(body)

    if pdf_path and os.path.exists(pdf_path):
        with open(pdf_path, 'rb') as f:
            msg.add_attachment(f.read(), maintype='application', subtype='pdf', filename=os.path.basename(pdf_path))

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            smtp.send_message(msg)
    except Exception as e:
        print(f"Failed to send email to {recipient_email}: {e}")

def notify_cancellation(permit_row, cancelled_by_role):
    """Sends a cancellation alert to the Requestor, Issuer, HSE, and Approver."""
    permit_id = permit_row['permit_id']
    subject = f"URGENT: Work Permit #{permit_id} has been CANCELLED"
    body = f"Hello,\n\nWork Permit #{permit_id} requested by {permit_row['requestor_name']} for {permit_row['location']} has been CANCELLED/REVOKED by the {cancelled_by_role}.\n\nAll work associated with this permit must stop immediately."
    
    emails_to_notify = []
    
    req_email = permit_row.get('requestor_email')
    if req_email: emails_to_notify.append(req_email)
        
    iss_email = extract_email(permit_row.get('issuer', ''))
    if iss_email: emails_to_notify.append(iss_email)
        
    hse_email = extract_email(permit_row.get('hse_reviewer', ''))
    if hse_email: emails_to_notify.append(hse_email)
        
    app_email = extract_email(permit_row.get('approver', ''))
    if app_email: emails_to_notify.append(app_email)
    
    unique_emails = list(set(emails_to_notify))
    
    for email in unique_emails:
        send_workflow_email(email, subject, body)

# --- REUSABLE SIGNATURE UI HELPER ---
def signature_selection_ui(role_name, person_name, permit_id):
    st.markdown(f"**{role_name} Signature Selection**")
    
    safe_person_name = str(person_name).split('(')[0].strip()
    existing_sigs = [f for f in os.listdir(SIGNATURE_DIR) if f.endswith(('.png', '.jpg', '.jpeg'))]
    options = ["-- Upload New Signature --"] + existing_sigs
    choice = st.selectbox(f"Select existing signature for {safe_person_name}, or upload new:", options, key=f"sig_select_{role_name}_{permit_id}")
    
    final_signature_path = None
    
    if choice == "-- Upload New Signature --":
        uploaded_file = st.file_uploader(f"Upload new signature image", type=["png", "jpg", "jpeg"], key=f"sig_upload_{role_name}_{permit_id}")
        if uploaded_file is not None:
            file_safe_name = safe_person_name.replace(" ", "_").lower()
            file_ext = uploaded_file.name.split('.')[-1]
            new_file_name = f"{file_safe_name}_signature.{file_ext}"
            final_signature_path = os.path.join(SIGNATURE_DIR, new_file_name)
            
            with open(final_signature_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
                
            st.success(f"Signature saved permanently as {new_file_name}!")
            st.image(final_signature_path, width=150)
    else:
        final_signature_path = os.path.join(SIGNATURE_DIR, choice)
        st.info("Using previously saved signature.")
        st.image(final_signature_path, width=150)
        
    return final_signature_path

# ==========================================
#             APP NAVIGATION
# ==========================================

# AUTO REDIRECT IF LINK IS USED
if open_permit_id and open_role:
    page = "Approver Dashboard"
else:
    st.sidebar.title("Navigation")
    page = st.sidebar.radio(
        "Go to:",
        ["Request Permit", "Approver Dashboard", "Manage Personnel", "Live Dashboard"]
    )

# ==========================================
#             PAGE 1: REQUEST FORM
# ==========================================
if page == "Request Permit":
    st.title("Digital Work Permit Request")
    
    if 'permit_count' not in st.session_state:
        st.session_state.permit_count = 1

    st.subheader("1. General Information")

    contractor_list = ["Select Contractor..."] + list(st.session_state.contractors.keys())
    selected_contractor = st.selectbox("Contractor", contractor_list)

    col1, col2 = st.columns(2)
    with col1:
        if selected_contractor != "Select Contractor...":
            requestors = st.session_state.contractors.get(selected_contractor, [])
            req_names = ["Select Requestor..."] + [r['name'] for r in requestors]
            req_name = st.selectbox("Requestor Name", req_names)
        else:
            req_name = st.selectbox("Requestor Name", ["Select Contractor First..."])
            
        loc_choice = st.selectbox("Location", st.session_state.locations + ["+ Add New Location"])
        if loc_choice == "+ Add New Location":
            location = st.text_input("Enter Custom Location")
        else:
            location = loc_choice
        
    with col2:
        req_email = ""
        if selected_contractor != "Select Contractor..." and req_name not in ["Select Requestor...", "Select Contractor First..."]:
            for r in st.session_state.contractors[selected_contractor]:
                if r['name'] == req_name:
                    req_email = r['email']
                    break
        st.text_input("Requestor Email", value=req_email, disabled=True)
        
    work_description = st.text_area("Work Description", placeholder="Enter the exact scope and description of the work to be performed...")

    st.divider()

    col3, col4 = st.columns(2)
    with col3:
        start_date = st.date_input("Start Date")
        start_time = st.time_input("Start Time")
    with col4:
        end_date = st.date_input("End Date")
        end_time = st.time_input("End Time")

    st.divider()

    st.subheader("2. Permit Approving Team")
    
    def format_person_list(role):
        return ["Select a person..."] + [f"{p['name']} ({p['email']})" for p in st.session_state.personnel.get(role, [])]

    col5, col6, col7 = st.columns(3)
    with col5:
        issuer = st.selectbox("Issuer", format_person_list("Issuer"))
    with col6:
        hse_reviewer = st.selectbox("HSE Reviewer", format_person_list("HSE Reviewer"))
    with col7:
        approver = st.selectbox("Approver", format_person_list("Approver"))

    st.divider()

    st.subheader("3. Permit Types & Job Safety Analysis")
    all_permits_data = {}
    
    for i in range(st.session_state.permit_count):
        st.markdown(f"**Permit Section {i+1}**")
        
        type_key = f"type_{i}"
        hazards_state_key = f"dynamic_hazards_{i}"
        prev_type_key = f"prev_type_{i}"
        
        p_type = st.selectbox(f"Select Permit Type", [""] + list(HAZARDS_MAP.keys()), key=type_key)
        
        if p_type != st.session_state.get(prev_type_key, ""):
            st.session_state[prev_type_key] = p_type
            if p_type:
                st.session_state[hazards_state_key] = copy.deepcopy(HAZARDS_MAP[p_type])
            else:
                st.session_state[hazards_state_key] = []
        
        if p_type:
            permit_hazards = []
            st.caption(f"Hazards and Controls for {p_type} (Edit values or add new ones below)")
            
            for hIdx, item in enumerate(st.session_state[hazards_state_key]):
                st.markdown(f"**Hazard {hIdx+1}**")
                
                c1, c2, c3, c4 = st.columns([2, 2, 2, 2])
                haz_val = c1.text_input("🔴 Hazard (Red)", value=item.get('hazard', ''), key=f"edit_haz_{i}_{hIdx}")
                ctrl_val = c2.text_input("🔵 Control Measure (Blue)", value=item.get('control', ''), key=f"edit_ctrl_{i}_{hIdx}")
                resp_name = c3.text_input("PIC Name", value=item.get('resp_name', ''), key=f"pic_name_{i}_{hIdx}")
                resp_cell = c4.text_input("PIC Cell", value=item.get('resp_cell', ''), key=f"pic_cell_{i}_{hIdx}")
                
                permit_hazards.append({
                    "hazard": haz_val, "control": ctrl_val, "resp_name": resp_name, "resp_cell": resp_cell
                })
                
            all_permits_data[p_type] = permit_hazards
            
            if st.button("Add Custom Hazard Row", key=f"add_row_{i}"):
                st.session_state[hazards_state_key].append({"hazard": "", "control": "", "resp_name": "", "resp_cell": ""})
                st.rerun()

            st.markdown("---") 
            st.subheader("Checklist & Attachments")
            
            if p_type in CHECKPOINTS_MAP:
                checkpoints_for_this_type = copy.deepcopy(CHECKPOINTS_MAP[p_type])
                for hIdx, item in enumerate(checkpoints_for_this_type):
                    st.write(f"**#{hIdx+1}:** {item['checkpoint_text']}")
                    
                    c1, c2 = st.columns([1, 2])
                    with c1:
                        st.selectbox("Response", ["Yes", "No", "N/A"], key=f"ans_{i}_{hIdx}")
                    with c2:
                        st.file_uploader("Attach Supporting Documents", accept_multiple_files=True, key=f"docs_{i}_{hIdx}", type=["pdf", "jpg", "jpeg", "png", "docx"])

        st.divider()

    if st.button("Add Another Permit Section"):
        st.session_state.permit_count += 1
        st.rerun()

    # --- SUBMIT WITH SUCCESS STATE ---
    st.divider()
    
    if 'permit_submitted' not in st.session_state:
        st.session_state.permit_submitted = False

    if not st.session_state.permit_submitted:
        if st.button("Submit Permit for Approval", type="primary", use_container_width=True):
            if selected_contractor == "Select Contractor..." or req_name in ["Select Requestor...", "Select Contractor First..."] or not req_email or not all_permits_data or issuer == "Select a person..." or not location:
                st.error("Please fill in Contractor, Requestor Name, Location, select a Permit Type, and ensure an Issuer is selected.")
            else:
                permit_id = datetime.now().strftime("%Y%m%d%H%M%S")
                
                if location not in st.session_state.locations:
                    st.session_state.locations.append(location)
                    with open(LOCATIONS_DB, 'w') as f:
                        json.dump(st.session_state.locations, f, indent=4)

                PERMIT_SUBMISSION_FOLDER = os.path.join(UPLOAD_FOLDER, f"permit_{permit_id}")
                os.makedirs(PERMIT_SUBMISSION_FOLDER, exist_ok=True)

                all_permits_checkpoint_data = {}
                for i in range(st.session_state.permit_count):
                    p_type = st.session_state.get(f"type_{i}")
                    if p_type and p_type in CHECKPOINTS_MAP:
                        section_checkpoint_responses = []
                        for hIdx, item in enumerate(CHECKPOINTS_MAP[p_type]):
                            answer = st.session_state.get(f"ans_{i}_{hIdx}")
                            file_objects = st.session_state.get(f"docs_{i}_{hIdx}")
                            
                            this_checkpoint_documents = []
                            if file_objects:
                                for file_obj in file_objects:
                                    secure_name = secure_filename(file_obj.name)
                                    dest_file_path = os.path.join(PERMIT_SUBMISSION_FOLDER, secure_name)
                                    with open(dest_file_path, "wb") as f:
                                        f.write(file_obj.getbuffer())
                                    this_checkpoint_documents.append({'name': file_obj.name, 'path': dest_file_path})
                                    
                            checkpoint_response_data = {'checkpoint_text': item['checkpoint_text'], 'answer': answer, 'attached_docs': this_checkpoint_documents}
                            section_checkpoint_responses.append(checkpoint_response_data)
                        all_permits_checkpoint_data[p_type] = section_checkpoint_responses
                
                new_data = {
                    "permit_id": permit_id,
                    "contractor": selected_contractor,
                    "work_description": work_description,
                    "type": ", ".join(all_permits_data.keys()),
                    "location": location,
                    "status": "PENDING_ISSUER",
                    "requestor_name": req_name,
                    "requestor_email": req_email,
                    "start_date": str(start_date),
                    "start_time": str(start_time),
                    "end_date": str(end_date),
                    "end_time": str(end_time),
                    "issuer": issuer,
                    "hse_reviewer": hse_reviewer,
                    "approver": approver,
                    "gas_test_img": "",
                    "hazards_json": str(all_permits_data), 
                    "checkpoints_json": str(all_permits_checkpoint_data), 
                    "issuer_comments": "",
                    "hse_comments": "",
                    "approver_comments": "",
                    "issuer_time": "",
                    "hse_time": "",
                    "approver_time": "",
                    "issuer_sign": "",
                    "hse_sign": "",
                    "approver_sign": ""
                }
                
                df = pd.read_csv(PERMIT_DB)
                df = pd.concat([df, pd.DataFrame([new_data])], ignore_index=True)
                df.to_csv(PERMIT_DB, index=False)
                
                issuer_email = extract_email(issuer)
                if issuer_email:
                    subject = f"Action Required: New Work Permit #{permit_id}"
                    
                    base_url = "https://your-app-name.streamlit.app"   # 🔥 replace later

                    approval_link = f"{base_url}/?permit_id={permit_id}&role=issuer"

                    body = f"""
                Hello,

                A new Work Permit #{permit_id} has been requested.

                👉 Click below to review and approve:
                {approval_link}

                This link will directly open your approval page.

                Regards,  
                Digital PTW System
                """

                    send_workflow_email(issuer_email, subject, body)

                st.session_state.permit_submitted = True
                st.rerun()
    else:
        st.success("✅ Permit Submitted Successfully! Notification sent to the Issuer.")
        if st.button("Start New Permit Request", use_container_width=True):
            st.session_state.permit_submitted = False
            st.session_state.permit_count = 1 
            st.rerun()


# ==========================================
#        PAGE 2: APPROVER DASHBOARD
# ==========================================
elif page == "Approver Dashboard":
    st.title("Permit Approval Dashboard")
    
    df = pd.read_csv(PERMIT_DB)
    
    # --- 1. TWO-WEEK TIME FILTER ---
    start_dates = pd.to_datetime(df['start_date'], errors='coerce')
    current_date = pd.Timestamp(datetime.now().date())
    age_in_days = (current_date - start_dates).dt.days
    recent_mask = (age_in_days <= 14) | start_dates.isna()
    display_df = df[recent_mask].copy()
    
    # --- 2. CUSTOM SORTING ---
    sort_mapping = {
        'PENDING_ISSUER': 1,
        'PENDING_HSE': 2,
        'PENDING_APPROVER': 3,
        'APPROVED': 4,
        'CANCELLED': 5
    }
    display_df['sort_order'] = display_df['status'].map(sort_mapping).fillna(99)
    display_df = display_df.sort_values(by=['sort_order', 'start_date'], ascending=[True, False])
    
    if display_df.empty:
        st.info("All caught up! No active or recent permits from the last 14 days.")
    else:
        for index, row in display_df.iterrows():

            # ✅ Step 6 logic
            auto_open = False
            if open_permit_id and str(row['permit_id']) == str(open_permit_id):
                auto_open = True

            # ✅ Expander (always runs, not inside IF!)
            with st.expander(
                f"Permit #{row['permit_id']} | {row['type']} | Status: {row['status']}",
                expanded=auto_open
            ):

                st.write(f"**Contractor:** {row.get('contractor', 'N/A')}")
                st.write(f"**Requestor:** {row['requestor_name']} ({row['requestor_email']})")
                st.write(f"**Location:** {row['location']}")
                st.write(f"**Work Description:** {row.get('work_description', 'N/A')}")
                st.write(f"**Schedule:** {row.get('start_date', '')} {row.get('start_time', '')}  TO  {row.get('end_date', '')} {row.get('end_time', '')}")
                st.caption(f"**Assigned To:** Issuer: {row.get('issuer', 'N/A')} | HSE: {row.get('hse_reviewer', 'N/A')} | Approver: {row.get('approver', 'N/A')}")

                # --- CANCELLED VIEW ---
                if row['status'] == "CANCELLED":
                    st.error("🚫 **PERMIT CANCELLED / REVOKED**")
                    st.write("This permit has been officially cancelled. All associated work must be stopped immediately.")
                
                # --- PENDING ISSUER ---
                elif row['status'] == "PENDING_ISSUER" and (not open_role or open_role == "issuer"):
                    st.markdown("### Issuer Approval")
                    comment = st.text_area("Issuer Comments", key=f"iss_{row['permit_id']}")
                    sign_path = signature_selection_ui("Issuer", row.get('issuer', 'Unknown'), row['permit_id'])
                    
                    c1, c2 = st.columns([1, 4])
                    with c1:
                        if st.button("Approve (Issuer)", key=f"btn_iss_{row['permit_id']}", type="primary"):
                            if sign_path:
                                df.at[index, 'issuer_sign'] = sign_path
                            df.at[index, 'issuer_comments'] = comment
                            df.at[index, 'issuer_time'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            df.at[index, 'status'] = "PENDING_HSE"
                            df.to_csv(PERMIT_DB, index=False)
                            
                            hse_email = extract_email(row['hse_reviewer'])
                            if hse_email:
                                base_url = "https://rksingh9883122-online-permit.streamlit.app"  # 🔥 replace later

                                hse_link = f"{base_url}/?permit_id={row['permit_id']}&role=hse"

                                send_workflow_email(
                                    hse_email,
                                    f"Action Required: HSE Review for Permit #{row['permit_id']}",
                                    f"""
                            Hello,

                            Permit #{row['permit_id']} has been approved by the Issuer.

                            👉 Click below to perform HSE review:
                            {hse_link}

                            This link will take you directly to your review page.

                            Regards,  
                            Digital PTW System
                            """
                                )

                            st.rerun()
                    with c2:
                        if st.button("Cancel Permit", key=f"cancel_iss_{row['permit_id']}"):
                            df.at[index, 'status'] = 'CANCELLED'
                            df.to_csv(PERMIT_DB, index=False)
                            notify_cancellation(row, "Issuer") 
                            st.rerun()

                # --- PENDING HSE ---
                elif row['status'] == "PENDING_HSE" and (not open_role or open_role == "hse"):
                    st.markdown("### HSE Review")
                    st.info(f"Issuer: {row['issuer']} | Signed at: {row.get('issuer_time', 'N/A')}\n\nIssuer Comments: {row['issuer_comments']}")
                    comment = st.text_area("HSE Comments", key=f"hse_{row['permit_id']}")
                    sign_path = signature_selection_ui("HSE Reviewer", row.get('hse_reviewer', 'Unknown'), row['permit_id'])

                    c1, c2 = st.columns([1, 4])
                    with c1:
                        if st.button("Approve (HSE)", key=f"btn_hse_{row['permit_id']}", type="primary"):
                            if sign_path:
                                df.at[index, 'hse_sign'] = sign_path
                            df.at[index, 'hse_comments'] = comment
                            df.at[index, 'hse_time'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            df.at[index, 'status'] = "PENDING_APPROVER"
                            df.to_csv(PERMIT_DB, index=False)

                            approver_email = extract_email(row['approver'])
                            if approver_email:
                                base_url = "https://rksingh9883122-online-permit.streamlit.app"   # 🔥 replace after deploy

                                approver_link = f"{base_url}/?permit_id={row['permit_id']}&role=approver"

                                send_workflow_email(
                                    approver_email,
                                    f"Action Required: Final Approval for Permit #{row['permit_id']}",
                                    f"""
                            Hello,

                            Permit #{row['permit_id']} has completed HSE review.

                            👉 Click below for final approval:
                            {approver_link}

                            This link will take you directly to the approval page.

                            Regards,  
                            Digital PTW System
                            """
                                )

                            st.rerun()
                    with c2:
                        if st.button("Cancel Permit", key=f"cancel_hse_{row['permit_id']}"):
                            df.at[index, 'status'] = 'CANCELLED'
                            df.to_csv(PERMIT_DB, index=False)
                            notify_cancellation(row, "HSE Reviewer") 
                            st.rerun()

                # --- PENDING APPROVER ---
                elif row['status'] == "PENDING_APPROVER" and (not open_role or open_role == "approver"):
                    st.markdown("### Final Approval")
                    st.info(f"Issuer: {row['issuer']} | Signed at: {row.get('issuer_time', 'N/A')}\n\nIssuer Comments: {row['issuer_comments']}")
                    st.info(f"HSE Reviewer: {row['hse_reviewer']} | Signed at: {row.get('hse_time', 'N/A')}\n\nHSE Comments: {row['hse_comments']}")
                    
                    st.warning("You are providing final approval. This will generate the PDF and email the requestor.")
                    comment = st.text_area("Approver Comments", key=f"app_{row['permit_id']}")
                    sign_path = signature_selection_ui("Approver", row.get('approver', 'Unknown'), row['permit_id'])

                    c1, c2 = st.columns([1, 4])
                    with c1:
                        if st.button("Final Approve & Send", key=f"btn_app_{row['permit_id']}", type="primary"):
                            if sign_path:
                                df.at[index, 'approver_sign'] = sign_path
                            df.at[index, 'approver_comments'] = comment
                            df.at[index, 'approver_time'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            df.at[index, 'status'] = "APPROVED"
                            df.to_csv(PERMIT_DB, index=False)
                            
                            approved_row = df.loc[index]
                            generated_pdf_path = generate_permit_pdf(approved_row)
                            
                            req_email = row.get('requestor_email')
                            if req_email:
                                 send_workflow_email(req_email, f"Permit Approved: #{row['permit_id']}", f"Hello,\n\nYour permit #{row['permit_id']} has been fully approved. Please find the PDF attached.", generated_pdf_path)
                            st.rerun()
                    with c2:
                        if st.button("Cancel Permit", key=f"cancel_app_{row['permit_id']}"):
                            df.at[index, 'status'] = 'CANCELLED'
                            df.to_csv(PERMIT_DB, index=False)
                            notify_cancellation(row, "Final Approver") 
                            st.rerun()
                
                # --- APPROVED ---
                elif row['status'] == "APPROVED":
                    st.success("This permit has been fully approved and PDF generated.")
                    st.warning("HSE Reviewer / Admin: You may still cancel this permit in an emergency if worksite conditions change.")
                    if st.button("Cancel Active Permit (Emergency Revoke)", key=f"cancel_active_{row['permit_id']}"):
                        df.at[index, 'status'] = 'CANCELLED'
                        df.to_csv(PERMIT_DB, index=False)
                        notify_cancellation(row, "HSE/Admin (Emergency Revoke)") 
                        st.rerun()

# ==========================================
#        PAGE 3: MANAGE PERSONNEL
# ==========================================
elif page == "Manage Personnel":
    st.title("Manage Personnel & Contractors")
    
    st.header("1. Internal Personnel (Roles)")
    role = st.selectbox("Select Role to Edit", list(st.session_state.personnel.keys()))
    
    st.write(f"**Current people in {role} role:**")
    for idx, person in enumerate(st.session_state.personnel[role]):
        st.write(f"- {person['name']} ({person['email']})")
        
    st.subheader(f"Add new {role}")
    with st.form(key=f"add_person_{role}"):
        new_name = st.text_input("Name")
        new_email = st.text_input("Email")
        submit = st.form_submit_button("Add Person")
        if submit and new_name and new_email:
            st.session_state.personnel[role].append({"name": new_name, "email": new_email})
            with open(PERSONNEL_DB, 'w') as f:
                json.dump(st.session_state.personnel, f, indent=4)
            st.success(f"Added {new_name} to {role}!")
            st.rerun()
            
    st.divider()

    st.header("2. Contractors")
    contractor = st.selectbox("Select Contractor Company", list(st.session_state.contractors.keys()) + ["+ Add New Contractor Company"])
    
    if contractor == "+ Add New Contractor Company":
        new_company = st.text_input("New Company Name")
        if st.button("Add Company") and new_company:
            st.session_state.contractors[new_company] = []
            with open(CONTRACTORS_DB, 'w') as f:
                json.dump(st.session_state.contractors, f, indent=4)
            st.success(f"Added {new_company}!")
            st.rerun()
    else:
        st.write(f"**Current requestors for {contractor}:**")
        for idx, person in enumerate(st.session_state.contractors[contractor]):
            st.write(f"- {person['name']} ({person['email']})")
            
        st.subheader(f"Add new Requestor to {contractor}")
        with st.form(key=f"add_req_{contractor}"):
            req_name = st.text_input("Name")
            req_email = st.text_input("Email")
            submit_req = st.form_submit_button("Add Requestor")
            if submit_req and req_name and req_email:
                st.session_state.contractors[contractor].append({"name": req_name, "email": req_email})
                with open(CONTRACTORS_DB, 'w') as f:
                    json.dump(st.session_state.contractors, f, indent=4)
                st.success(f"Added {req_name} to {contractor}!")
                st.rerun()

# ==========================================
#        PAGE 4: LIVE DASHBOARD
# ==========================================
elif page == "Live Dashboard":
    st.title("Live HSE Permit Dashboard")
    st.markdown("Real-time monitoring of Work Permits.")

    @st.cache_data(ttl=10)
    def load_dashboard_data():
        try:
            df = pd.read_csv(PERMIT_DB)
            if not df.empty:
                df['start_date'] = pd.to_datetime(df['start_date'], errors='coerce')
            return df
        except Exception as e:
            st.error(f"Error loading dashboard data: {e}")
            return pd.DataFrame()

    df_dash = load_dashboard_data()

    if st.button("Refresh Data Now"):
        st.cache_data.clear()
        st.rerun()

    if df_dash.empty:
        st.warning("No permit data found yet. Create some permits first!")
    else:
        st.markdown("### Permit Overview")
        col1, col2, col3, col4 = st.columns(4)

        total_permits = len(df_dash)
        approved_permits = len(df_dash[df_dash['status'] == 'APPROVED'])
        hot_work_count = sum(df_dash['type'].astype(str).str.contains('Hot Work'))
        confined_space_count = sum(df_dash['type'].astype(str).str.contains('Confined Space'))

        col1.metric("Total Permits", total_permits)
        col2.metric("Approved", approved_permits)
        col3.metric("Hot Work", hot_work_count)
        col4.metric("Confined Space", confined_space_count)
        st.divider()

        st.markdown("### Dashboard Analytics")
        chart_col1, chart_col2 = st.columns(2)

        with chart_col1:
            status_counts = df_dash['status'].value_counts().reset_index()
            status_counts.columns = ['Status', 'Count']
            fig_pie = px.pie(
                status_counts, 
                names='Status', 
                values='Count', 
                title='Permit Distribution by Status',
                hole=0.4 
            )
            st.plotly_chart(fig_pie, use_container_width=True)

        with chart_col2:
            loc_counts = df_dash['location'].value_counts().reset_index()
            loc_counts.columns = ['Location', 'Count']
            fig_bar = px.bar(
                loc_counts, 
                x='Location', 
                y='Count', 
                title='Total Permits by Location', 
                text_auto=True,
                color='Location'
            )
            fig_bar.update_layout(showlegend=False, xaxis_title="", yaxis_title="Number of Permits")
            st.plotly_chart(fig_bar, use_container_width=True)

        st.divider()

        st.markdown("### Live Permit Feed")
        st.sidebar.header("Filter Dashboard")
        selected_type = st.sidebar.multiselect("Permit Type", df_dash['type'].unique(), default=df_dash['type'].unique())
        selected_status = st.sidebar.multiselect("Status", df_dash['status'].unique(), default=df_dash['status'].unique())

        filtered_df = df_dash[(df_dash['type'].isin(selected_type)) & (df_dash['status'].isin(selected_status))]

        st.dataframe(
            filtered_df[['permit_id', 'contractor', 'type', 'location', 'status', 'requestor_name', 'start_date']], 
            use_container_width=True,
            hide_index=True
        )

        st.markdown("### Permit Deep Dive")
        selected_permit = st.selectbox("Select a Permit ID to view detailed hazards, checkpoints, and approvals:", filtered_df['permit_id'])

        if selected_permit:
            permit_data = filtered_df[filtered_df['permit_id'] == selected_permit].iloc[0]
            
            st.markdown("#### Approval Chain")
            ac1, ac2, ac3 = st.columns(3)
            with ac1:
                st.write(f"**Issuer:** {permit_data.get('issuer', 'N/A')}")
                st.caption(f"Time: {permit_data.get('issuer_time', 'Pending')}")
                st.caption(f"Comments: {permit_data.get('issuer_comments', 'None')}")
            with ac2:
                st.write(f"**HSE Reviewer:** {permit_data.get('hse_reviewer', 'N/A')}")
                st.caption(f"Time: {permit_data.get('hse_time', 'Pending')}")
                st.caption(f"Comments: {permit_data.get('hse_comments', 'None')}")
            with ac3:
                st.write(f"**Approver:** {permit_data.get('approver', 'N/A')}")
                st.caption(f"Time: {permit_data.get('approver_time', 'Pending')}")
                st.caption(f"Comments: {permit_data.get('approver_comments', 'None')}")

            st.divider()
            
            col_info1, col_info2 = st.columns(2)
            
            with col_info1:
                st.markdown("#### Hazards & Controls")
                try:
                    hazards = ast.literal_eval(permit_data['hazards_json'])
                    for p_type, hazard_list in hazards.items():
                        st.markdown(f"**Permit Type: {p_type}**")
                        for i, h in enumerate(hazard_list):
                            st.markdown(f"**Hazard {i+1}:** :red[{h.get('hazard', 'N/A')}]")
                            st.markdown(f"**Control:** :blue[{h.get('control', 'N/A')}]")
                            st.write("---")
                except Exception as e:
                    st.write("No valid hazard data available.")
                    
            with col_info2:
                st.markdown("#### Checkpoints Validated")
                try:
                    checkpoints = ast.literal_eval(permit_data['checkpoints_json'])
                    for p_type, cp_list in checkpoints.items():
                        st.markdown(f"**Permit Type: {p_type}**")
                        for i, cp in enumerate(cp_list):
                            answer = cp.get('answer', 'N/A')
                            color = "green" if answer == "Yes" else "red" if answer == "No" else "gray"
                            
                            st.markdown(f"**{i+1}.** {cp.get('checkpoint_text', 'N/A')}")
                            st.markdown(f"**Response:** :{color}[**{answer}**]")
                            st.write("---")
                except Exception as e:
                    st.write("No valid checkpoint data available.")