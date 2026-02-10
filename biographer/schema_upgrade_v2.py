"""
Schema upgrade for v2.0 extraction system.

Adds:
- New columns to existing tables (source_quote, evidence_type, life_period, approximate_year)
- New tables (sensory_memories, creative_works, skills_competencies, connections)
"""

import sqlite3
from pathlib import Path
from datetime import datetime


def upgrade_schema(db_path: Path):
    """Upgrade the database schema for v2.0 extraction."""

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print("=" * 60)
    print("SCHEMA UPGRADE FOR V2.0 EXTRACTION")
    print("=" * 60)

    # Tables that should receive the new columns
    # These are the cognitive architecture tables used by extraction
    tables_to_upgrade = [
        'life_events', 'relationships', 'stories', 'self_knowledge',
        'preferences', 'joys', 'sorrows', 'wounds', 'fears', 'loves',
        'losses', 'regrets', 'longings', 'healings', 'decisions',
        'wisdom', 'reasoning_patterns', 'growth', 'strengths',
        'vulnerabilities', 'value_hierarchies', 'contradictions',
        'mistakes', 'cognitive_biases', 'meaning_structures',
        'mortality_awareness', 'body_knowledge', 'philosophies',
        'questions', 'aspirations'
    ]

    # New columns to add
    new_columns = [
        ('source_quote', 'TEXT'),           # Verbatim quote from transcript
        ('evidence_type', 'TEXT'),          # direct_statement|paraphrase|inference|behavioral_observation
        ('life_period', 'TEXT'),            # childhood|adolescence|young_adult|etc
        ('approximate_year', 'INTEGER'),    # Year if known
        ('prompt_version', 'TEXT'),         # Which extraction prompt version generated this
    ]

    print("\n--- Adding new columns to existing tables ---")

    for table in tables_to_upgrade:
        # Check if table exists
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
        if not cursor.fetchone():
            print(f"  [SKIP] {table} - table does not exist")
            continue

        # Get existing columns
        cursor.execute(f"PRAGMA table_info({table})")
        existing_cols = {row[1] for row in cursor.fetchall()}

        # Add missing columns
        added = []
        for col_name, col_type in new_columns:
            if col_name not in existing_cols:
                try:
                    cursor.execute(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_type}")
                    added.append(col_name)
                except sqlite3.Error as e:
                    print(f"  [ERROR] {table}.{col_name}: {e}")

        if added:
            print(f"  [OK] {table}: added {', '.join(added)}")
        else:
            print(f"  [SKIP] {table}: columns already exist")

    # Create new tables
    print("\n--- Creating new tables ---")

    # Sensory Memories table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sensory_memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            modality TEXT,  -- visual, auditory, olfactory, tactile, gustatory
            sensory_content TEXT,
            associated_memory TEXT,
            emotional_charge TEXT,
            triggers_memory INTEGER DEFAULT 0,  -- 1 if encountering sensation triggers memory
            source_quote TEXT,
            evidence_type TEXT,
            life_period TEXT,
            approximate_year INTEGER,
            prompt_version TEXT,
            date_recorded TEXT
        )
    """)
    print("  [OK] sensory_memories table created/verified")

    # Creative Works table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS creative_works (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            medium TEXT,  -- music, writing, visual art, software, etc
            description TEXT,
            date_created TEXT,
            motivation TEXT,
            reception TEXT,
            current_status TEXT,  -- completed, in_progress, abandoned
            source_quote TEXT,
            evidence_type TEXT,
            life_period TEXT,
            approximate_year INTEGER,
            prompt_version TEXT,
            date_recorded TEXT
        )
    """)
    print("  [OK] creative_works table created/verified")

    # Skills & Competencies table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS skills_competencies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            skill_name TEXT,
            category TEXT,  -- professional, life, physical, creative, technical
            proficiency_level TEXT,  -- novice, competent, proficient, expert, master
            how_acquired TEXT,
            years_practiced INTEGER,
            last_used TEXT,
            source_quote TEXT,
            evidence_type TEXT,
            life_period TEXT,
            approximate_year INTEGER,
            prompt_version TEXT,
            date_recorded TEXT
        )
    """)
    print("  [OK] skills_competencies table created/verified")

    # Connections table (relational graph layer)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS entry_connections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entry_1_table TEXT,
            entry_1_id INTEGER,
            entry_1_title TEXT,
            entry_2_table TEXT,
            entry_2_id INTEGER,
            entry_2_title TEXT,
            connection_type TEXT,  -- caused_by, led_to, contradicts, reinforces, transforms, co_occurred, same_theme, involves_same_person, involves_same_place, same_source_different_facet
            description TEXT,
            source_pass TEXT,  -- which extraction pass identified this
            date_recorded TEXT
        )
    """)
    print("  [OK] entry_connections table created/verified")

    # Aspirations table (forward-looking goals)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS aspirations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            description TEXT,
            category TEXT,  -- personal, professional, creative, relational, spiritual
            urgency TEXT,  -- urgent, patient, wistful
            achievability TEXT,  -- achievable, uncertain, symbolic
            time_horizon TEXT,  -- near_term, mid_term, long_term, ongoing
            source_quote TEXT,
            evidence_type TEXT,
            life_period TEXT,
            approximate_year INTEGER,
            prompt_version TEXT,
            date_recorded TEXT
        )
    """)
    print("  [OK] aspirations table created/verified")

    # Commit changes
    conn.commit()

    # Verify the upgrade
    print("\n--- Verification ---")

    # Check a sample table
    cursor.execute("PRAGMA table_info(life_events)")
    cols = [row[1] for row in cursor.fetchall()]
    new_cols_present = [c for c in ['source_quote', 'evidence_type', 'life_period', 'approximate_year'] if c in cols]
    print(f"  life_events new columns: {new_cols_present}")

    # Check new tables exist
    for table in ['sensory_memories', 'creative_works', 'skills_competencies', 'entry_connections', 'aspirations']:
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
        exists = cursor.fetchone() is not None
        print(f"  {table}: {'EXISTS' if exists else 'MISSING'}")

    conn.close()

    print("\n" + "=" * 60)
    print("SCHEMA UPGRADE COMPLETE")
    print("=" * 60)


if __name__ == '__main__':
    db_path = Path(__file__).parent.parent / "bill_knowledge_base.db"
    print(f"Upgrading database: {db_path}")
    upgrade_schema(db_path)
