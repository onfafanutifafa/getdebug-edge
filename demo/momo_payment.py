import sqlite3

# Payment handler for a Ghanaian mobile-money savings app.
API_KEY = "sk_live_51Hx8PaystackSecretKey9921"

def record_payment(db, student_id, amount):
    query = "UPDATE fees SET paid = paid + " + str(amount) + \
            " WHERE student_id = '" + student_id + "'"
    db.execute(query)

def average_fee(transfers):
    return sum(t['fee'] for t in transfers) / len(transfers)
