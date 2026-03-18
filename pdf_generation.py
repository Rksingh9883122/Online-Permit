from fpdf import FPDF
import ast

class PermitPDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 16)
        self.cell(0, 10, 'OFFICIAL WORK PERMIT', 1, 1, 'C')
        self.ln(10)

def generate_permit_pdf(permit_row):
    pdf = PermitPDF()
    pdf.add_page()
    
    # Header Information
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, f"Permit ID: {permit_row['permit_id']}", 0, 1)
    pdf.set_font('Arial', '', 12)
    pdf.cell(0, 10, f"Location: {permit_row['location']} | Requestor: {permit_row['requestor_name']}", 0, 1)
    pdf.ln(5)

    # Hazards & Controls Section
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, "Hazards & Control Measures", 1, 1, 'L')
    pdf.set_font('Arial', '', 10)
    
    hazards = ast.literal_eval(permit_row['hazards_json'])
    for h in hazards:
        pdf.multi_cell(0, 10, f"- {h['hazard']}: {h['control']} (Responsible: {h['resp_name']})", 1)

    # Revalidation Page (Page 2)
    pdf.add_page()
    pdf.set_font('Arial', 'B', 14)
    pdf.cell(0, 10, "DAILY REVALIDATION LOG (OFFLINE)", 0, 1, 'C')
    pdf.ln(5)
    
    # Table for 7 days
    pdf.set_font('Arial', 'B', 9)
    headers = ['Date', 'Shift', 'Issuer Sign', 'HSE Sign', 'Approver Sign']
    for head in headers:
        pdf.cell(38, 10, head, 1, 0, 'C')
    pdf.ln()
    
    for _ in range(7):
        for _ in range(5):
            pdf.cell(38, 15, "", 1, 0)
        pdf.ln()

    # Ensure the directory exists before saving
    os.makedirs('static/permits', exist_ok=True)
    path = f"static/permits/Permit_{permit_row['permit_id']}.pdf"
    pdf.output(path)
    return path