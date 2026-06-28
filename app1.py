# app.py
import streamlit as st
import pandas as pd
import json
import copy
from datetime import datetime
from werkzeug.utils import secure_filename

# Import our modularized code
from config import *
from helpers import signature_selection_ui, extract_email, send_workflow_email

# --- PAGE CONFIG & INITIALIZATION ---
st.set_page_config(page_title="Digital Permit System", layout="wide")
initialize_system()

# Load Session State Data
if 'personnel' not in st.session_state:
    with open(PERSONNEL_DB, 'r') as f: st.session_state.personnel = json.load(f)
if 'contractors' not in st.session_state:
    with open(CONTRACTORS_DB, 'r') as f: st.session_state.contractors = json.load(f)
if 'locations' not in st.session_state:
    with open(LOCATIONS_DB, 'r') as f: st.session_state.locations = json.load(f)

with open(HAZARDS_DB, 'r') as f: HAZARDS_MAP = json.load(f)
with open(CHECKPOINTS_DB, 'r') as f: CHECKPOINTS_MAP = json.load(f)

# ==========================================
#             APP NAVIGATION
# ==========================================
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to:", ["Request Permit", "Approver Dashboard", "Manage Personnel", "Live Dashboard"])

# ==========================================
#             PAGE 1: REQUEST FORM
# ==========================================
if page == "Request Permit":
    st.title("Digital Work Permit Request")
    # (Insert your Request Permit UI logic here)

# ==========================================
#        PAGE 2: APPROVER DASHBOARD
# ==========================================
elif page == "Approver Dashboard":
    st.title("Permit Approval Dashboard")
    df = pd.read_csv(PERMIT_DB)
    
    # --- TIME FILTER & SORTING ---
    start_dates = pd.to_datetime(df['start_date'], errors='coerce')
    recent_mask = ((pd.Timestamp(datetime.now().date()) - start_dates).dt.days <= 14) | start_dates.isna()
    display_df = df[recent_mask].copy()
    
    sort_mapping = {'PENDING_ISSUER': 1, 'PENDING_HSE': 2, 'PENDING_APPROVER': 3, 'APPROVED': 4, 'CANCELLED': 5}
    display_df['sort_order'] = display_df['status'].map(sort_mapping).fillna(99)
    display_df = display_df.sort_values(by=['sort_order', 'start_date'], ascending=[True, False])
    
    if display_df.empty:
        st.info("All caught up! No active or recent permits from the last 14 days.")
    else:
        for index, row in display_df.iterrows():
            with st.expander(f"Permit #{row['permit_id']} | {row['type']} | Status: {row['status']}"):
                st.write(f"**Contractor:** {row.get('contractor', 'N/A')}")
                
                if row['status'] == "CANCELLED":
                    st.error("🚫 **PERMIT CANCELLED / REVOKED**")
                elif row['status'] == "PENDING_ISSUER":
                    st.markdown("### Issuer Approval")
                    comment = st.text_area("Issuer Comments", key=f"iss_{row['permit_id']}")
                    sign_path = signature_selection_ui("Issuer", row.get('issuer', 'Unknown'), row['permit_id'])
                    
                    c1, c2 = st.columns()
                    with c1:
                        if st.button("Approve (Issuer)", key=f"btn_iss_{row['permit_id']}", type="primary"):
                            if sign_path: df.at[index, 'issuer_sign'] = sign_path
                            df.at[index, 'issuer_comments'] = comment
                            df.at[index, 'issuer_time'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            df.at[index, 'status'] = "PENDING_HSE"
                            df.to_csv(PERMIT_DB, index=False)
                            st.rerun()
                    with c2:
                        if st.button("Cancel Permit", key=f"cancel_iss_{row['permit_id']}"):
                            df.at[index, 'status'] = "CANCELLED"
                            df.to_csv(PERMIT_DB, index=False)
                            st.rerun()