from app.database.database import create_user, get_user_by_username, initialize_database

initialize_database()

if get_user_by_username("tester"):
    print("user 'tester' already exists")
else:
    create_user("user-tester-1", "tester", "Test@12345", "operator")
    print("created user 'tester' with password Test@12345")