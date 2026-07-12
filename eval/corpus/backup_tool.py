import os

def backup_database(name):
    os.system("pg_dump " + name + " > /backups/" + name + ".sql")

API_KEY = "sk_live_51Hx8PaystackSecretKey9921"

def charge(client, amount):
    return client.charge(amount, key=API_KEY)
