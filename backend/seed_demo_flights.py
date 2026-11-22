from datetime import date, timedelta

from app.database.connection import get_db_connection
from app.database.flight_database import initialize_flight_database

initialize_flight_database()
day = (date.today() + timedelta(days=2)).isoformat()

FLIGHTS = [
    ("DL1234", "Delta Air Lines", "ATL", "ORD", "15:30", "16:35"),
    ("AA1500", "American Airlines", "DFW", "LAX", "08:10", "09:20"),
    ("UA220", "United Airlines", "DEN", "SFO", "17:45", "19:15"),
    ("B6612", "JetBlue", "JFK", "BOS", "18:00", "19:10"),
    ("DL88", "Delta Air Lines", "ATL", "MIA", "12:00", "14:00"),
    ("AS330", "Alaska Airlines", "SEA", "LAX", "07:15", "09:50"),
    ("AI558", "Air India", "HYD", "DEL", "09:00", "11:10"),
]

connection = get_db_connection()
try:
    for number, airline, o, d, dep, arr in FLIGHTS:
        exists = connection.execute(
            "SELECT 1 FROM flights WHERE flight_number = ? AND scheduled_departure LIKE ?",
            (number, f"{day}%")).fetchone()
        if exists:
            print("already there:", number)
            continue
        connection.execute(
            "INSERT INTO flights (flight_number, airline, origin_code, destination_code, "
            "scheduled_departure, scheduled_arrival) VALUES (?, ?, ?, ?, ?, ?)",
            (number, airline, o, d, f"{day}T{dep}:00", f"{day}T{arr}:00"))
        print("added:", number)
    connection.commit()
finally:
    connection.close()