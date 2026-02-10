"""Database schema upgrade for cognitive architecture capture.

Adds new tables for deeper personality/cognition modeling while preserving existing data.
"""

import sqlite3
from pathlib import Path
from datetime import datetime


def upgrade_schema(db_path: Path = None):
    """Add cognitive architecture tables to the database."""
    if db_path is None:
        db_path = Path(__file__).parent.parent / "bill_knowledge_base.db"

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # New tables for cognitive architecture capture
    new_tables = """

    -- Major decisions with full reasoning context
    CREATE TABLE IF NOT EXISTS decisions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        time_period TEXT,
        context TEXT,                    -- Situation that required the decision
        options_considered TEXT,         -- What alternatives existed
        what_was_chosen TEXT,           -- The actual choice made
        reasoning TEXT,                  -- Why this choice was made
        what_was_felt TEXT,             -- Emotional state during decision
        outcome TEXT,                    -- What happened as a result
        would_change TEXT,              -- What Bill would do differently
        what_it_reveals TEXT,           -- AI inference about decision patterns
        evidence TEXT,                   -- Source quotes
        narrative_ref INTEGER,          -- Link to source narrative
        significance INTEGER DEFAULT 5,
        date_recorded TEXT
    );

    -- Mistakes analyzed for patterns and learning
    CREATE TABLE IF NOT EXISTS mistakes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        time_period TEXT,
        what_happened TEXT,             -- The error itself
        why_it_happened TEXT,           -- Root cause analysis
        what_was_believed TEXT,         -- False beliefs that led to error
        what_was_protected TEXT,        -- What ego/fear was defending
        pattern_category TEXT,          -- Does this repeat? What type?
        what_it_cost TEXT,              -- Consequences
        what_broke_pattern TEXT,        -- If pattern stopped, what changed
        evidence TEXT,
        narrative_ref INTEGER,
        significance INTEGER DEFAULT 5,
        date_recorded TEXT
    );

    -- Reasoning patterns - how Bill thinks through problems
    CREATE TABLE IF NOT EXISTS reasoning_patterns (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pattern_name TEXT NOT NULL,
        description TEXT,               -- What the pattern looks like
        when_used TEXT,                 -- Situations that trigger this approach
        strengths TEXT,                 -- When it works well
        weaknesses TEXT,                -- When it fails
        example_decisions TEXT,         -- Specific examples
        evidence TEXT,
        confidence TEXT,                -- How confident is this inference
        date_recorded TEXT
    );

    -- Value hierarchies - what Bill prioritizes
    CREATE TABLE IF NOT EXISTS value_hierarchies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        value TEXT NOT NULL,
        rank INTEGER,                   -- Position in hierarchy (1=highest)
        competes_with TEXT,             -- What values it tensions against
        sacrifice_evidence TEXT,        -- What Bill sacrificed for this value
        violation_response TEXT,        -- How Bill reacts when this is violated
        evolution TEXT,                 -- How this changed over time
        evidence TEXT,
        date_recorded TEXT
    );

    -- Cognitive biases - known blind spots
    CREATE TABLE IF NOT EXISTS cognitive_biases (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        bias_name TEXT NOT NULL,
        description TEXT,
        how_it_manifests TEXT,          -- Specific ways it shows up
        examples TEXT,                  -- Instances observed
        awareness_level TEXT,           -- Does Bill know about this?
        mitigation TEXT,                -- Any strategies to counter it
        evidence TEXT,
        date_recorded TEXT
    );

    -- Fear architecture
    CREATE TABLE IF NOT EXISTS fears (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fear TEXT NOT NULL,
        root_source TEXT,               -- Where it comes from
        what_it_protects TEXT,          -- What the fear is trying to protect
        triggers TEXT,                  -- What activates it
        physical_response TEXT,         -- Body sensations
        behavioral_response TEXT,       -- What Bill does when afraid
        adaptive_value TEXT,            -- Is this fear useful?
        cost TEXT,                      -- What opportunities lost
        evidence TEXT,
        significance INTEGER DEFAULT 5,
        date_recorded TEXT
    );

    -- Joy map - what brings genuine fulfillment
    CREATE TABLE IF NOT EXISTS joys (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        joy TEXT NOT NULL,
        category TEXT,                  -- Type of joy (creative, relational, etc.)
        what_it_feels_like TEXT,        -- Phenomenology
        conditions TEXT,                -- What enables this joy
        frequency TEXT,                 -- How often experienced
        depth TEXT,                     -- Fleeting pleasure vs deep fulfillment
        connection_to_meaning TEXT,     -- How it relates to life purpose
        evidence TEXT,
        date_recorded TEXT
    );

    -- Wisdom - hard-won heuristics
    CREATE TABLE IF NOT EXISTS wisdom (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        insight TEXT NOT NULL,
        domain TEXT,                    -- Life area (relationships, work, etc.)
        how_learned TEXT,               -- What experience taught this
        cost_of_learning TEXT,          -- What it took to learn
        when_applicable TEXT,           -- Situations where this applies
        exceptions TEXT,                -- When it doesn't apply
        confidence INTEGER DEFAULT 5,   -- How certain (1-10)
        evidence TEXT,
        date_recorded TEXT
    );

    -- Contradictions - unresolved tensions
    CREATE TABLE IF NOT EXISTS contradictions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tension TEXT NOT NULL,          -- The contradiction itself
        side_a TEXT,                    -- One pole
        side_b TEXT,                    -- Other pole
        how_navigated TEXT,             -- How Bill lives with this
        resolution_attempts TEXT,       -- Any efforts to resolve
        what_it_reveals TEXT,           -- What this tension says about Bill
        evidence TEXT,
        date_recorded TEXT
    );

    -- Meaning structures - what makes life worth living
    CREATE TABLE IF NOT EXISTS meaning_structures (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source_of_meaning TEXT NOT NULL,
        category TEXT,                  -- Type (purpose, connection, etc.)
        how_discovered TEXT,            -- When this became meaningful
        how_expressed TEXT,             -- How Bill lives this meaning
        threatened_by TEXT,             -- What endangers this meaning
        would_fight_for TEXT,           -- Evidence of commitment
        evidence TEXT,
        significance INTEGER DEFAULT 5,
        date_recorded TEXT
    );

    -- Mortality awareness - how finitude shapes choices
    CREATE TABLE IF NOT EXISTS mortality_awareness (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        insight TEXT NOT NULL,
        category TEXT,                  -- Type (acceptance, fear, urgency, etc.)
        what_changed TEXT,              -- How this insight changed Bill
        triggered_by TEXT,              -- What brought this awareness
        impact_on_priorities TEXT,      -- How it affects what matters
        impact_on_relationships TEXT,   -- How it affects connections
        evidence TEXT,
        date_recorded TEXT
    );

    -- Aesthetic responses - what Bill finds beautiful
    CREATE TABLE IF NOT EXISTS beauties (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        what TEXT NOT NULL,             -- The beautiful thing
        category TEXT,                  -- Type (music, nature, human, etc.)
        response TEXT,                  -- What Bill feels/does
        why_beautiful TEXT,             -- AI inference about why
        pattern TEXT,                   -- Common thread with other beauties
        evidence TEXT,
        date_recorded TEXT
    );

    -- Body knowledge - what incarnation teaches
    CREATE TABLE IF NOT EXISTS body_knowledge (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        insight TEXT NOT NULL,
        category TEXT,                  -- Type (pain, aging, pleasure, etc.)
        how_learned TEXT,               -- Physical experience that taught this
        mind_body_connection TEXT,      -- How body affects thinking/feeling
        what_body_knows TEXT,           -- Wisdom the body holds
        evidence TEXT,
        date_recorded TEXT
    );

    -- Inferred patterns - AI meta-analysis across all data
    CREATE TABLE IF NOT EXISTS inferred_patterns (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pattern_name TEXT NOT NULL,
        pattern_type TEXT,              -- Category of pattern
        description TEXT,               -- What the pattern is
        supporting_evidence TEXT,       -- Citations from multiple sources
        confidence TEXT,                -- How confident is inference
        cross_references TEXT,          -- Links to related entries
        first_observed TEXT,            -- When pattern first noted
        last_updated TEXT,
        date_recorded TEXT
    );

    -- Cross references between entries
    CREATE TABLE IF NOT EXISTS cross_references (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source_table TEXT NOT NULL,
        source_id INTEGER NOT NULL,
        target_table TEXT NOT NULL,
        target_id INTEGER NOT NULL,
        relationship_type TEXT,         -- How they relate
        notes TEXT,
        date_created TEXT
    );

    """

    # Execute all table creations
    cursor.executescript(new_tables)
    conn.commit()

    # Verify tables were created
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [row[0] for row in cursor.fetchall()]

    new_table_names = [
        'decisions', 'mistakes', 'reasoning_patterns', 'value_hierarchies',
        'cognitive_biases', 'fears', 'joys', 'wisdom', 'contradictions',
        'meaning_structures', 'mortality_awareness', 'beauties', 'body_knowledge',
        'inferred_patterns', 'cross_references'
    ]

    created = [t for t in new_table_names if t in tables]
    print(f"Schema upgrade complete. New tables available: {len(created)}")
    for t in created:
        print(f"  - {t}")

    conn.close()
    return created


if __name__ == "__main__":
    upgrade_schema()
