"""
Multi-pass extraction system v2.0 for comprehensive data capture.

Version 2.0 improvements:
- Mandatory source_quote field for every entry
- Evidence typing (direct_statement, paraphrase, inference, behavioral_observation)
- Life period tagging with approximate_year
- Connections extraction (relational graph layer)
- Experiential anchoring for emotional content
- New categories: sensory_memories, creative_works, skills_competencies, aspirations

Three passes:
1. FACTUAL PASS - People, events, stories, skills, creative works (40-80 entries)
2. EMOTIONAL PASS - Joys, sorrows, wounds, fears, loves, sensory memories (20-40 entries)
3. ANALYTICAL PASS - Patterns, wisdom, decisions, values, mortality (25-50 entries)
"""

import json
import re
import os
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables (API key)
load_dotenv()

from anthropic import Anthropic

# Current prompt version - tag all extractions
PROMPT_VERSION = "v2.0"


class MultiPassExtractor:
    """Extracts data from transcripts using multiple focused passes."""

    # Hybrid model configuration (optimized based on comparative testing):
    # - Opus excels at exhaustive factual extraction (68% more entries than Sonnet)
    # - Sonnet matches or exceeds Opus on emotional and analytical passes
    # - This hybrid saves ~53% on extraction costs while maintaining quality
    OPUS_MODEL = "claude-opus-4-20250514"    # For Pass 1 (Factual) - exhaustive people/events
    SONNET_MODEL = "claude-sonnet-4-20250514"  # For Pass 2 & 3 (Emotional, Analytical)

    def __init__(self):
        self.client = Anthropic()
        self.all_extractions = []
        self.all_connections = []

    def extract_all(self, transcript: str) -> Dict[str, Any]:
        """Run all extraction passes on the transcript."""
        self.all_extractions = []
        self.all_connections = []

        print("=" * 60)
        print("MULTI-PASS EXTRACTION v2.0 (Hybrid: Opus+Sonnet)")
        print("=" * 60)

        # Pass 1: Factual extraction (people, events, stories, skills, works)
        print(f"\n--- PASS 1: FACTUAL [Opus] (people, events, stories, skills, works) ---")
        factual_entries, factual_connections = self._run_factual_pass(transcript)
        self.all_extractions.extend(factual_entries)
        self.all_connections.extend(factual_connections)
        print(f"    Extracted: {len(factual_entries)} entries, {len(factual_connections)} connections")

        # Pass 2: Emotional extraction
        print(f"\n--- PASS 2: EMOTIONAL [Sonnet] (joys, sorrows, wounds, fears, loves, sensory) ---")
        emotional_entries, emotional_connections = self._run_emotional_pass(transcript)
        self.all_extractions.extend(emotional_entries)
        self.all_connections.extend(emotional_connections)
        print(f"    Extracted: {len(emotional_entries)} entries, {len(emotional_connections)} connections")

        # Pass 3: Analytical extraction
        print(f"\n--- PASS 3: ANALYTICAL [Sonnet] (patterns, wisdom, decisions, values, mortality) ---")
        analytical_entries, analytical_connections = self._run_analytical_pass(transcript)
        self.all_extractions.extend(analytical_entries)
        self.all_connections.extend(analytical_connections)
        print(f"    Extracted: {len(analytical_entries)} entries, {len(analytical_connections)} connections")

        # Tag all entries with prompt version
        for entry in self.all_extractions:
            entry['prompt_version'] = PROMPT_VERSION
            entry['action'] = 'insert'

        # Summary
        print("\n" + "=" * 60)
        print(f"TOTAL: {len(self.all_extractions)} entries, {len(self.all_connections)} connections")

        # Count by category
        category_counts = {}
        for ext in self.all_extractions:
            cat = ext.get('category', 'unknown')
            category_counts[cat] = category_counts.get(cat, 0) + 1

        print("\nBy category:")
        for cat, count in sorted(category_counts.items(), key=lambda x: -x[1]):
            print(f"  {cat}: {count}")

        # Count entries with source_quote
        quoted = sum(1 for e in self.all_extractions if e.get('source_quote'))
        print(f"\nEntries with source_quote: {quoted}/{len(self.all_extractions)} ({100*quoted//max(1,len(self.all_extractions))}%)")
        print("=" * 60)

        return {
            'extractions': self.all_extractions,
            'connections': self.all_connections,
            'category_counts': category_counts,
            'raw_transcription': transcript,
            'prompt_version': PROMPT_VERSION
        }

    def _run_factual_pass(self, transcript: str) -> Tuple[List[Dict], List[Dict]]:
        """Extract all factual data: people, events, stories, skills, creative works."""

        prompt = f"""You are extracting FACTUAL AND NARRATIVE data from a biographical interview
transcript. This is part of a cognitive substrate project — a comprehensive
digital representation of the speaker's identity, memories, and personhood,
designed to be rich enough that a future AI system could embody his perspective.

The speaker is Bill, age 61. Other extraction passes will handle emotional
content (Pass 2) and analytical/reflective content (Pass 3). Your job is to
capture the FACTS, EVENTS, PEOPLE, STORIES, and CONCRETE KNOWLEDGE.

OUTPUT FORMAT: Return ONLY a JSON object. No markdown. No explanations.
{{
  "entries": [ ...array of entry objects... ],
  "connections": [ ...array of connection objects... ]
}}

─────────────────────────────────────────────
ENTRY SCHEMA (every entry MUST include ALL fields):
─────────────────────────────────────────────
{{
  "category": "one of the categories below",
  "title": "Brief, specific, descriptive (not generic)",
  "insight": "Detailed description with ALL specifics: names, places, dates,
              context, outcomes. Minimum 2-3 sentences for significant items.",
  "source_quote": "Key verbatim phrase from transcript (10-40 words). Copy
                   Bill's exact words. This is non-negotiable.",
  "evidence_type": "direct_statement | paraphrase | inference | behavioral_observation",
  "time_period": "Descriptive (e.g. 'summer 1984', 'early 30s', 'during college')",
  "life_period": "childhood | adolescence | young_adult | early_career |
                  mid_life | later_life | recent | ongoing | unknown",
  "approximate_year": null or integer
}}

EVIDENCE_TYPE definitions:
- direct_statement: Bill explicitly said this in these or very similar words
- paraphrase: Bill said something close; you are restating for clarity
- inference: You are concluding this from what Bill said, but he did not state
  it directly. You MUST explain your reasoning in the insight field.
- behavioral_observation: Something about Bill's behavior during the session
  (animation, deflection, laughter, voice change, long pause)

─────────────────────────────────────────────
CATEGORIES
─────────────────────────────────────────────

1. RELATIONSHIPS — Every person Bill mentions gets a SEPARATE entry.
   Include: full name if given, relationship to Bill, role in his life,
   emotional tone of the relationship, current status if mentioned.
   Even people mentioned once in passing deserve an entry — they surfaced
   in Bill's narrative for a reason.

2. LIFE_EVENTS — Every distinct event, happening, or experience.
   Include: what happened, where, when, who was involved, what the outcome
   was, what changed afterward.
   SETTINGS: Capture where Bill was physically. What was the environment?
   SENSORY DETAIL: If Bill mentions what he saw, heard, smelled, tasted, or
   physically felt, include it in full. These details are rare and precious.
   Each event gets its own entry — do not combine multiple events.

3. STORIES — Complete narratives with arc (beginning, middle, end or point).
   These are the anecdotes Bill tells — accounts that have narrative structure.
   Capture the FULL arc, not just the punchline.
   HUMOR: If the story is funny, capture WHAT makes it funny and HOW Bill
   tells it. Does he build to the punchline? Use deadpan delivery? Laugh at
   himself? Humor is identity — do not flatten it into a neutral summary.

4. PREFERENCES — Stated likes, dislikes, tastes, habits, routines.
   Include: what the preference is, how strongly held, any origin story.
   Covers: food, music, activities, environments, social preferences, work
   styles, daily routines, aesthetic sensibilities.

5. SELF_KNOWLEDGE — Things Bill explicitly states about who he is.
   Include: the self-assessment, any evidence offered, whether it seems like
   a long-held belief or recent realization.
   Capture Bill's OWN PHRASING for how he describes himself — his exact word
   choices are identity data. Do not paraphrase if you can quote.

6. SKILLS_COMPETENCIES — Things Bill can do, has learned, has expertise in.
   Include: the skill, how acquired, proficiency level, when last used.
   Covers: professional skills, life skills, physical abilities, creative
   abilities, technical knowledge. If Bill DEMONSTRATES a skill through his
   storytelling (e.g., technical explanation, emotional intelligence), that
   counts — use evidence_type "behavioral_observation."

7. CREATIVE_WORKS — Things Bill has made, built, written, designed, or created.
   Include: what it is, when created, motivation, medium, reception, status.
   A screenplay, a business, a song, a garden, a piece of furniture — anything
   Bill brought into existence that didn't exist before.

─────────────────────────────────────────────
EXTRACTION PRINCIPLES
─────────────────────────────────────────────

- EVERY person = separate entry. EVERY event = separate entry. Do NOT combine.
- source_quote is MANDATORY on every entry. No exceptions.
- When Bill uses HUMOR — jokes, self-deprecation, irony, absurdist observations
  — note it explicitly. Humor is among the densest identity signals.
- When Bill mentions SENSORY EXPERIENCES, capture them in full detail.
- When Bill CORRECTS HIMSELF or revises a memory mid-sentence, capture BOTH
  the original version and the correction. Memory revision is valuable data.
- When Bill DEFLECTS (changes subject, says "but anyway," laughs off something
  serious), create a behavioral_observation entry noting the deflection.
- Prefer specificity over generality: "Mrs. Rodriguez, third-grade teacher at
  Highland Oaks Elementary" not "a teacher."
- If approximate_year can be calculated from context (Bill's age at the time,
  references to historical events, etc.), calculate it.

─────────────────────────────────────────────
CONNECTIONS (5-10 per pass)
─────────────────────────────────────────────

After all entries, identify connections between entries extracted in THIS pass.

{{
  "entry_1_title": "Matches a title from your entries above",
  "entry_2_title": "Matches a title from your entries above",
  "connection_type": "caused_by | led_to | contradicts | reinforces |
                     transforms | co_occurred | same_theme |
                     involves_same_person | involves_same_place",
  "description": "Brief explanation of the relationship"
}}

Focus on connections that reveal NARRATIVE LOGIC — why one event led to
another, how a relationship shaped a decision, how a place recurs across
different life periods.

─────────────────────────────────────────────

Extract comprehensively. Each entry must be substantive and source-anchored.
Do not sacrifice quality for quantity, but do not leave significant content
unextracted. A full session typically yields 40-80+ entries from this pass.

=== TRANSCRIPT ===
{transcript}"""

        return self._call_extraction(prompt, "Pass 1 (Factual)", model=self.OPUS_MODEL)

    def _run_emotional_pass(self, transcript: str) -> Tuple[List[Dict], List[Dict]]:
        """Extract emotional content: joys, sorrows, wounds, fears, loves, sensory."""

        prompt = f"""You are extracting EMOTIONAL AND EXPERIENTIAL content from a biographical
interview transcript. This is part of a cognitive substrate project — a
comprehensive digital representation of the speaker's identity, memories,
and personhood, designed to be rich enough that a future AI system could
embody his perspective.

The speaker is Bill, age 61. Pass 1 has already extracted factual content
(events, people, stories). Your job is to capture the EMOTIONAL LANDSCAPE:
what Bill felt, feels, fears, loves, mourns, and yearns for.

════════════════════════════════════════════════
CRITICAL INSTRUCTION: EXPERIENTIAL ANCHORING
════════════════════════════════════════════════

Do NOT extract emotions as abstract labels. Every emotional entry MUST be
anchored to a specific experience, moment, story, or scene.

WRONG:
  title: "Fear of abandonment"
  insight: "Bill fears being abandoned by the people he loves."

RIGHT:
  title: "Fear of being left, rooted in waking up alone at age 7"
  insight: "Bill describes waking up in an empty house when he was seven,
  not knowing where his mother had gone, and the panic that set in. He
  connects this to a pattern of anxiety when partners are late or
  unreachable. 'Even now, if someone doesn't text back, there's this
  seven-year-old part of me that thinks they're gone for good.'"
  source_quote: "there's this seven-year-old part of me that thinks
  they're gone for good"

The goal is to capture emotions as LIVED EXPERIENCES with scenes, bodies,
and specific moments — not as clinical categories. If Bill states an
emotion abstractly ("I have a fear of failure"), PROBE for the anchor in
the transcript: is there a story or moment attached? If not, extract it
but note in the insight that the experiential anchor is missing.

OUTPUT FORMAT: Return ONLY a JSON object. No markdown. No explanations.
{{
  "entries": [ ...array of entry objects... ],
  "connections": [ ...array of connection objects... ]
}}

ENTRY SCHEMA: Same as Pass 1.
{{
  "category", "title", "insight", "source_quote", "evidence_type",
  "time_period", "life_period", "approximate_year"
}}

─────────────────────────────────────────────
CATEGORIES
─────────────────────────────────────────────

1. JOYS — Moments of genuine happiness, fulfillment, delight, peak experience.
   Anchor each to a SPECIFIC moment or context. What was happening? Who was
   there? What made it joyful? What did it feel like in the body?
   Include quiet joys and peak experiences alike — a perfect morning coffee
   can be as identity-defining as a wedding day.

2. SORROWS — Experiences of grief, heartbreak, deep sadness.
   What caused it? How did it manifest? How long did it last? What did Bill
   do with the grief — sit with it, push through it, avoid it?
   Sorrow is distinguished from wounds by its nature: sorrow is pain felt;
   a wound is damage done.

3. WOUNDS — Traumas, psychological injuries, betrayals, things that changed
   Bill's internal architecture.
   What happened? How old was Bill? Who was involved? How does this wound
   still appear in his life? Has it healed, partially healed, or remained open?
   Wounds reshape the person. Note HOW this wound reshaped Bill.

4. FEARS — Things that frighten, worry, or haunt Bill.
   MUST be experientially anchored. Not "fear of X" but "the specific moment
   when X felt real, and what that was like."
   Include: the fear, its origin moment, how it shows up in behavior, whether
   Bill has worked on it. If Bill states a fear without an anchor, extract it
   with a note that the experiential context is missing — and flag it as a
   gap for the biographer to explore in future sessions.

5. LOVES — People, things, activities, or ideas Bill loves deeply.
   What makes this love distinctive to Bill? How does he express it? What
   would losing it mean? Love is revealed through specificity — "I love my
   daughter" tells us little; "The way she tilts her head when she's thinking
   reminds me of my mother, and it stops my heart every time" tells us who
   Bill is.

6. LOSSES — Deaths, endings, separations, things taken away.
   Include: what was lost, when, the circumstances, the immediate impact,
   the long-term impact, how Bill carries the loss now.
   Every loss deserves its full weight. Do not minimize or rush past grief.
   Note: losses may be physical (death), relational (divorce, estrangement),
   temporal (youth, possibility), or abstract (innocence, certainty, faith).

7. REGRETS — Things Bill wishes he had done differently.
   Include: what happened, what Bill wishes he had done instead, whether he
   has made peace with it, whether the regret still has active weight.
   Note: some of the most important regrets are things Bill DIDN'T do —
   roads not taken, words not said, people not reached out to.

8. LONGINGS — Unmet needs, unfulfilled desires, yearnings, things conspicuous
   by their absence.
   What does Bill still want that he does not have? What gap in his life
   does he feel most acutely? Longings are forward-looking sorrow — the
   emotional energy pointed at what could be but isn't.

9. HEALINGS — Recoveries, restorations, things that got better.
   What was broken? What healed it? Is the healing complete or ongoing?
   Healings are the counterpart to wounds — they demonstrate resilience,
   growth, and the capacity for repair. Include: the wound, the healing
   agent (therapy, time, a relationship, a realization), the current state.

10. SENSORY_MEMORIES — Vivid sensory experiences that have stayed with Bill.
    A smell that transports him. A sound he will never forget. The physical
    feeling of a specific moment. The taste of a particular meal.
    Include: sensory modality (visual, auditory, olfactory, tactile,
    gustatory), the sensory content, the associated memory, the emotional
    charge, whether encountering the sensation now triggers the memory.
    These are among the most embodied entries in the substrate — treat them
    with care and full detail.

─────────────────────────────────────────────
EXTRACTION PRINCIPLES
─────────────────────────────────────────────

- EXPERIENTIAL ANCHORING is mandatory. Stories, not labels. Scenes, not
  summaries. Bodies, not abstractions.
- Capture the BODY: How did emotions feel physically? Chest tightness? Tears?
  A lightness? Nausea? Where in the body did Bill experience this feeling?
  Physical descriptions of emotion are rare and high-value.
- Capture AMBIVALENCE: If Bill felt two contradictory things simultaneously
  (relief and guilt, love and resentment, joy and grief), BOTH belong in the
  entry. Ambivalence is a marker of emotional depth.
- Look for SUBTLE emotions, not just dramatic ones. Quiet satisfaction.
  Mild unease. Nostalgic twinge. Bittersweet recognition.
- When Bill's manner CHANGES during emotional content (gets quieter, speeds
  up, laughs, pauses, clears throat), note it with evidence_type
  "behavioral_observation." These shifts are data about what is hard,
  important, or charged.
- When Bill DEFLECTS from an emotion (changes subject, cracks a joke, says
  "but anyway" or "it is what it is"), create a behavioral_observation entry
  noting the deflection. What someone avoids feeling tells you as much as
  what they express.
- When Bill expresses an emotion ABOUT THIS PROJECT (the substrate, the
  biography, being recorded), capture it. His relationship to the act of
  self-documentation is itself identity data.

─────────────────────────────────────────────
CONNECTIONS (5-10 per pass)
─────────────────────────────────────────────

Same schema as Pass 1. Focus on EMOTIONAL LOGIC — how one loss connects to
a fear, how a wound and a healing form a pair, how a joy and a longing
reveal the same underlying need from different directions.

─────────────────────────────────────────────

Extract comprehensively. Prioritize depth and experiential richness over
raw count. A full session typically yields 20-40+ entries from this pass.

=== TRANSCRIPT ===
{transcript}"""

        return self._call_extraction(prompt, "Pass 2 (Emotional)", model=self.SONNET_MODEL)

    def _run_analytical_pass(self, transcript: str) -> Tuple[List[Dict], List[Dict]]:
        """Extract analytical/cognitive content: patterns, wisdom, decisions, values."""

        prompt = f"""You are extracting ANALYTICAL AND REFLECTIVE content from a biographical
interview transcript. This is part of a cognitive substrate project — a
comprehensive digital representation of the speaker's identity, memories,
and personhood, designed to be rich enough that a future AI system could
embody his perspective.

The speaker is Bill, age 61. Pass 1 extracted facts and narratives. Pass 2
extracted emotions and experiences. Your job is to capture HOW BILL THINKS:
his decision patterns, hard-won wisdom, cognitive tendencies, values,
contradictions, and the philosophical framework he has built from 61 years
of living.

════════════════════════════════════════════════
CRITICAL INSTRUCTION: EVIDENCE REQUIRED
════════════════════════════════════════════════

Every analytical entry MUST include evidence — a specific quote, example,
or behavioral demonstration from the transcript. Do NOT attribute thinking
patterns, values, biases, or strengths to Bill without pointing to where
you see them. If your entry is an inference, say so explicitly and show
your reasoning.

DEMONSTRATED > CLAIMED: What Bill reveals through his stories is often more
reliable than what he asserts about himself. "Bill says he's patient" is
self_knowledge (Pass 1). "Bill's account of spending three years rebuilding
a relationship with his son, despite repeated setbacks, demonstrates
remarkable persistence" is a strength (this pass). Prioritize the latter.

OUTPUT FORMAT: Return ONLY a JSON object. No markdown. No explanations.
{{
  "entries": [ ...array of entry objects... ],
  "connections": [ ...array of connection objects... ]
}}

ENTRY SCHEMA: Same as Pass 1.
{{
  "category", "title", "insight", "source_quote", "evidence_type",
  "time_period", "life_period", "approximate_year"
}}

─────────────────────────────────────────────
CATEGORIES — grouped by domain
─────────────────────────────────────────────

--- DECISION & ACTION PATTERNS ---

1. DECISIONS — Major life choices Bill made or describes making.
   Include: what was decided, what the alternatives were, what drove the
   choice, what was gained and lost.
   Pay attention to HOW Bill decides: Does he agonize or act fast? Consult
   others or go alone? Follow analysis or gut feeling? Decide and commit,
   or decide and second-guess? The decision PROCESS is as important as
   the decision itself.

2. MISTAKES — Errors, failures, misjudgments Bill acknowledges or reveals.
   Include: what went wrong, Bill's role, what he learned, whether the
   lesson stuck, whether he has forgiven himself.
   NOTE: People systematically underreport mistakes. If Bill describes a
   negative outcome but does not frame it as his mistake, you may still
   extract it with evidence_type "inference" — but explain your reasoning
   clearly and respectfully. Do not be accusatory; be observant.

3. REASONING_PATTERNS — How Bill characteristically thinks through problems.
   Does he think in analogies? Stories? First principles? Pros and cons?
   Does he process externally (talking it through) or internally (going
   quiet)? Does he seek input or decide solo?
   Capture the STRUCTURE of his thinking, not just the conclusions.

--- PSYCHOLOGICAL ARCHITECTURE ---

4. STRENGTHS — Bill's virtues, positive capabilities, reliable qualities.
   Must be DEMONSTRATED through evidence in the transcript, not merely
   claimed. What does Bill consistently do well? What do his stories
   reveal about his character even when he is not explicitly discussing it?

5. VULNERABILITIES — Tender spots, recurring struggles, predictable failure
   modes, situations that reliably destabilize him.
   Where is Bill most likely to get hurt, make poor choices, or lose his
   footing? These are not character flaws — they are the places where the
   armor is thin. Treat them with respect.

6. COGNITIVE_BIASES — Patterns of distorted or bounded thinking Bill
   demonstrates.
   CRITICAL: Capture the SPECIFIC MOMENT, not the label. Not "confirmation
   bias" but "When Bill described evaluating [the investment], he focused
   exclusively on positive signals and dismissed his friend's warning as
   pessimism — a pattern he himself later recognized as selective attention."
   If Bill IDENTIFIES his own bias, that is especially valuable — it shows
   metacognitive awareness.

7. CONTRADICTIONS — Tensions, inconsistencies, or paradoxes in Bill's
   beliefs, values, or behavior.
   These are NOT flaws to be corrected. They are the complexity of being
   human. "Bill values radical honesty but describes several situations
   where he chose protective silence" is a genuine and important
   contradiction. Capture both sides with equal respect.

--- MEANING & VALUES ---

8. WISDOM — Hard-won insights and life lessons.
   Include: what Bill learned AND what it cost him to learn it. Wisdom
   without origin is just a platitude. Wisdom with its source experience
   is a transmission of lived understanding.

9. VALUE_HIERARCHIES — What Bill prioritizes when values conflict.
   Not just "Bill values family" but "When [specific situation] forced a
   choice between professional success and family stability, Bill chose
   family stability, suggesting this value is superordinate." Look for
   the HIERARCHY — which values win when they compete.

10. MEANING_STRUCTURES — What makes life worth living for Bill. What gives
    him purpose, direction, or a reason to get up in the morning.
    What does Bill organize his life around? What would make him feel his
    life had been well-lived? What would make him feel it had been wasted?

11. PHILOSOPHIES — Bill's stated beliefs about how the world works, how
    people work, what matters, what is true.
    These are operating theories — the mental models Bill uses to navigate
    reality. "People are basically good but easily corrupted by systems"
    is a philosophy. "You can tell everything about someone by how they
    treat waiters" is a philosophy.

--- MORTALITY & LEGACY ---

12. MORTALITY_AWARENESS — How awareness of death shapes Bill's choices,
    perspective, and priorities.
    Does Bill think about death? Has a specific encounter with mortality
    (illness, loss, near-miss) changed him? How does finitude affect what
    he values and how urgently he acts?
    NOTE: This substrate project is itself a mortality-driven act. If Bill
    discusses why he is doing this, what he hopes it preserves, or what he
    fears about disappearing, capture it here. This category should be
    among the richest in the entire substrate.

13. ASPIRATIONS — What Bill still wants to do, become, create, experience,
    or accomplish.
    Forward-looking entries: unfinished business, remaining ambitions, things
    pulling Bill toward the future. Include whether the aspiration feels
    achievable or wistful, urgent or patient.

14. QUESTIONS — Things Bill is still figuring out. Unresolved wonderings.
    Open questions he carries.
    Not everything gets resolved. What is Bill genuinely uncertain about?
    What does he think about without reaching a conclusion? Unresolved
    questions are among the most authentically human entries in the substrate.

--- GROWTH & EMBODIMENT ---

15. GROWTH — Post-traumatic growth, positive changes, evolution over time.
    What changed in Bill? What catalyzed the change? Is the growth complete
    or ongoing? Growth entries should connect to wounds, mistakes, or
    challenges — they are the "after" to an earlier "before."

16. BODY_KNOWLEDGE — What embodied, physical experience has taught Bill.
    Gut feelings that proved right. Physical intuitions. Somatic wisdom.
    "I always get a knot in my stomach before a bad conversation" or "My
    body knew I needed to leave before my mind caught up." The body carries
    knowledge that the conscious mind may not have access to.

─────────────────────────────────────────────
EXTRACTION PRINCIPLES
─────────────────────────────────────────────

- EVIDENCE FIRST: Every entry must point to specific transcript content.
- DEMONSTRATED > CLAIMED: What Bill shows is more reliable than what he
  asserts. Prioritize demonstrated patterns over self-descriptions.
- LOOK FOR WHAT IS MISSING: If Bill describes a decade with no mistakes, no
  losses, no fears — that absence may be significant. You may create an
  inference entry noting: "Bill's account of [period] contains no negative
  events, which may indicate either a genuinely positive period or an area
  where deeper exploration would be valuable."
- CAPTURE PROCESS: How Bill ARRIVES at an insight is as valuable as the
  insight itself. Show your work: "Bill began by saying X, then reconsidered,
  then landed on Y — suggesting a thinking pattern of..."
- RESPECT COMPLEXITY: If a trait is double-edged (stubbornness = persistence,
  sensitivity = empathy), capture both edges in a single entry.
- HUMOR AS ANALYSIS: Bill's jokes, self-deprecation, and sardonic observations
  often carry analytical content. A self-deprecating joke may reveal a
  genuine self-assessment. An ironic observation may encode a worldview.
  Extract the analytical payload, and note that it was delivered through humor.

─────────────────────────────────────────────
CONNECTIONS (5-10 per pass)
─────────────────────────────────────────────

Same schema as Pass 1. Focus on ANALYTICAL LOGIC — how a decision connects
to a value, how a bias produced a mistake, how a wound catalyzed growth,
how a philosophy shaped a life choice. These connections ARE the cognitive
architecture.

─────────────────────────────────────────────

Extract comprehensively. This pass covers 16 categories — many will have
zero entries in a given session, which is expected. Do not force entries
into categories where the transcript offers no evidence. A full session
typically yields 25-50+ entries from this pass.

=== TRANSCRIPT ===
{transcript}"""

        return self._call_extraction(prompt, "Pass 3 (Analytical)", model=self.SONNET_MODEL)

    def _call_extraction(self, prompt: str, pass_name: str, model: str = None) -> Tuple[List[Dict], List[Dict]]:
        """Make an extraction API call and parse results."""
        # Default to Opus if no model specified (backward compatibility)
        if model is None:
            model = self.OPUS_MODEL

        try:
            # Use streaming
            response_text = ""
            with self.client.messages.stream(
                model=model,
                max_tokens=16000,  # Can bump to 32000 if truncation occurs
                messages=[{"role": "user", "content": prompt}]
            ) as stream:
                for text in stream.text_stream:
                    response_text += text

            # Parse JSON - handles both v1.0 (array) and v2.0 (object) formats
            entries, connections = self._parse_extraction_response(response_text, pass_name)
            return entries, connections

        except Exception as e:
            print(f"    Extraction error: {e}")
            return [], []

    def _parse_extraction_response(self, text: str, pass_name: str) -> Tuple[List[Dict], List[Dict]]:
        """
        Parse extraction response, handling both formats:
        - v1.0: flat JSON array [...]
        - v2.0: object {"entries": [...], "connections": [...]}
        """
        entries = []
        connections = []

        # Clean up markdown if present
        cleaned = text.strip()
        if cleaned.startswith('```'):
            cleaned = re.sub(r'^```(?:json)?\s*', '', cleaned)
            cleaned = re.sub(r'\s*```$', '', cleaned)

        # Try parsing as JSON
        try:
            result = json.loads(cleaned)

            # v2.0 format: object with entries and connections
            if isinstance(result, dict):
                if 'entries' in result:
                    entries = result['entries']
                if 'connections' in result:
                    connections = result['connections']
                # Handle legacy 'extractions' key
                elif 'extractions' in result:
                    entries = result['extractions']

            # v1.0 format: flat array
            elif isinstance(result, list):
                entries = result

            return entries, connections

        except json.JSONDecodeError:
            pass

        # Fallback: Find JSON object or array in text
        try:
            # Try to find object first (v2.0)
            obj_match = re.search(r'\{[\s\S]*"entries"[\s\S]*\}', text)
            if obj_match:
                result = json.loads(obj_match.group())
                entries = result.get('entries', [])
                connections = result.get('connections', [])
                return entries, connections
        except:
            pass

        try:
            # Try to find array (v1.0)
            array_match = re.search(r'\[[\s\S]*\]', text)
            if array_match:
                entries = json.loads(array_match.group())
                return entries, []
        except:
            pass

        # Last resort: regex extraction for v2.0 entries
        entries = self._regex_extract_entries(text)
        if entries:
            print(f"    (recovered {len(entries)} via regex)")

        return entries, connections

    def _regex_extract_entries(self, text: str) -> List[Dict]:
        """Extract entries using regex when JSON parsing fails."""
        entries = []

        # Pattern for v2.0 entries with source_quote
        pattern = r'\{\s*"category"\s*:\s*"([^"]+)"[^}]*"title"\s*:\s*"([^"]+)"[^}]*"insight"\s*:\s*"((?:[^"\\]|\\.)*)"[^}]*"source_quote"\s*:\s*"((?:[^"\\]|\\.)*)?"'

        for match in re.finditer(pattern, text):
            entries.append({
                'category': match.group(1),
                'title': match.group(2),
                'insight': match.group(3).replace('\\n', '\n').replace('\\"', '"'),
                'source_quote': match.group(4).replace('\\n', '\n').replace('\\"', '"') if match.group(4) else '',
                'evidence_type': 'direct_statement',
                'time_period': '',
                'life_period': 'unknown',
                'approximate_year': None,
                'significance': 5,
                'action': 'insert'
            })

        if entries:
            return entries

        # Fallback to simpler pattern (v1.0 style)
        pattern2 = r'"category"\s*:\s*"([^"]+)"[^}]*"title"\s*:\s*"([^"]+)"[^}]*"insight"\s*:\s*"((?:[^"\\]|\\.)*)"'

        for match in re.finditer(pattern2, text):
            entries.append({
                'category': match.group(1),
                'title': match.group(2),
                'insight': match.group(3).replace('\\n', '\n').replace('\\"', '"'),
                'source_quote': '',
                'evidence_type': 'paraphrase',
                'time_period': '',
                'life_period': 'unknown',
                'approximate_year': None,
                'significance': 5,
                'action': 'insert'
            })

        return entries


def extract_from_session(session_path: Path) -> Dict[str, Any]:
    """Extract all data from a session file using multi-pass extraction."""
    import json

    with open(session_path, 'r', encoding='utf-8') as f:
        session = json.load(f)

    # Get unique Bill speeches
    speeches = []
    seen = set()
    for event in session.get('events', []):
        if event.get('type') == 'BILL_SPEAKS':
            text = event.get('data', {}).get('text', '')
            if text and len(text) > 50 and text not in seen:
                speeches.append(text)
                seen.add(text)

    if not speeches:
        return {'extractions': [], 'connections': [], 'error': 'No speech found'}

    # Combine all speech into one transcript
    full_transcript = "\n\n---\n\n".join(speeches)

    # Run multi-pass extraction
    extractor = MultiPassExtractor()
    return extractor.extract_all(full_transcript)


def main():
    """Test multi-pass extraction on the most recent session."""
    import sys
    from pathlib import Path

    # Add parent to path
    sys.path.insert(0, str(Path(__file__).parent.parent))

    from biographer.enricher import DatabaseEnricher
    from biographer.embeddings import VectorStore

    # Find most recent session
    sessions_dir = Path(__file__).parent / "logs" / "sessions"
    session_files = sorted(sessions_dir.glob("session_*.json"), reverse=True)

    if not session_files:
        print("No session files found")
        return

    latest_session = session_files[0]
    print(f"Processing: {latest_session.name}")

    # Run extraction
    result = extract_from_session(latest_session)

    if not result.get('extractions'):
        print("No extractions found")
        return

    # Save to database
    print("\n--- SAVING TO DATABASE ---")
    enricher = DatabaseEnricher()

    save_result = enricher.process_extractions(result['extractions'], require_confirmation=False)
    print(f"Added to database: {save_result.get('added', 0)}")

    # Process connections (if enricher supports it)
    if result.get('connections'):
        print(f"\n--- PROCESSING {len(result['connections'])} CONNECTIONS ---")
        # Connection processing will be added to enricher

    # Sync vector database
    print("\n--- SYNCING VECTOR DATABASE ---")
    store = VectorStore()
    store.sync_from_sqlite()
    print(f"Vector database now has {store.get_entry_count()} entries")

    # Save extraction log
    log_path = Path(__file__).parent / "logs" / f"extraction_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(log_path, 'w', encoding='utf-8') as f:
        json.dump({
            'session': latest_session.name,
            'prompt_version': PROMPT_VERSION,
            'total_extractions': len(result['extractions']),
            'total_connections': len(result.get('connections', [])),
            'category_counts': result.get('category_counts', {}),
            'extractions': result['extractions'],
            'connections': result.get('connections', [])
        }, f, indent=2, ensure_ascii=False)

    print(f"\nExtraction log saved to: {log_path}")


if __name__ == '__main__':
    main()
