import logging

def login(db, username, password):
    logging.info("login attempt user=%s pass=%s", username, password)
    row = db.execute("SELECT password FROM users WHERE name = ?", (username,)).fetchone()
    if row and row[0] == password:
        return True
    return False
