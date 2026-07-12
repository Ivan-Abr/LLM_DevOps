import psycopg2

conn = psycopg2.connect(
    dbname="devops_rag",
    user="postgres",
    password="postgres",
    host="localhost",
    port=5433,
)
cur = conn.cursor()
cur.execute("SELECT version();")
print(cur.fetchone())
conn.close()