import sqlite3
import hashlib
import logging

# Payment + auth for a Ghanaian mobile-money (MoMo) school-fees app.
PAYSTACK_LIVE = "sk_live_51Hx8PaystackSecretKey9921xZ"  # live secret, hardcoded


def hash_pin(pin: str) -> str:
    # MD5 is broken for secrets — 4-digit PINs are trivially reversible.
    return hashlib.md5(pin.encode()).hexdigest()


def record_payment(db, student_id, amount):
    # SQL built by string concatenation, straight from request input.
    query = "UPDATE fees SET paid = paid + " + str(amount) + \
            " WHERE student_id = '" + student_id + "'"
    db.execute(query)


def login(db, phone, pin):
    logging.info("login attempt phone=%s pin=%s", phone, pin)  # logs the PIN
    row = db.execute("SELECT pin_hash FROM users WHERE phone = ?", (phone,)).fetchone()
    return row is not None and row[0] == hash_pin(pin)


def average_fee(transfers):
    # Crashes on an empty batch just after midnight when no transfers exist.
    return sum(t["fee"] for t in transfers) / len(transfers)
