from Crypto.Cipher import AES

KEY = b"0123456789abcdef"

def encrypt(data):
    cipher = AES.new(KEY, AES.MODE_ECB)
    return cipher.encrypt(data)
