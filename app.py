import os
import sqlite3
import pandas as pd
import streamlit as st
import generate_data
import reconciler

st.set_page_config(page_title="AI Finance Controller", layout="wide")

st.title("🤖 AI Finance Controller & SLA Reconciler")
st.write("Automated B2B invoice audit engine powered by Gemini 1.5 Flash.")

# Ensure synthetic data exists on load
if not os.path.exists("vendor_invoices.csv"):
    import subprocess
    subprocess.run(["python", "generate_data.py"])
    st.toast("Generated initial synthetic dataset!")

# Run AI Analysis Trigger
if st.button("🚀 Run AI Reconciliation Batch"):
    with st.spinner("Gemini 1.5 Flash is auditing invoices against SLA terms..."):
        msg = reconciler.run_reconciliation()
        st.success(msg)

# Display Dashboard Metrics & Audit Log Table
if os.path.exists("audit_trail.db"):
    conn = sqlite3.connect("audit_trail.db")
    df = pd.read_sql_query("SELECT * FROM audit_logs ORDER BY id DESC", conn)
    conn.close()

    if not df.empty:
        total_recovered = df[df["status"] == "REFUND_DUE"]["refund_amount"].sum()
        flagged_count = len(df[df["status"] == "REQUIRES_HUMAN_REVIEW"])

        col1, col2, col3 = st.columns(3)
        col1.metric("Invoices Processed", len(df))
        col2.metric("Total Revenue Recovered", f"${total_recovered:,.2f}")
        col3.metric("Human Review Flagged", flagged_count)

        st.subheader("📊 Live Audit Trail")
        st.dataframe(df, use_container_width=True)
    else:
        st.info("Tap 'Run AI Reconciliation Batch' above to execute the AI auditor.")
else:
        st.info("Click 'Run AI Reconciliation Batch' to create the initial audit trail database.")
  
