"""Voice Biographer Bot - Main entry point.

A conversational interview system for enriching Bill's knowledge database.

Usage:
    python main.py           # Start a voice conversation
    python main.py --text    # Text-only mode (no voice)
    python main.py --test    # Run component tests
"""

import sys
import argparse
from pathlib import Path

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from biographer.session import Session
from biographer.biographer import Biographer
from biographer.enricher import DatabaseEnricher


def run_text_mode():
    """Run in text-only mode (no voice I/O)."""
    print("=" * 60)
    print("  VOICE BIOGRAPHER BOT - Text Mode")
    print("=" * 60)
    print()
    print("Commands:")
    print("  'quit' or 'exit' - End session")
    print("  'summary' - Get session summary")
    print("  'save' - Save insights to database")
    print()

    # Initialize components
    session = Session()
    biographer = Biographer()
    enricher = DatabaseEnricher()

    # Check for previous session
    has_previous = session.load_previous_session()
    if has_previous:
        print(f"Resuming session from {session.started_at}")
        previous_context = session.get_summary()
    else:
        session.start_new_session()
        print(f"Starting new session: {session.session_id}")
        previous_context = ""

    # Analyze database for topics
    print("\nAnalyzing your knowledge database...")
    topics = biographer.analyze_database()
    session.set_topics_remaining(topics)

    # Get opening
    print()
    opening = biographer.get_opening(has_previous, previous_context)
    print(f"Biographer: {opening}")
    print()
    session.add_message("assistant", opening)

    # Main conversation loop
    conversation = session.get_conversation_context()

    while True:
        try:
            # Get user input
            user_input = input("Bill: ").strip()

            if not user_input:
                continue

            # Check for commands
            lower_input = user_input.lower()

            if lower_input in ['quit', 'exit', 'bye', 'goodbye']:
                print("\nEnding session...")
                break

            if lower_input == 'summary':
                summary = biographer.generate_summary(conversation)
                print(f"\nBiographer: {summary}\n")
                continue

            if lower_input == 'save':
                print("\nExtracting insights from conversation...")
                extractions = biographer.extract_insights(conversation)

                if extractions.get('extractions'):
                    print(enricher.preview_additions(extractions['extractions']))
                    confirm = input("\nAdd these to the database? (y/n): ").strip().lower()
                    if confirm == 'y':
                        results = enricher.process_extractions(extractions['extractions'])
                        print(f"Added {results['added']} entries, {results['skipped']} skipped, {results['errors']} errors")
                else:
                    print("No new insights to extract.")
                continue

            # Regular conversation
            session.add_message("user", user_input)
            conversation.append({"role": "user", "content": user_input})

            # Get response
            response = biographer.respond(user_input, conversation)
            print(f"\nBiographer: {response}\n")

            session.add_message("assistant", response)
            conversation.append({"role": "assistant", "content": response})

        except KeyboardInterrupt:
            print("\n\nInterrupted. Ending session...")
            break

    # End of session
    print("\n" + "=" * 60)

    # Offer summary
    summary = biographer.generate_summary(conversation)
    print(f"\nSession Summary:\n{summary}")

    # Extract and save insights
    print("\nExtracting insights...")
    extractions = biographer.extract_insights(conversation)

    if extractions.get('extractions'):
        print(enricher.preview_additions(extractions['extractions']))
        confirm = input("\nSave these insights to the database? (y/n): ").strip().lower()
        if confirm == 'y':
            results = enricher.process_extractions(extractions['extractions'])
            print(f"\nSaved {results['added']} new entries to database.")

            # Record insights in session
            for ext in extractions['extractions']:
                session.add_insight(ext)

    # End session
    session.end_session(archive=True)
    print("\nSession archived. Goodbye, Bill.")


def run_voice_mode():
    """Run with full voice I/O."""
    print("=" * 60)
    print("  VOICE BIOGRAPHER BOT")
    print("=" * 60)
    print()
    print("To end the session, say:")
    print("  'That's enough for this session' or 'OK, enough for now'")
    print("Say 'give me a summary' for a mid-session summary")
    print()

    # Import voice components (may take a moment to load models)
    print("Loading voice components...")

    try:
        from biographer.voice_input import VoiceInput
        from biographer.voice_output import SimpleTTS
    except ImportError as e:
        print(f"Voice components not available: {e}")
        print("Falling back to text mode.")
        run_text_mode()
        return

    # Initialize components
    session = Session()
    biographer = Biographer()
    enricher = DatabaseEnricher()

    try:
        voice_in = VoiceInput()  # Uses default from voice_input.py (small model)
        voice_out = SimpleTTS(volume=0.5, rate=1)  # 50% volume, slightly faster than normal
    except Exception as e:
        print(f"Error initializing voice: {e}")
        print("Falling back to text mode.")
        run_text_mode()
        return

    # Check for previous session
    has_previous = session.load_previous_session()
    if has_previous:
        print(f"Resuming session from {session.started_at}")
        previous_context = session.get_summary()
    else:
        session.start_new_session()
        print(f"Starting new session: {session.session_id}")
        previous_context = ""

    # Analyze database
    print("Analyzing your knowledge database...")
    topics = biographer.analyze_database()
    session.set_topics_remaining(topics)

    # Get and speak opening
    opening = biographer.get_opening(has_previous, previous_context)
    print(f"\nBiographer: {opening}")
    voice_out.speak(opening)
    session.add_message("assistant", opening)

    # Main conversation loop - use listen_once to avoid audio device conflicts
    conversation = session.get_conversation_context()
    should_continue = True

    print("\nListening... (speak naturally, I'll respond after you pause)")

    while should_continue:
        try:
            # Listen for one utterance (audio stream stops after transcription)
            text = voice_in.listen_once(timeout=600)  # 10 minute timeout for long stories

            if text is None or not text.strip():
                print("\n(No speech detected, still listening...)")
                continue

            print(f"\nBill: {text}")
            lower_text = text.lower().strip()

            # Check for end phrases - must be explicit session-ending statements
            end_phrases = [
                "ok enough for now", "okay enough for now",
                "let's stop the session", "end the session", "stop the interview",
                "that's enough for this session", "enough for this session",
                "that will be enough for this session", "that's enough for now",
                "let's end this session", "stop the session", "end this session"
            ]
            if any(phrase in lower_text for phrase in end_phrases):
                # Add this final message to conversation so it's included in extraction
                session.add_message("user", text)
                conversation.append({"role": "user", "content": text})
                voice_out.speak("Of course. Processing and saving now.")
                should_continue = False
                continue

            # Check for summary request
            if "summary" in lower_text or "what did we" in lower_text:
                summary = biographer.generate_summary(conversation)
                print(f"\nBiographer: {summary}")
                voice_out.speak(summary)
                print("\nListening...")
                continue

            # Regular conversation
            session.add_message("user", text)
            conversation.append({"role": "user", "content": text})

            # Get response from Claude
            print("(Thinking...)")
            response = biographer.respond(text, conversation)
            print(f"\nBiographer: {response}")

            # Speak response (audio input is stopped, so no conflict)
            voice_out.speak(response)

            session.add_message("assistant", response)
            conversation.append({"role": "assistant", "content": response})

            print("\nListening...")

        except KeyboardInterrupt:
            print("\n\nSession interrupted by user.")
            should_continue = False

    # End of session
    print("\n" + "=" * 60)
    print("Processing session...")

    try:
        # Generate summary (print only, no speech)
        print("\nGenerating session summary...")
        summary = biographer.generate_summary(conversation)
        print(f"\nSession Summary:\n{summary}")

        # Extract insights
        print("\nExtracting insights from our conversation...")
        extractions = biographer.extract_insights(conversation)

        # Always try to save raw transcription first
        if extractions.get('raw_transcription'):
            try:
                from datetime import datetime
                enricher.add_transcription(
                    session_date=datetime.now().isoformat(),
                    duration_seconds=0,
                    topic_prompt="biographer_session",
                    raw_transcription=extractions['raw_transcription']
                )
                print("Raw transcription saved.")
            except Exception as e:
                print(f"Note: Could not save raw transcription: {e}")

        if extractions.get('extractions'):
            extraction_count = len(extractions['extractions'])
            print(enricher.preview_additions(extractions['extractions']))

            # Auto-save without confirmation
            results = enricher.process_extractions(extractions['extractions'])

            if results['errors'] == 0:
                print(f"\n*** SUCCESS: Saved {results['added']} new entries to database. ***")
            else:
                print(f"\n*** PARTIAL: Saved {results['added']} entries, {results['errors']} had errors. ***")

            for ext in extractions['extractions']:
                session.add_insight(ext)
        else:
            print("No structured insights extracted, but transcription was saved.")

        # End session
        session.end_session(archive=True)
        print("*** SESSION ARCHIVED SUCCESSFULLY ***")
        voice_out.speak("All done. Session saved successfully. Until next time, Bill.")

    except Exception as e:
        error_msg = f"Error during session processing: {e}"
        print(f"\n*** ERROR: {error_msg} ***")
        print("Attempting to save session state anyway...")

        try:
            session.end_session(archive=True)
            print("Session state saved despite error.")
            voice_out.speak(f"There was an error, but I saved the session state.")
        except Exception as e2:
            print(f"*** CRITICAL: Could not save session: {e2} ***")
            voice_out.speak("Error saving session. Please check the logs.")

    print("\nGoodbye!")


def run_tests():
    """Run component tests."""
    print("Running component tests...\n")

    print("=" * 40)
    print("Testing Session Manager")
    print("=" * 40)
    from biographer.session import test_session
    test_session()

    print("\n" + "=" * 40)
    print("Testing Database Enricher")
    print("=" * 40)
    from biographer.enricher import test_enricher
    test_enricher()

    print("\n" + "=" * 40)
    print("Testing Biographer Brain")
    print("=" * 40)
    from biographer.biographer import test_biographer
    test_biographer()

    print("\n" + "=" * 40)
    print("All tests complete!")
    print("=" * 40)


def main():
    parser = argparse.ArgumentParser(
        description="Voice Biographer Bot - A conversational interview system"
    )
    parser.add_argument(
        '--text', '-t',
        action='store_true',
        help='Run in text-only mode (no voice)'
    )
    parser.add_argument(
        '--test',
        action='store_true',
        help='Run component tests'
    )
    parser.add_argument(
        '--voice', '-v',
        action='store_true',
        help='Run with voice I/O (default)'
    )

    args = parser.parse_args()

    if args.test:
        run_tests()
    elif args.text:
        run_text_mode()
    else:
        # Default to voice mode, with fallback to text
        run_voice_mode()


if __name__ == "__main__":
    main()
