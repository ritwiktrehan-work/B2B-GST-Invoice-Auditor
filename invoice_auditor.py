import streamlit as st
from PIL import Image
import re
import pandas as pd
from pydantic import BaseModel, Field
from google import genai
from google.genai import types

st.set_page_config(page_title="Enterprise GST Auditor", layout="wide")

# Securely attempt to pull from secrets; automatically fall back if running locally
try:
    DEFAULT_API_KEY = st.secrets["GEMINI_API_KEY"]
except Exception:
    DEFAULT_API_KEY = "PASTE_YOUR_NEW_GEMINI_API_KEY_HERE"

class InvoiceData(BaseModel):
    vendor_name: str = Field(description="Legal name of the vendor/supplier")
    invoice_date: str = Field(description="Date of the invoice issue")
    gstin: str = Field(description="The 15-character GST identification number of the supplier")
    taxable_value: float = Field(description="The base taxable value before GST calculation")
    cgst: float = Field(default=0.0, description="Central GST amount")
    sgst: float = Field(default=0.0, description="State/UT GST amount")
    igst: float = Field(default=0.0, description="Integrated GST amount")
    total_amount: float = Field(description="The final total invoice value stated on the document")

def validate_gstin(gstin: str) -> bool:
    gstin_pattern = r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$"
    return bool(re.match(gstin_pattern, gstin.strip().upper()))

st.title("🧾 Institutional B2B Invoice & GST Auditor")
st.caption("Hybrid AI Extraction & Deterministic Financial Auditing Ledger")
st.markdown("---")

uploaded_file = st.file_uploader("Upload Vendor Invoice (JPEG/PNG)", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    col_layout_left, col_layout_right = st.columns([1, 1.3])

    with col_layout_left:
        image = Image.open(uploaded_file)
        st.image(image, caption="Uploaded Invoice Source", width="stretch")

    with col_layout_right:
        if st.button("Execute Compliance & Tax Audit", type="primary", width="stretch"):

            # CHECK: If no key is configured anywhere, run the Sandbox Simulation instantly
            if DEFAULT_API_KEY == "PASTE_YOUR_NEW_GEMINI_API_KEY_HERE" or not DEFAULT_API_KEY:
                st.warning("📊 No active API Key gateway detected. Running in Sandbox Demo Mode using cached ledger targets...")

                extracted_data = InvoiceData(
                    vendor_name="WAL-MART INDIA PVT. LTD.",
                    invoice_date="06/07/2026",
                    gstin="01AADCB2110L1ZE",
                    taxable_value=2464.85,
                    cgst=79.89,
                    sgst=79.89,
                    igst=0.0,
                    total_amount=2624.63
                )
                successful_model = "Sandbox-Core-Simulation"
                error_logs = []

            else:
                # Live Production Routing Mode
                models_to_try = [
                    'gemini-3.5-flash',
                    'gemini-3.1-flash-lite',
                    'gemini-3.1-pro-preview'
                ]

                extracted_data = None
                successful_model = None
                error_logs = []

                status_placeholder = st.empty()

                for current_model in models_to_try:
                    status_placeholder.info(f"Connecting to data extraction gateway via {current_model}...")
                    try:
                        client = genai.Client(api_key=DEFAULT_API_KEY)

                        response = client.models.generate_content(
                            model=current_model,
                            contents=[image, "Extract all the required financial parameters accurately from this Indian B2B invoice."],
                            config=types.GenerateContentConfig(
                                response_mime_type="application/json",
                                response_schema=InvoiceData,
                                temperature=0.1
                            ),
                        )

                        extracted_data = InvoiceData.model_validate_json(response.text)
                        successful_model = current_model
                        break

                    except Exception as model_error:
                        error_msg = f"Track {current_model} encountered an exception: {str(model_error)}"
                        error_logs.append(error_msg)
                        st.warning(f"⚠️ Channel {current_model} bypassed. Hot-swapping to next available track...")
                        continue

                status_placeholder.empty()

            # --- Render Dashboard UI Elements ---
            if extracted_data:
                with st.container():
                    st.subheader("📋 Audit Summary Ledger")

                    is_gstin_valid = validate_gstin(extracted_data.gstin)
                    calculated_total = extracted_data.taxable_value + extracted_data.cgst + extracted_data.sgst + extracted_data.igst
                    variance = round(extracted_data.total_amount - calculated_total, 2)
                    is_math_valid = abs(variance) <= 0.05

                    m_col1, m_col2, m_col3 = st.columns(3)
                    m_col1.metric("Stated Invoice Total", f"₹{extracted_data.total_amount:,.2f}")
                    m_col2.metric("Calculated Total", f"₹{calculated_total:,.2f}")
                    m_col3.metric("Variance", f"₹{variance}", delta=f"{variance} discrepancy" if variance != 0 else None, delta_color="inverse")

                    st.markdown("### ⚖️ Executive Audit Verdict")
                    if is_gstin_valid and is_math_valid:
                        verdict_text = "🟢 COMPLIANT"
                        st.success(f"{verdict_text}: Invoice structural properties and tax metrics reconciled perfectly.")
                    elif not is_math_valid:
                        verdict_text = "🔴 AUDIT FAILURE"
                        st.error(f"{verdict_text}: Tax arithmetic ledger variance detected (Discrepancy: ₹{variance}).")
                    else:
                        verdict_text = "🟡 REGULARITY FLAGGED"
                        st.warning(f"{verdict_text}: Math is correct, but Supplier GSTIN format failed structural checks.")

                    with st.expander("📝 View Auditor's File Note (Copy-Paste Ready)", expanded=True):
                        memo_content = f"""**INTERNAL COMPLIANCE MEMORANDUM**
**Status:** {verdict_text}  
**Vendor:** {extracted_data.vendor_name} | **Date:** {extracted_data.invoice_date}  
**GSTIN:** {extracted_data.gstin} (Structure Verified: {is_gstin_valid})  

**Financial Summary:**
* Base Taxable Amount: ₹{extracted_data.taxable_value:,.2f}
* Total Computed Tax: ₹{(extracted_data.cgst + extracted_data.sgst + extracted_data.igst):,.2f}
* Variance to Stated Total: ₹{variance:,.2f}

*File processed digitally via system automation parsing framework.*"""
                        st.code(memo_content, language="markdown")

                    st.markdown("### 📋 1. Core Corporate Identifiers")
                    gstin_status = "🟢 Pass (Valid Format)" if is_gstin_valid else "🔴 Fail (Invalid GSTIN Layout)"

                    df_identifiers = pd.DataFrame({
                        "Field": ["Vendor Name", "Invoice Date", "Extracted GSTIN", "GSTIN Struct Status"],
                        "Value": [extracted_data.vendor_name, str(extracted_data.invoice_date), extracted_data.gstin, gstin_status]
                    })
                    st.table(df_identifiers)
