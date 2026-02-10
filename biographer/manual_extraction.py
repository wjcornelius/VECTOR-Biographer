"""Manual extraction of data from failed session."""

import sqlite3
from datetime import datetime
from pathlib import Path

db_path = Path(__file__).parent.parent / "bill_knowledge_base.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()
now = datetime.now().isoformat()

print("Extracting data from failed session...")

# ============ LIFE EVENTS ============
# Schema: id, date_start, date_end, age_at_event, event_type, title, description, location, impact, lessons_learned

life_events = [
    ("1970s", "trading", "Early Trading Success", "Turned $700 into $8,000", "Toronto", "Planted seeds of both opportunity and danger that resurface in AI trading systems", "Trading can be lucrative but also dangerous"),
    ("childhood", "mentorship", "Peter Underwood Mentorship", "Neighbor who had English pub-style basement and patiently engaged with Bill's endless curiosity", "Toronto", "Formative experience of patient adult taking curiosity seriously", "Patient mentorship matters for curious children"),
    ("childhood", "discovery", "Discovery of Hidden Rabbits", "While digging for Peter Underwood's fountain, broke through to discover hidden rabbits", "Toronto", "Emblematic moment of breakthrough discovery", "Persistence in digging reveals hidden wonders"),
]

for date, etype, title, desc, loc, impact, lessons in life_events:
    cursor.execute("""
        INSERT INTO life_events (date_start, event_type, title, description, location, impact, lessons_learned)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (date, etype, title, desc, loc, impact, lessons))

# ============ DECISIONS ============

cursor.execute("""
    INSERT INTO decisions (title, context, what_was_chosen, reasoning, what_it_reveals, evidence, significance, date_recorded)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
""", (
    "Creating automated trading systems instead of manual trading",
    "Bill recognized that manual trading was becoming obsessive and unhealthy for someone with bipolar disorder",
    "Built Sentinel, Onplab, and Mag7 - autopilot trading systems that work with his brain chemistry rather than against it",
    "Invest upfront effort to create self-running systems that accommodate variable moods and energy levels",
    "Bill's self-awareness about his limitations leads him to engineer around them rather than fight them",
    "Session discussed how manual trading became obsessive, so he needed autopilot systems",
    9,
    now
))

cursor.execute("""
    INSERT INTO decisions (title, context, what_was_chosen, reasoning, what_it_reveals, evidence, significance, date_recorded)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
""", (
    "Structuring Sentinel like a virtual corporation",
    "Needed to organize complex trading bot with multiple functions",
    "Created different 'departments' communicating through messaging systems",
    "Systems thinking - treating software architecture like organizational design",
    "Bill applies organizational/business mental models to technical problems",
    "Session mentioned Sentinel structured like a virtual corporation with departments communicating through messaging",
    7,
    now
))

# ============ MISTAKES ============

cursor.execute("""
    INSERT INTO mistakes (title, what_happened, why_it_happened, pattern_category, evidence, significance, date_recorded)
    VALUES (?, ?, ?, ?, ?, ?, ?)
""", (
    "Unspoken assumptions in business partnership with Lisa",
    "Bill hoped Lisa would handle administrative side while he did technical work, but this assumption was never discussed explicitly",
    "Avoidance of difficult conversations about role expectations",
    "communication_assumption",
    "Session mentioned 'how that unspoken assumption contributed to problems'",
    7,
    now
))

# ============ REASONING PATTERNS ============

cursor.execute("""
    INSERT INTO reasoning_patterns (pattern_name, description, when_used, evidence, confidence, date_recorded)
    VALUES (?, ?, ?, ?, ?, ?)
""", (
    "Invest upfront to automate later",
    "Bill prefers to invest significant effort upfront to create systems that run themselves, rather than ongoing manual effort",
    "Applied to trading systems, likely applies to other life domains",
    "Session mentioned this as a core philosophy that 'goes beyond trading into how you approach life itself'",
    "high",
    now
))

cursor.execute("""
    INSERT INTO reasoning_patterns (pattern_name, description, when_used, evidence, confidence, date_recorded)
    VALUES (?, ?, ?, ?, ?, ?)
""", (
    "Engineer around limitations rather than fight them",
    "When Bill identifies a personal limitation (like bipolar affecting trading judgment), he designs systems to work with it rather than trying to overcome it through willpower",
    "Trading systems, likely broader application",
    "Session discussed self-awareness about bipolar and building autopilot systems that 'work with your brain chemistry rather than against it'",
    "high",
    now
))

# ============ VALUE HIERARCHIES ============

cursor.execute("""
    INSERT INTO value_hierarchies (value, sacrifice_evidence, evolution, evidence, date_recorded)
    VALUES (?, ?, ?, ?, ?)
""", (
    "Freedom from crushing responsibility",
    "Bill admitted part of him was relieved when addiction destroyed the MRI business because it freed him from 24/7 obligations",
    "The crushing weight of business responsibility may have contributed to self-destructive behavior as an unconscious escape",
    "Session mentioned 'that striking admission that part of you was relieved when addiction destroyed everything because it freed you from those obligations'",
    now
))

# ============ SELF KNOWLEDGE / INSIGHTS ============

insights = [
    ("bipolar_management", "Bill recognizes that manual trading is dangerous for him due to bipolar - it becomes obsessive and affects his judgment. He needs automated systems.", "Session on trading bots"),
    ("curiosity_origin", "Bill's lifelong scientific curiosity and desire to understand how things work was sparked in childhood, evidenced by the rabbit discovery and this very biographer project", "Session mentioned 'that childhood moment of discovery clearly planted seeds'"),
    ("mentorship_value", "Patient adults who engaged with Bill's curiosity (like Peter Underwood) were formative - people who 'actually enjoyed your endless curiosity instead of brushing you off'", "Session on Peter Underwood"),
    ("surface_vs_depth", "Bill has a drive to 'look beneath the surface and understand how things really work' - from breaking through to find rabbits, to MRI scanners, to AI trading systems", "Session summary noted this pattern"),
]

for cat, insight, evidence in insights:
    cursor.execute("""
        INSERT INTO self_knowledge (category, insight, evidence, date_realized, source)
        VALUES (?, ?, ?, ?, ?)
    """, (cat, insight, evidence, datetime.now().date().isoformat(), "biographer_session_manual"))

# ============ WISDOM ============

cursor.execute("""
    INSERT INTO wisdom (insight, domain, how_learned, when_applicable, evidence, date_recorded)
    VALUES (?, ?, ?, ?, ?, ?)
""", (
    "Build systems that accommodate your nature rather than fighting against it",
    "self_management",
    "Years of experience with bipolar and trading, recognizing that willpower alone fails",
    "Any situation where personal limitations interfere with goals",
    "Trading bot discussion - creating autopilot because manual trading was 'obsessive and unhealthy'",
    now
))

# ============ JOYS ============

cursor.execute("""
    INSERT INTO joys (joy, category, what_it_feels_like, connection_to_meaning, evidence, date_recorded)
    VALUES (?, ?, ?, ?, ?, ?)
""", (
    "Discovery - breaking through to find what's hidden",
    "intellectual",
    "The moment of finding the hidden rabbits while digging - surprise and reward for persistent curiosity",
    "Core to Bill's sense of purpose - understanding what lies beneath surfaces",
    "Peter Underwood fountain/rabbit story as paradigmatic example",
    now
))

# ============ CONTRADICTIONS ============

cursor.execute("""
    INSERT INTO contradictions (tension, how_navigated, what_it_reveals, evidence, date_recorded)
    VALUES (?, ?, ?, ?, ?)
""", (
    "Desire for accomplishment vs. relief at escape from responsibility",
    "Bill built ambitious businesses but part of him was relieved when they were destroyed, freeing him from obligations",
    "Possible tension between achievement drive and need for freedom/autonomy",
    "Admission about relief when MRI business failed due to addiction",
    now
))

# ============ STORIES ============

cursor.execute("""
    INSERT INTO stories (title, full_narrative, period, themes, emotional_weight)
    VALUES (?, ?, ?, ?, ?)
""", (
    "Peter Underwood and the Hidden Rabbits",
    "In Toronto during childhood, Bill's neighbor Peter Underwood had an English pub-style basement. Peter was a patient adult who enjoyed Bill's endless curiosity rather than brushing him off. While digging to help Peter with a fountain project, Bill broke through to discover hidden rabbits - a moment of unexpected discovery that became emblematic of his lifelong drive to look beneath surfaces.",
    "childhood",
    "mentorship,discovery,curiosity,patience",
    8
))

cursor.execute("""
    INSERT INTO stories (title, full_narrative, period, themes, emotional_weight)
    VALUES (?, ?, ?, ?, ?)
""", (
    "From $700 to $8,000 - Early Trading",
    "In the 1970s, Bill had an early trading success, turning $700 into $8,000. This experience planted seeds of both opportunity and danger that would resurface decades later in his AI trading systems.",
    "1970s",
    "trading,risk,early_success",
    6
))

cursor.execute("""
    INSERT INTO stories (title, full_narrative, period, themes, emotional_weight)
    VALUES (?, ?, ?, ?, ?)
""", (
    "Building the Trading Bot Empire",
    "Bill developed a series of trading bots - Sentinel, Onplab, and Mag7. Sentinel was structured like a virtual corporation with different departments communicating through messaging systems. This was driven by Bill's recognition that manual trading was obsessive and unhealthy for someone with bipolar disorder - he needed autopilot systems that work with his brain chemistry rather than against it.",
    "2020s",
    "trading,automation,bipolar,self-awareness,systems_thinking",
    8
))

conn.commit()
print(f"Added data from failed session extraction:")
print(f"  - Life events: {len(life_events)}")
print(f"  - Decisions: 2")
print(f"  - Mistakes: 1")
print(f"  - Reasoning patterns: 2")
print(f"  - Value hierarchies: 1")
print(f"  - Self knowledge: {len(insights)}")
print(f"  - Wisdom: 1")
print(f"  - Joys: 1")
print(f"  - Contradictions: 1")
print(f"  - Stories: 3")

# Show current counts
print("\nDatabase counts (tables with data):")
tables_to_check = [
    'self_knowledge', 'life_events', 'stories', 'decisions', 'mistakes',
    'reasoning_patterns', 'value_hierarchies', 'wisdom', 'joys',
    'contradictions', 'fears', 'transcriptions', 'philosophies'
]
for table in tables_to_check:
    try:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        if count > 0:
            print(f"  {table}: {count}")
    except Exception as e:
        pass

conn.close()
print("\nDone!")
