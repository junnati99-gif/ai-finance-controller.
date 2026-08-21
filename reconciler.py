import csv
import json
import os
import sqlite3
from typing import Literal
from pydantic import BaseModel
from google import genai

class ReconciliationResult(BaseModel):
    invoice_id: str
    status: Literal["MATCH", "REFUND_DUE", "REQUIRES_HUMAN_REVIEW"]
    refund_amount: float
    reason: str
    sla_rule_cited: Literal["NONE", "OVERBILLING", "DOWNTIME_10_TO_30", "DOWNTIME_OVER_30", "DATA_CORRUPTION"]

def init_db():
    conn = sqlite3.connect("audit_trail.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
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

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return "Error: GEMINI_API_KEY environment variable not set."

    client = genai.Client(api_key=api_key)
    
    with open("sla_contracts.txt", "r") as f:
        sla_text = f.read()

    system_instruction = f"You are an automated AI Finance Controller. Rules:\n{sla_text}"

    conn = sqlite3.connect("audit_trail.db")
    cursor = conn.cursor()

    for inv_id, inv in invoices.items():
        log = logs.get(inv_id, {})
        prompt_data = f"INVOICE: {json.dumps(inv)}\nLOG: {json.dumps(log)}"
        
        try:
            response = client.models.generate_content(
                model="gemini-1.5-flash",
                contents=prompt_data,
                config={
                    "system_instruction": system_instruction,
                    "response_mime_type": "application/json",
                    "response_schema": ReconciliationResult,
                    "temperature": 0.0,
                }
            )
            res = ReconciliationResult.model_validate_json(response.text)
            cursor.execute("""
                INSERT INTO audit_logs (invoice_id, status, refund_amount, reason, sla_rule_cited)
                VALUES (?, ?, ?, ?, ?)
            """, (res.invoice_id, res.status, res.refund_amount, res.reason, res.sla_rule_cited))
            
        except Exception as e:
            cursor.execute("""
                INSERT INTO audit_logs (invoice_id, status, refund_amount, reason, sla_rule_cited)
                VALUES (?, ?, ?, ?, ?)
            """, (inv_id, "REQUIRES_HUMAN_REVIEW", 0.0, f"Guardrail: {str(e)}", "DATA_CORRUPTION"))

    conn.commit()
    conn.close()
    return "Reconciliation Complete!"
  
