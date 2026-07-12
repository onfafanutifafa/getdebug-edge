import hashlib

def hash_pin(pin):
    return hashlib.md5(pin.encode()).hexdigest()

def apply_discount(balance, percent):
    if percent > 100:
        percent = 100
    return balance - balance * percent / 100

def split_bill(total, people):
    share = total / len(people)
    return [share for _ in people]
