import csv
import random
import uuid

sla_text = """
SERVICE LEVEL AGREEMENT (SLA) & BILLING TERMS
Vendor: CloudCompute Inc.
Customer: Razorpay Buildathon Project

1. BILLING ACCURACY: The vendor will bill based on actual units consumed. If billed units exceed actual usage logs, the customer is entitled to a full refund of the overcharged amount.
2. UPTIME GUARANTEE: 
   - Acceptable downtime is strictly less than 10 minutes per billing cycle.
   - If actual downtime is 10 to 30 minutes, customer receives a 10% refund on the total billed amount for that service.
   - If actual downtime exceeds 30 minutes, customer receives a 25% refund on the total billed amount.
3. EXCEPTION HANDLING: If usage logs are missing, corrupted, or cannot be verified, the invoice must be flagged as "REQUIRES_HUMAN_REVIEW" and not automatically approved.
"""

with open("sla_contracts.txt", "w") as f:
    f.write(sla_text.strip())

services = [
    {"name": "EC2_Compute", "price_per_unit": 2.50},
    {"name": "S3_Storage", "price_per_unit": 0.05},
    {"name": "RDS_Database", "price_per_unit": 5.00},
    {"name": "API_Gateway", "price_per_unit": 0.01}
]

invoices, usage_logs = [], []

for i in range(60):
    invoice_id = f"INV-{uuid.uuid4().hex[:8].upper()}"
    service = random.choice(services)
    actual_units = random.randint(100, 10000)
    actual_downtime = random.randint(0, 5)
    scenario = random.choices(["MATCH", "OVERBILLED", "SLA_BREACH", "CORRUPTED"], weights=[70, 15, 10, 5], k=1)[0]
    
    if scenario == "MATCH":
        billed_units, billed_downtime, log_status = actual_units, actual_downtime, "OK"
    elif scenario == "OVERBILLED":
        billed_units, billed_downtime, log_status = int(actual_units * random.uniform(1.1, 1.3)), actual_downtime, "OK"
    elif scenario == "SLA_BREACH":
        billed_units, actual_downtime, billed_downtime, log_status = actual_units, random.randint(15, 45), 5, "OK"
    elif scenario == "CORRUPTED":
        billed_units, billed_downtime, log_status, actual_units, actual_downtime = actual_units, actual_downtime, "CORRUPTED_OR_MISSING", -1, -1

    total_billed = round(billed_units * service["price_per_unit"], 2)
    invoices.append({"invoice_id": invoice_id, "service_type": service["name"], "billed_units": billed_units, "unit_price": service["price_per_unit"], "total_billed": total_billed, "vendor_reported_downtime": billed_downtime})
    usage_logs.append({"log_id": f"LOG-{uuid.uuid4().hex[:6].upper()}", "invoice_id": invoice_id if log_status != "CORRUPTED_OR_MISSING" else "UNKNOWN", "actual_units_used": actual_units if log_status != "CORRUPTED_OR_MISSING" else "", "actual_downtime_minutes": actual_downtime if log_status != "CORRUPTED_OR_MISSING" else "", "system_status": log_status})

with open("vendor_invoices.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["invoice_id", "service_type", "billed_units", "unit_price", "total_billed", "vendor_reported_downtime"])
    writer.writeheader()
    writer.writerows(invoices)

with open("system_usage_logs.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["log_id", "invoice_id", "actual_units_used", "actual_downtime_minutes", "system_status"])
    writer.writeheader()
    writer.writerows(usage_logs)
  
