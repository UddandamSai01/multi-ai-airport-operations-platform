import json
from app.agents.analysis_agent import run_analysis

r = run_analysis(["DL1234", "AA1500", "B6612", "AI558", "XX000"])
print(json.dumps({k: v for k, v in r.items() if k != "assessments"}, indent=2))
for a in r["assessments"]:
    print(a["flight_id"], a["route"], a["status"], a["risk_level"],
          a["delay_probability"], a["error"])