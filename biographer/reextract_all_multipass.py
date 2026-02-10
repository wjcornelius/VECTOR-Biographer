"""
Re-extract ALL session transcripts using multi-pass extraction methodology.

This will process all session files and extract comprehensive data:
- FACTUAL: people, events, places, dates (50-100 entries per session)
- EMOTIONAL: joys, sorrows, wounds, fears, loves (20-40 entries)
- ANALYTICAL: patterns, wisdom, decisions, growth (20-40 entries)
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from biographer.multi_pass_extraction import MultiPassExtractor, extract_from_session
from biographer.enricher import DatabaseEnricher
from biographer.embeddings import VectorStore


def main():
    print("=" * 70)
    print("MULTI-PASS RE-EXTRACTION OF ALL SESSIONS")
    print("=" * 70)
    print()

    # Find all session files
    sessions_dir = Path(__file__).parent / "logs" / "sessions"
    session_files = sorted(sessions_dir.glob("session_*.json"))

    print(f"Found {len(session_files)} session files")
    print()

    # Initialize enricher
    enricher = DatabaseEnricher()

    # Track results
    results = {
        'started_at': datetime.now().isoformat(),
        'sessions_processed': 0,
        'total_extractions': 0,
        'extractions_by_category': {},
        'sessions': [],
        'errors': []
    }

    # Process each session
    for session_path in session_files:
        session_name = session_path.stem
        print(f"\n{'=' * 60}")
        print(f"Processing: {session_name}")
        print("=" * 60)

        try:
            # Run multi-pass extraction
            result = extract_from_session(session_path)

            if not result.get('extractions'):
                print("  No extractions found")
                results['errors'].append(f"{session_name}: No extractions")
                continue

            extractions = result['extractions']
            print(f"\n  Total extractions: {len(extractions)}")

            # Add action field and save to database
            for ext in extractions:
                ext['action'] = 'insert'
                cat = ext.get('category', 'unknown')
                results['extractions_by_category'][cat] = results['extractions_by_category'].get(cat, 0) + 1

            # Save to database
            save_result = enricher.process_extractions(extractions, require_confirmation=False)
            added = save_result.get('added', 0)

            print(f"  Added to database: {added}")

            # Track results
            results['sessions_processed'] += 1
            results['total_extractions'] += len(extractions)
            results['sessions'].append({
                'session': session_name,
                'extractions': len(extractions),
                'added': added,
                'categories': result.get('category_counts', {})
            })

        except Exception as e:
            error_msg = f"{session_name}: {str(e)}"
            print(f"  ERROR: {e}")
            results['errors'].append(error_msg)

    # Sync vector database
    print("\n" + "=" * 70)
    print("SYNCING VECTOR DATABASE")
    print("=" * 70)

    store = VectorStore()
    store.sync_from_sqlite()
    final_count = store.get_entry_count()
    print(f"Vector database now has {final_count} entries")

    # Final summary
    results['completed_at'] = datetime.now().isoformat()
    results['final_vector_count'] = final_count

    print("\n" + "=" * 70)
    print("RE-EXTRACTION COMPLETE")
    print("=" * 70)
    print(f"Sessions processed: {results['sessions_processed']}")
    print(f"Total extractions: {results['total_extractions']}")
    print(f"Vector DB entries: {final_count}")
    print()
    print("Extractions by category:")
    for cat, count in sorted(results['extractions_by_category'].items(), key=lambda x: -x[1]):
        print(f"  {cat}: {count}")

    if results['errors']:
        print()
        print(f"Errors: {len(results['errors'])}")
        for err in results['errors']:
            print(f"  - {err}")

    # Save log
    log_path = Path(__file__).parent / "logs" / "multipass_reextract_all.json"
    with open(log_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print()
    print(f"Log saved to: {log_path}")


if __name__ == '__main__':
    main()
