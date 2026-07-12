import jwt

JWT_SECRET = "supersecret123"

def make_token(user_id):
    return jwt.encode({"uid": user_id}, JWT_SECRET, algorithm="HS256")

def verify(token):
    return jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
