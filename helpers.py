# helpers.py
import os
import ast
import smtplib
import pandas as pd
import streamlit as st
from datetime import datetime
from email.message import EmailMessage
from fpdf import FPDF
from config import PERMIT_FOLDER, SIGNATURE_DIR

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
    # (Insert your full PDF generation logic here)
    pass 

# --- EMAIL HELPER ---
def extract_email(person_string):
    if pd.isna(person_string) or not person_string: return None
    if "(" in str(person_string) and ")" in str(person_string):
        return str(person_string).split("(")[-1].split(")").strip()
    return None

def send_workflow_email(recipient_email, subject, body, pdf_path=None):
    if not recipient_email: return
    EMAIL_ADDRESS = "rksingh9883122@gmail.com"
    EMAIL_PASSWORD = "cbkw xsus zyht ryso"
    msg = EmailMessage()
    msg['Subject'], msg['From'], msg['To'] = subject, EMAIL_ADDRESS, recipient_email
    msg.set_content(body)

    if pdf_path and os.path.exists(pdf_path):
        with open(pdf_path, 'rb') as f:
            msg.add_attachment(f.read(), maintype='application', subtype='pdf', filename=os.path.basename(pdf_path))
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            smtp.send_message(msg)
    except Exception as e:
        print(f"Failed to send email: {e}")

def notify_cancellation(permit_row, cancelled_by_role):
    # (Insert your cancellation logic here using send_workflow_email)
    pass

# --- REUSABLE SIGNATURE UI HELPER ---
def signature_selection_ui(role_name, person_name, permit_id):
    st.markdown(f"**{role_name} Signature Selection**")
    safe_person_name = str(person_name).split('(').strip()
    existing_sigs = [f for f in os.listdir(SIGNATURE_DIR) if f.endswith(('.png', '.jpg', '.jpeg'))]
    options = ["-- Upload New Signature --"] + existing_sigs
    choice = st.selectbox(f"Select existing signature for {safe_person_name}, or upload new:", options, key=f"sig_select_{role_name}_{permit_id}")
    
    final_signature_path = None
    if choice == "-- Upload New Signature --":
        uploaded_file = st.file_uploader(f"Upload new signature image", type=["png", "jpg", "jpeg"], key=f"sig_upload_{role_name}_{permit_id}")
        if uploaded_file is not None:
            new_file_name = f"{safe_person_name.replace(' ', '_').lower()}_signature.{uploaded_file.name.split('.')[-1]}"
            final_signature_path = os.path.join(SIGNATURE_DIR, new_file_name)
            with open(final_signature_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            st.success(f"Signature saved!")
            st.image(final_signature_path, width=150)
    else:
        final_signature_path = os.path.join(SIGNATURE_DIR, choice)
        st.info("Using previously saved signature.")
        st.image(final_signature_path, width=150)
        
    return final_signature_path