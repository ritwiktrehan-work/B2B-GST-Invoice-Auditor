# B2B GST Invoice Auditor

![License](https://img.shields.io/badge/license-MIT-blue.svg)

🔗 **[Try the live app](https://b2b-gst-invoice-auditor-qndy3wprwcwrlgfzw6zxc5.streamlit.app)**

<img width="2560" height="2839" alt="B2B Invoice   GST Auditor Screenshot" src="https://github.com/user-attachments/assets/142a022d-8001-486a-9bd6-343341fb9ca2" />

A tool that automates data extraction from unstructured Indian B2B invoices and runs instant math and statutory tax compliance audits — supports single invoices,
batches of dozens at once, and both images and PDFs.

## What it does
Upload one or many vendor invoices — JPEG, PNG, or PDF.

- Extracts key financial fields (vendor, GSTIN, taxable value, CGST/SGST/IGST, total) using Google's Gemini vision model
- Runs a deterministic math check to verify the extracted totals actually add up
- Validates GST compliance: does Base Value + CGST + SGST + IGST equal the stated Total Invoice Value?
- Flags mismatches and GSTIN formatting errors for manual review
- Shows a full audit dashboard per invoice, plus one combined CSV export for the whole batch

## Features
- Extracts vendor name, invoice date, GSTIN, taxable value, CGST, SGST,
  IGST, and total amount directly from an invoice image or PDF
- **Batch processing** — upload multiple invoices at once and audit them
  all in a single run, with a progress bar and one combined CSV at the end
- **PDF support** — handles both single-page and multi-page PDFs
- **Configurable PDF interpretation** — choose whether a multi-page PDF is
  one invoice spanning several pages, or a batch of separate single-page
  invoices scanned into one file
- Deterministic math check — flags any variance between stated and
  calculated totals, so the AI's output is never trusted blindly
- GSTIN structural validation via regex, independent of the AI extraction
- Automatic model fallback — if one Gemini model is unavailable, the app
  retries with the next before giving up
- Sandbox demo mode — works instantly with sample data even with no API
  key configured, so anyone can try the UI without setup
- Works out of the box with a shared API key, or your own Gemini key as
  a fallback via the sidebar
- Copy-paste-ready internal compliance memo for each invoice

## Why I built this
Manually checking GST invoices for math errors and compliance issues is tedious and error-prone. This tool automates that first-pass check so mistakes get caught faster.

## How it works
Invoice image/PDF → Gemini vision extraction → Pydantic validation → Math + GSTIN checks → Audit dashboard

1. **Upload → pages** — each file is turned into one or more page images;
   PDFs are rendered page by page via PyMuPDF
2. **Pages → Gemini** — the image(s) are sent to Gemini with a structured
   extraction schema (via Pydantic), so the model's response is always
   valid, typed data rather than free-form text
3. **Gemini → structured data** — the model returns vendor details and tax
   figures matching the exact schema
4. **Deterministic audit** — two checks run entirely in Python, independent
   of the AI: does `taxable value + CGST + SGST + IGST` equal the stated
   total, and does the GSTIN match the correct 15-character format?
5. **Dashboard + export** — each invoice gets a verdict (compliant/flagged/failed), a detailed ledger, and a chart; the full batch can
   be exported as one CSV

## Setup

1. **Clone this repo**
```bash
   git clone https://github.com/ritwiktrehan-work/B2B-GST-Invoice-Auditor.git
   cd B2B-GST-Invoice-Auditor
```

2. **Create a virtual environment**
```bash
   python3 -m venv .venv
```

3. **Activate it**
```bash
   source .venv/bin/activate        # macOS/Linux
   .venv\Scripts\activate           # Windows
```

4. **Install dependencies**
```bash
   pip install -r requirements.txt
```

5. **(Optional) Add your own Gemini API key for local testing**

   Get a free key at [aistudio.google.com/apikey](https://aistudio.google.com/apikey),
   then create `.streamlit/secrets.toml`:
```toml
   GEMINI_API_KEY = "your-key-here"
```
   This file is git-ignored and will never be committed. Without a key, the
   app runs in Sandbox Demo Mode with sample data — you can also just paste
   a key into the app's "Advanced" sidebar panel once it's running.

6. **Run the app**
```bash
   streamlit run invoice_auditor.py
```

7. Open `http://localhost:8501` in your browser.

## Requirements
- Python 3.9+
- Free Google Gemini API key ([aistudio.google.com](https://aistudio.google.com/apikey)) — only needed to run real audits; sandbox mode works without one

## Privacy
Invoice images and PDFs are sent to Google's Gemini API for processing. No
data is stored by this app beyond what's held temporarily in your browser
session and any CSV you choose to export. Review
[Google's API terms](https://ai.google.dev/gemini-api/terms) before
processing sensitive financial documents.

## Cost
Gemini's free tier covers typical personal use at no cost. Batch audits
make one API call per invoice, so large batches use quota proportionally
faster. Heavy or repeated use of the shared demo key may occasionally hit
rate limits — use your own key in the Advanced panel if that happens.

## Built with
- [Streamlit](https://streamlit.io) — web app framework
- [Google Gemini API](https://ai.google.dev) (`google-genai`) — vision-based invoice extraction
- [Pydantic](https://docs.pydantic.dev) — structured output validation
- [PyMuPDF](https://pymupdf.readthedocs.io) — PDF-to-image conversion
- Python standard library — `re` for GSTIN validation

## Disclaimer
For educational and internal-review purposes only. This tool does not
constitute a certified statutory GST audit. AI-extracted data may contain
errors — always verify independently before relying on it for compliance
or filing purposes.

## License
This project is licensed under the [MIT License](LICENSE).

## Status
Actively in development. Deployed via Streamlit Cloud.

## Development note
Built with AI-assisted development (Claude) for implementation, based on my own requirements and domain knowledge of GST compliance rules.
