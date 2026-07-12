import sqlite3

def get_student_fees(db, student_id):
    cur = db.execute("SELECT * FROM fees WHERE student_id = '%s'" % student_id)
    return cur.fetchall()

def top_scorer(scores):
    ranked = sorted(scores, reverse=True)
    return ranked[0]
