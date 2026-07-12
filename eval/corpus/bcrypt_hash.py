import bcrypt

def hash_password(pw: str) -> bytes:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt())

def check_password(pw: str, stored: bytes) -> bool:
    return bcrypt.checkpw(pw.encode(), stored)
