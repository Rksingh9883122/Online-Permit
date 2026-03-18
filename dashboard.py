import streamlit as st
import pandas as pd

st.set_page_config(page_title="HSE Permit Dashboard", layout="wide")
st.title("🚧 Site Safety Monitor")

# Read data from the CSV shared with Flask
df = pd.read_csv('database/permits.csv')

# Metric Cards
col1, col2, col3 = st.columns(3)
col1.metric("Active Permits", len(df[df['status'] == 'APPROVED']))
col2.metric("Pending Review", len(df[df['status'].str.contains('PENDING')]))
col3.metric("High Risk (Hot Work)", len(df[df['type'] == 'hot_work']))

# Interactive Table
st.subheader("Permit Logs")
st.dataframe(df)

# Filter by Status
status_filter = st.selectbox("Filter by Status", df['status'].unique())
st.write(df[df['status'] == status_filter])

# Inside dashboard.py
if st.button("Download Selected Permit PDF"):
    # Assuming the row is selected
    with open(f"static/permits/Permit_{selected_id}.pdf", "rb") as f:
        st.download_button("Click here", f, file_name="Work_Permit.pdf")

# In dashboard.py
st.subheader("Action Required")
pending = df[df['status'].str.contains("PENDING")]

for index, row in pending.iterrows():
    col1, col2 = st.columns([3, 1])
    col1.write(f"Permit {row['permit_id']} - {row['type']} at {row['location']}")
    # Create a link to the Flask review page
    if col2.button(f"Review {row['permit_id']}", key=row['permit_id']):
        st.write(f"Open this link: http://127.0.0.1:5000/review/{row['permit_id']}")