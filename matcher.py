import streamlit as st
import psycopg2
from psycopg2 import extras
from rapidfuzz import process, utils

def get_db_connection():
    """Establishes a secure connection to the Supabase Cloud PostgreSQL database."""
    # Reads the secure connection string directly from your Streamlit App Secrets vault
    connection_string = st.secrets["db_url"]
    conn = psycopg2.connect(connection_string)
    
    # Initialize the tables automatically if they do not exist on Supabase yet
    with conn.cursor() as cursor:
        # 1. Create clients table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS clients (
                id SERIAL PRIMARY KEY,
                name TEXT UNIQUE NOT NULL
            );
        ''')
        
        # 2. Create mappings table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS mappings (
                id SERIAL PRIMARY KEY,
                client_name TEXT NOT NULL,
                type TEXT NOT NULL,
                raw_name TEXT NOT NULL,
                tally_name TEXT NOT NULL,
                UNIQUE(client_name, type, raw_name)
            );
        ''')
        conn.commit()
    return conn

def get_all_clients():
    """Fetches all registered client company profiles from the cloud database."""
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT name FROM clients ORDER BY name ASC;")
            clients = [row[0] for row in cursor.fetchall() if row[0]]
        conn.close()
        return clients
    except Exception as e:
        print(f"Cloud DB Error fetching clients: {e}")
        return []

def add_new_client(client_name):
    """Registers a brand new company profile safely into the permanent cloud database."""
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO clients (name) VALUES (%s) ON CONFLICT (name) DO NOTHING;",
                (client_name.strip(),)
            )
            conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Cloud DB Error adding client: {e}")
        return False

def remove_client(client_name):
    """Deletes a client profile and clears out its associated mapping data globally."""
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM clients WHERE name = %s;", (client_name,))
            cursor.execute("DELETE FROM mappings WHERE client_name = %s;", (client_name,))
            conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Cloud DB Error removing client: {e}")
        return False

def save_mapping(client_name, mapping_type, raw_name, tally_name):
    """Saves or overrides a mapping decision directly into the Supabase cloud ledger."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute('''
                INSERT INTO mappings (client_name, type, raw_name, tally_name)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (client_name, type, raw_name) 
                DO UPDATE SET tally_name = EXCLUDED.tally_name;
            ''', (client_name, mapping_type, raw_name, tally_name))
            conn.commit()
    except Exception as e:
        print(f"Cloud DB Sync Error: {e}")
    finally:
        conn.close()

def smart_match(raw_value, tally_master_list, client_name, mapping_type):
    """Checks cloud mapping history first, falling back to rapidfuzz string matching."""
    if not raw_value or str(raw_value).strip() == "" or not tally_master_list:
        return "", 0.0

    raw_str = str(raw_value).strip()

    # --- 1. CLOUD MEMORY HISTORY LOOKUP ---
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute('''
                SELECT tally_name FROM mappings 
                WHERE client_name = %s AND type = %s AND raw_name = %s
                LIMIT 1;
            ''', (client_name, mapping_type, raw_str))
            result = cursor.fetchone()
        conn.close()
        
        if result and result[0] and result[0] in tally_master_list:
            return result[0], 100.0  # History match found
    except Exception:
        pass

    # --- 2. FUZZY MATCHING ENGINE FALLBACK ---
    try:
        extract = process.extractOne(
            raw_str, 
            tally_master_list, 
            processor=utils.default_process,
            score_cutoff=0.0
        )
        if extract:
            best_match, score, _ = extract
            return best_match, round(float(score), 1)
    except Exception:
        pass

    return tally_master_list[0] if tally_master_list else "", 0.0
