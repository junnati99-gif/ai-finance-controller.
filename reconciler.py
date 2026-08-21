import csv
import json
import os
import sqlite3
import streamlit as st
from google import genai

def init_db():
    conn = sqlite3.connect("audit_trail.db")
    cursor = conn.cursor()
    cursor.execute("DROP TABLE IF EXISTS audit_logs")
    cursor.execute("""
        CREATE TABLE audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            invoice_id TEXT,
            status TEXT,
            refund_amount REAL,
            reason TEXT,
            sla_rule_cited TEXT
        )
    """)
    conn.commit()
    conn.close()

def run_reconciliation():
    init_db()
    
    invoices, logs = {}, {}
    with open("vendor_invoices.csv", "r") as f:
        for row in csv.DictReader(f):
            invoices[row["invoice_id"]] = row

    with open("system_usage_logs.csv", "r") as f:
        for row in csv.DictReader(f):
            logs[row["invoice_id"]] = row

    # Retrieve API key from Streamlit Secrets or Environment
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key and "GEMINI_API_KEY" in st.secrets:
        api_key = st.secrets["GEMINI_API_KEY"]

    conn = sqlite3.connect("audit_trail.db")
    cursor = conn.cursor()

    for inv_id, inv in invoices.items():
        log = logs.get(inv_id, {})
        
        billed_units = float(inv.get("billed_units", 0))
        unit_price = float(inv.get("unit_price", 0))
        total_billed = float(inv.get("total_billed", 0))
        
        system_status = log.get("system_status", "OK")
        
        # Rule 3: Corrupted or missing log check
        if system_status == "CORRUPTED_OR_MISSING" or not log.get("actual_units_used"):
            cursor.execute("""
                INSERT INTO audit_logs (invoice_id, status, refund_amount, reason, sla_rule_cited)
                VALUES (?, ?, ?, ?, ?)
            """, (inv_id, "REQUIRES_HUMAN_REVIEW", 0.0, "Usage log corrupted or missing in system records.", "DATA_CORRUPTION"))
            continue

        actual_units = float(log.get("actual_units_used", 0))
        actual_downtime = float(log.get("actual_downtime_minutes", 0))

        refund = 0.0
        status = "MATCH"
        sla_cited = "NONE"
        reasons = []

        # Rule 1: Overbilling Check
        if billed_units > actual_units:
            overbilled_units = billed_units - actual_units
            overbilled_refund = round(overbilled_units * unit_price, 2)
            refund += overbilled_refund
            status = "REFUND_DUE"
            sla_cited = "OVERBILLING"
            reasons.append(f"Overbilled by {overbilled_units:.0f} units (${overbilled_refund:.2f} refund).")

        # Rule 2: Downtime SLA Breach Check
        if actual_downtime > 30:
            downtime_refund = round(total_billed * 0.25, 2)
            refund += downtime_refund
            status = "REFUND_DUE"
            sla_cited = "DOWNTIME_OVER_30"
            reasons.append(f"Downtime was {actual_downtime:.0f} mins (>30m SLA breach: 25% refund = ${downtime_refund:.2f}).")
        elif actual_downtime >= 10:
            downtime_refund = round(total_billed * 0.10, 2)
            refund += downtime_refund
            status = "REFUND_DUE"
            sla_cited = "DOWNTIME_10_TO_30"
            reasons.append(f"Downtime was {actual_downtime:.0f} mins (10-30m SLA breach: 10% refund = ${downtime_refund:.2f}).")

        reason_text = " ".join(reasons) if reasons else "Invoice matches system usage logs and SLA terms."

        cursor.execute("""
            INSERT INTO audit_logs (invoice_id, status, refund_amount, reason, sla_rule_cited)
            VALUES (?, ?, ?, ?, ?)
        """, (inv_id, status, round(refund, 2), reason_text, sla_cited))

    conn.commit()
    conn.close()
    return "Reconciliation Complete!"
