from app.database.database import (
    initialize_database,
    initialize_workflow_table,
    initialize_permission_requests_table,
    initialize_audit_logs_table,
    initialize_action_proposals_table,
)

from app.database.runway_database import initialize_runway_database

if __name__ == "__main__":
    initialize_database()
    initialize_workflow_table()
    initialize_permission_requests_table()
    initialize_audit_logs_table()
    initialize_action_proposals_table()
    initialize_runway_database()

    print("Database initialized successfully.")