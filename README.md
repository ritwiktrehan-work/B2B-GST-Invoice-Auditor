# B2B GST Invoice Auditor

🔗 **[Try the live app](https://b2b-gst-invoice-auditor-qndy3wprwcwrlgfzw6zxc5.streamlit.app)**

A tool that automates data extraction from unstructured Indian B2B invoices and runs instant math and statutory tax compliance audits.

## What it does
- Extracts key fields from invoice text using RegEx pattern matching
- Runs automated math checks to verify invoice totals
- Validates GST compliance: Base Value + CGST + SGST + IGST = Total Invoice Value
- Flags mismatches and errors for manual review

## Tech stack
- Python
- RegEx for text parsing
- Streamlit for the web interface

## Why I built this
Manually checking GST invoices for math errors and compliance issues is tedious and error-prone. This tool automates that first-pass check so mistakes get caught faster.

## Status
Actively in development. Deployed via Streamlit Cloud.
