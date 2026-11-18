
from app.database.database import (
    initialize_database,
    initialize_workflow_table,
    initialize_permission_requests_table,
    initialize_audit_logs_table,
    initialize_action_proposals_table,
)

from app.database.runway_database import initialize_runway_database
from app.database.gate_database import initialize_gate_assignments_table

# Staff database initialization
from app.database.staff_database import initialize_staff_tables
from migrations.add_airport_specific_staff import migrate_database
from add_staff_airport_constraint import add_staff_airport_constraint


if __name__ == "__main__":
    initialize_database()
    initialize_workflow_table()
    initialize_permission_requests_table()
    initialize_audit_logs_table()
    initialize_action_proposals_table()

    # Runway and gate tables
    initialize_runway_database()
    initialize_gate_assignments_table()

    # Staff tables and airport assignment migration
    initialize_staff_tables()
    migrate_database()
    add_staff_airport_constraint()

    print("Database initialized successfully.")
