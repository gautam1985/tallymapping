import os
import sys
import sqlite3
from rapidfuzz import process, utils

# ==========================================
# 🧠 PORTABLE ENGINE (DETERMINES RUN LOCATION)
# ==========================================
if getattr(sys, 'frozen', False):
    # Running as a compiled EXE - look right next to Tally_Automation.exe
    BASE_DIR = os.path.dirname(sys.executable)
else:
    # Running locally in VS Code
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DB_PATH = os.path.join(BASE_DIR, "tally_data.db")

def get_db_connection():
    return sqlite3.connect(DB_PATH)

def initialize_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        )
    ''')
    cursor.execute("PRAGMA table_info(clients)")
    columns = [row[1] for row in cursor.fetchall()]
    if 'name' not in columns:
        cursor.execute("DROP TABLE IF EXISTS clients")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS clients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL
            )
        ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS mappings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_name TEXT NOT NULL,
            type TEXT NOT NULL,         
            raw_name TEXT NOT NULL,
            tally_name TEXT NOT NULL,
            UNIQUE(client_name, type, raw_name)
        )
    ''')
    conn.commit()
    conn.close()

initialize_db()

def add_new_client(client_name):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO clients (name) VALUES (?)", (client_name.strip(),))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def get_all_clients():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT name FROM clients ORDER BY name ASC")
        return [row[0] for row in cursor.fetchall()]
    except sqlite3.OperationalError:
        initialize_db()
        return []
    finally:
        conn.close()

def remove_client(client_name):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM clients WHERE name = ?", (client_name,))
        cursor.execute("DELETE FROM mappings WHERE client_name = ?", (client_name,))
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()

def save_mapping(client_name, mapping_type, raw_name, tally_name):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO mappings (client_name, type, raw_name, tally_name)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(client_name, type, raw_name) 
        DO UPDATE SET tally_name = excluded.tally_name
    ''', (client_name, mapping_type, raw_name.strip(), tally_name.strip()))
    conn.commit()
    conn.close()

def smart_match(raw_name, tally_masters_list, client_name, mapping_type):
    cleaned_raw = raw_name.strip()
    if not tally_masters_list:
        return cleaned_raw, 0.0

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT tally_name FROM mappings 
        WHERE client_name = ? AND type = ? AND raw_name = ?
    ''', (client_name, mapping_type, cleaned_raw))
    row = cursor.fetchone()
    conn.close()

    if row:
        historical_saved_name = row[0]
        if historical_saved_name in tally_masters_list:
            return historical_saved_name, 100.0

    extract = process.extractOne(
        cleaned_raw, 
        tally_masters_list, 
        processor=utils.default_process,
        score_cutoff=0.0
    )
    
    if extract:
        best_match_text, score, _ = extract
        return best_match_text, round(float(score), 1)
    
    return tally_masters_list[0], 0.0