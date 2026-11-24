from app.agents.analysis_tools import run_delay_tool

good = {"airline": "DL", "origin": "ATL", "dest": "ORD", "flight_date": "2026-11-25",
        "sched_dep_time": 1530, "sched_arr_time": 1655,
        "sched_duration_min": 145, "distance_miles": 606}

print("1 good flight   :", run_delay_tool(good, "DL123")["status"])
print("2 non-US flight :", run_delay_tool({**good, "airline": "AI", "origin": "HYD", "dest": "DEL"}, "AI1")["status"])
print("3 airline name  :", run_delay_tool({**good, "airline": "Delta Air Lines"}, "bad1"))
print("4 bad time      :", run_delay_tool({**good, "sched_dep_time": 2575}, "bad2"))
print("5 missing field :", run_delay_tool({k: v for k, v in good.items() if k != "distance_miles"}, "bad3"))