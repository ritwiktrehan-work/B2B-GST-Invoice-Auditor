import streamlit as st
from PIL import Image
import re
import io
import fitz  # PyMuPDF
import pandas as pd
from pydantic import BaseModel, Field
from google import genai
from google.genai import types

st.set_page_config(page_title="Enterprise GST Auditor", layout="wide")

# Securely attempt to pull from secrets; this is the shared key that lets
# every visitor use the app with zero setup. It's never shown to visitors.
try:
    DEFAULT_API_KEY = st.secrets["GEMINI_API_KEY"]
except Exception:
    DEFAULT_API_KEY = None

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


def run_extraction(page_images, api_key):
    """Runs the model-fallback extraction against one document's page images.
    Returns (extracted_data_or_None, model_used_or_None, error_logs)."""
    models_to_try = [
        'gemini-3.5-flash',
        'gemini-3.1-flash-lite',
        'gemini-3.1-pro'
    ]
    error_logs = []

    for current_model in models_to_try:
        try:
            client = genai.Client(api_key=api_key)
            contents = list(page_images) + [
                "Extract all the required financial parameters accurately from "
                "this Indian B2B invoice. If multiple pages are provided, treat "
                "them as one single invoice document."
            ]
            response = client.models.generate_content(
                model=current_model,
                contents=contents,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=InvoiceData,
                    temperature=0.1
                ),
            )
            extracted = InvoiceData.model_validate_json(response.text)
            return extracted, current_model, error_logs
        except Exception as model_error:
            error_logs.append(f"Track {current_model} encountered an exception: {str(model_error)}")
            continue

    return None, None, error_logs


def render_audit(extracted_data, successful_model, source_label):
    """Renders the full audit dashboard for one extracted invoice."""
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

    with st.expander("📝 View Auditor's File Note (Copy-Paste Ready)", expanded=False):
        memo_content = f"""**INTERNAL COMPLIANCE MEMORANDUM**
**Source:** {source_label}
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

    st.markdown("### 🧮 2. Tax Arithmetic Ledger")
    df_ledger = pd.DataFrame({
        "Tax Component": ["Taxable Base Amount", "CGST", "SGST", "IGST", "Reported Final Total"],
        "Amount (INR)": [
            f"₹{extracted_data.taxable_value:,.2f}",
            f"₹{extracted_data.cgst:,.2f}",
            f"₹{extracted_data.sgst:,.2f}",
            f"₹{extracted_data.igst:,.2f}",
            f"₹{extracted_data.total_amount:,.2f}"
        ]
    })
    st.table(df_ledger)

    st.markdown("### 📊 3. Ledger Asset Distribution")
    chart_data = pd.DataFrame({
        "Components": ["Base Taxable", "CGST", "SGST", "IGST"],
        "Values (INR)": [extracted_data.taxable_value, extracted_data.cgst, extracted_data.sgst, extracted_data.igst]
    }).set_index("Components")
    st.bar_chart(chart_data, color="#1f77b4")

    st.caption(f"Audit Cycle Concluded Successfully (Routed via active infrastructure pipeline: {successful_model}).")

    return {
        **extracted_data.model_dump(),
        "source_file": source_label,
        "gstin_valid": is_gstin_valid,
        "arithmetic_variance": variance,
        "verdict": verdict_text,
    }


def load_pages_as_images(uploaded_file) -> list[Image.Image]:
    """Turn any supported upload into a list of PIL images (one per page).
    JPG/PNG become a single-item list; PDFs are rendered page by page so
    multi-page invoices are handled as one combined document."""
    file_bytes = uploaded_file.getvalue()
    name = uploaded_file.name.lower()

    if name.endswith(".pdf"):
        pages = []
        pdf = fitz.open(stream=file_bytes, filetype="pdf")
        for page in pdf:
            pix = page.get_pixmap(dpi=200)
            img = Image.open(io.BytesIO(pix.tobytes("png")))
            pages.append(img)
        pdf.close()
        return pages

    # JPG / PNG / other Pillow-readable image formats
    return [Image.open(io.BytesIO(file_bytes))]

st.title("🧾 Institutional B2B Invoice & GST Auditor")
st.caption("Hybrid AI Extraction & Deterministic Financial Auditing Ledger")
st.markdown("---")

# ---------------------------------------------------------------------------
# SIDEBAR: optional visitor-supplied API key. Most visitors never need this —
# the shared key (from secrets) covers everyone by default. This is just a
# fallback in case that key ever hits its free-tier rate limit.
# ---------------------------------------------------------------------------
user_key = ""
with st.sidebar.expander("⚙️ Advanced: use your own API key"):
    st.caption(
        "This app already works out of the box. Only use this if you hit a "
        "rate-limit error, or want to use your own Gemini quota."
    )
    user_key = st.text_input(
        "Your Gemini API key",
        type="password",
        help="Get a free key at aistudio.google.com/apikey.",
    )

active_key = user_key.strip() or DEFAULT_API_KEY

if not active_key:
    st.sidebar.info(
        "ℹ️ No API key configured. Running in Sandbox Demo Mode with cached "
        "sample data. Open 'Advanced' above and add a key to run real audits."
    )

uploaded_files = st.file_uploader(
    "Upload Vendor Invoice(s) — JPEG, PNG, or PDF",
    type=["jpg", "jpeg", "png", "pdf"],
    accept_multiple_files=True,
    help="Multi-page PDFs are supported — choose below how to interpret their pages.",
)

pdf_mode = st.radio(
    "How should multi-page PDFs be interpreted?",
    options=[
        "Each page is a separate invoice (batch of scanned invoices)",
        "All pages belong to one invoice (e.g. invoice + annexure)",
    ],
    index=0,
    help="Only matters for PDFs with more than one page. Single-page PDFs and images are unaffected.",
)
split_pdf_pages = pdf_mode.startswith("Each page")

if uploaded_files:
    st.markdown(f"**{len(uploaded_files)} file(s) queued for audit.**")

    if st.button("Execute Compliance & Tax Audit", type="primary", use_container_width=True):
        all_records = []

        # Flatten every uploaded file into a list of "documents" to audit.
        # A document is (label, [one or more page images]).
        documents = []
        for uploaded_file in uploaded_files:
            try:
                page_images = load_pages_as_images(uploaded_file)
            except Exception as e:
                st.error(f"Couldn't read '{uploaded_file.name}': {e}")
                continue

            if split_pdf_pages and len(page_images) > 1:
                for page_num, page_img in enumerate(page_images, start=1):
                    documents.append((f"{uploaded_file.name} (page {page_num})", [page_img]))
            else:
                label = uploaded_file.name
                if len(page_images) > 1:
                    label += f" ({len(page_images)} pages, treated as one invoice)"
                documents.append((label, page_images))

        progress = st.progress(0.0, text="Starting batch audit...")

        for i, (label, page_images) in enumerate(documents):
            progress.progress(
                i / len(documents),
                text=f"Processing {label} ({i + 1}/{len(documents)})...",
            )

            with st.container(border=True):
                col_layout_left, col_layout_right = st.columns([1, 1.3])

                with col_layout_left:
                    st.image(page_images[0], caption=label, use_container_width=True)
                    if len(page_images) > 1:
                        st.caption(f"📄 {len(page_images)}-page document — all pages sent as one invoice.")

                with col_layout_right:
                    st.subheader(f"📋 Audit: {label}")

                    if not active_key:
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
                        extracted_data, successful_model, error_logs = run_extraction(page_images, active_key)

                    if extracted_data:
                        record = render_audit(extracted_data, successful_model, label)
                        all_records.append(record)
                    else:
                        st.error("❌ High Availability Failure: All configured AI engine clusters are structurally congested or experiencing timeouts.")
                        with st.expander("View System Error Context Log"):
                            for log in error_logs:
                                st.text(log)

        progress.progress(1.0, text="Batch audit complete.")
        progress.empty()

        if all_records:
            st.markdown("---")
            st.subheader(f"📥 Batch Export — {len(all_records)} invoice(s) audited")
            export_df = pd.DataFrame(all_records)
            csv_data = export_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Export All Audit Records to CSV/Excel Ledger",
                data=csv_data,
                file_name="Batch_Audit_Report.csv",
                mime="text/csv",
                use_container_width=True,
            )
