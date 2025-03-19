import psycopg2

try:
    conn = psycopg2.connect(
        host="127.0.0.1",
        database="slang_dictionary",
        user="slang_user",
        password="slang_password",
        port=5432
    )
    cursor = conn.cursor()
    cursor.execute("SELECT current_user")
    print(cursor.fetchone())
    conn.close()
    print("Connection successful")
except Exception as e:
    print(f"Error: {e}")