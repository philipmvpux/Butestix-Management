import psycopg2

try:
    # Using connection string with proper encoding
    conn = psycopg2.connect(
        "postgresql://postgres:philo1234@localhost/bauapp"
    )
    cur = conn.cursor()
    
    # Try to add each column individually with ROLLBACK on error
    columns = [
        ("is_test_account", "BOOLEAN DEFAULT FALSE"),
        ("test_expiration_time", "TIMESTAMP DEFAULT NULL"),
        ("test_duration_hours", "INTEGER DEFAULT 24")
    ]
    
    for col_name, col_type in columns:
        try:
            sql_stmt = f"ALTER TABLE benutzer ADD COLUMN {col_name} {col_type}"
            cur.execute(sql_stmt)
            conn.commit()
            print(f"✅ Added column {col_name}")
        except psycopg2.errors.DuplicateColumn:
            conn.rollback()
            print(f"⚠️  Column {col_name} already exists")
        except Exception as e:
            conn.rollback()
            print(f"❌ Error adding {col_name}: {e}")
    
    conn.close()
except Exception as e:
    print(f"❌ Connection error: {e}")
