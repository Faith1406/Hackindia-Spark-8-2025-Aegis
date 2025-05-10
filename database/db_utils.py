import sqlite3
import os
from config import DB_PATH

def init_database():
    """Initialize the SQLite database with updated schema"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create sessions table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS sessions (
        session_id TEXT PRIMARY KEY,
        start_time TEXT,
        end_time TEXT,
        active INTEGER
    )
    ''')
    
    # Check if columns exist in chunks table
    cursor.execute("PRAGMA table_info(chunks)")
    columns = cursor.fetchall()
    column_names = [col[1] for col in columns]
    
    # If table doesn't exist or requires updates
    should_recreate = False
    
    if not any(col[1] == 'source' for col in columns):
        should_recreate = True
    
    if not any(col[1] == 'speaker_id' for col in columns):
        if 'chunks' in column_names:
            cursor.execute("ALTER TABLE chunks ADD COLUMN speaker_id TEXT")
        else:
            should_recreate = True
    
    if should_recreate:
        # Create new chunks table with all required columns
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS chunks_new (
            chunk_id TEXT PRIMARY KEY,
            session_id TEXT,
            timestamp TEXT,
            text TEXT,
            audio_path TEXT,
            source TEXT,
            speaker_id TEXT,
            FOREIGN KEY (session_id) REFERENCES sessions (session_id)
        )
        ''')
        
        # If old table exists, copy data
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='chunks'")
        if cursor.fetchone():
            # Copy all existing columns, set unknown for new ones
            query = """
            INSERT INTO chunks_new 
            SELECT 
                chunk_id, 
                session_id, 
                timestamp, 
                text, 
                audio_path,
                COALESCE(source, 'unknown') as source,
                NULL as speaker_id
            FROM chunks
            """
            cursor.execute(query)
            cursor.execute("DROP TABLE chunks")
        
        # Rename new table to chunks
        cursor.execute("ALTER TABLE chunks_new RENAME TO chunks")
    else:
        # Create chunks table if it doesn't exist
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS chunks (
            chunk_id TEXT PRIMARY KEY,
            session_id TEXT,
            timestamp TEXT,
            text TEXT,
            audio_path TEXT,
            source TEXT,
            speaker_id TEXT,
            FOREIGN KEY (session_id) REFERENCES sessions (session_id)
        )
        ''')
    
    conn.commit()
    conn.close()
    
    # Create directories if they don't exist
    os.makedirs("audio_chunks", exist_ok=True)
    os.makedirs("speaker_embeddings", exist_ok=True)

def get_chunks_from_db(session_id, last_chunk_id=None):
    """Get chunks from database for a session"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Get chunks for that session
    if last_chunk_id:
        # Only get chunks after the specified one - use rowid to ensure proper ordering
        cursor.execute(
            """
            SELECT c1.chunk_id, c1.timestamp, c1.text, c1.audio_path, c1.source, c1.speaker_id 
            FROM chunks c1
            JOIN (SELECT rowid FROM chunks WHERE chunk_id = ?) c2
            WHERE c1.session_id = ? AND c1.rowid > c2.rowid
            ORDER BY c1.rowid
            """,
            (last_chunk_id, session_id)
        )
    else:
        cursor.execute(
            "SELECT chunk_id, timestamp, text, audio_path, source, speaker_id FROM chunks WHERE session_id = ? ORDER BY rowid",
            (session_id,)
        )
    
    chunks = []
    for row in cursor.fetchall():
        chunks.append({
            "chunk_id": row['chunk_id'],
            "timestamp": row['timestamp'],
            "text": row['text'],
            "audio_path": row['audio_path'],
            "source": row['source'] if 'source' in row.keys() else 'unknown',
            "speaker_id": row['speaker_id'] if 'speaker_id' in row.keys() else None
        })
    
    conn.close()
    return chunks

def get_audio_path(chunk_id):
    """Get the audio file path for a specific chunk"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT audio_path FROM chunks WHERE chunk_id = ?", (chunk_id,))
    row = cursor.fetchone()
    
    conn.close()
    
    if row:
        return row['audio_path']
    else:
        return None

def get_latest_session_id():
    """Get the most recent session ID from the database"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Get most recent session
    cursor.execute("SELECT session_id FROM sessions ORDER BY start_time DESC LIMIT 1")
    session_row = cursor.fetchone()
    
    conn.close()
    
    if session_row:
        return session_row['session_id']
    else:
        return None

# Initialize database if not done already
init_database()