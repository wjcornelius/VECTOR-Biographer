#!/usr/bin/env python3
"""
Cognitive Substrate - Voice Biographer with GUI
Main entry point for the graphical voice biographer application.
"""

import sys
import threading
import queue
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from biographer.gui.main_window import MainWindow
from biographer.gui.visualizations import MemoryVisualizer
from biographer.biographer import Biographer
from biographer.enricher import DatabaseEnricher
from biographer.session import Session as SessionManager
from biographer.voice_input import VoiceInput
from biographer.voice_output import VoiceOutput
from biographer.embeddings import VectorStore
from biographer.logger import SessionLogger, system_log


class BiographerApp:
    """Main application class integrating GUI with voice biographer."""

    def __init__(self):
        self.running = False
        self.session_active = False
        self.paused = False
        self.pause_event = threading.Event()
        self.pause_event.set()  # Start in "not paused" state

        # Message queue for thread-safe GUI updates
        self.gui_queue = queue.Queue()

        # Initialize session logger
        self.session_logger: Optional[SessionLogger] = None

        # Initialize GUI (must be in main thread)
        system_log.info("Initializing GUI...")
        self.window = MainWindow()

        # Set up GUI callbacks
        self.window.on_start_session = self.start_session
        self.window.on_end_session = self.end_session
        self.window.on_pause_session = self.pause_session
        self.window.on_resume_session = self.resume_session
        self.window.on_done_speaking = self.done_speaking
        self.window.on_visualization = self.show_visualization

        # Manual recording control
        self.user_done_speaking = threading.Event()
        self.recording_thread: Optional[threading.Thread] = None
        self.recorded_audio: List = []

        # Initialize components (some are heavy, do async)
        self.vector_store: Optional[VectorStore] = None
        self.biographer: Optional[Biographer] = None
        self.enricher: Optional[DatabaseEnricher] = None
        self.session_manager: Optional[SessionManager] = None
        self.voice_input: Optional[VoiceInput] = None
        self.voice_output: Optional[VoiceOutput] = None

        # Conversation state
        self.conversation: List[Dict[str, str]] = []
        self.all_extractions: List[Dict[str, Any]] = []

        # Schedule component initialization
        self.window.after(100, self._init_components_async)

        # Schedule GUI update loop
        self.window.after(50, self._process_gui_queue)

    def _init_components_async(self):
        """Initialize heavy components in background thread."""
        def init_worker():
            try:
                self._update_gui('status', 'Loading vector store...')
                self.vector_store = VectorStore()
                vector_count = self.vector_store.get_entry_count()
                self._update_gui('sync_status', f'{vector_count} vectors')

                self._update_gui('status', 'Loading biographer...')
                self.session_logger = SessionLogger()
                self.biographer = Biographer(
                    use_vector_store=False,  # We'll pass our own
                    session_logger=self.session_logger
                )
                self.biographer.vector_store = self.vector_store

                # Set up biographer callbacks
                self.biographer.on_memories_retrieved = lambda m: self._update_gui('memories', m)
                self.biographer.on_topic_change = lambda t: self._update_gui('topic', t)
                self.biographer.on_insights_update = lambda i: self._update_gui('insights', i)
                self.biographer.on_exploration_update = lambda e: self._update_gui('exploration', e)

                self._update_gui('status', 'Loading enricher...')
                self.enricher = DatabaseEnricher(
                    vector_store=self.vector_store,
                    session_logger=self.session_logger
                )
                self.enricher.on_entry_added = self._on_entry_added
                self.enricher.on_sync_complete = lambda s: self._update_gui('sync_status', s)

                self._update_gui('status', 'Loading session manager...')
                self.session_manager = SessionManager()

                self._update_gui('status', 'Loading voice input (Whisper)...')
                try:
                    self.voice_input = VoiceInput()
                except Exception as ve:
                    system_log.error(f"Voice input init failed: {ve}", exc_info=True)
                    raise RuntimeError(f"Voice input failed: {ve}")

                self._update_gui('status', 'Loading voice output (TTS)...')
                try:
                    self.voice_output = VoiceOutput()
                except Exception as ve:
                    system_log.error(f"Voice output init failed: {ve}", exc_info=True)
                    raise RuntimeError(f"Voice output failed: {ve}")

                # Get initial entry count
                entry_count = sum(self.enricher.get_entry_count().values())
                self._update_gui('entry_count', entry_count)

                self._update_gui('status', 'Ready')
                self._update_gui('ready', True)
                system_log.info("All components initialized successfully")

            except Exception as e:
                system_log.error(f"Component initialization failed: {e}", exc_info=True)
                self._update_gui('error', f"Initialization failed: {e}")

        threading.Thread(target=init_worker, daemon=True).start()

    def _update_gui(self, update_type: str, data: Any):
        """Queue a GUI update (thread-safe)."""
        self.gui_queue.put((update_type, data))

    def _process_gui_queue(self):
        """Process queued GUI updates (runs in main thread)."""
        try:
            while True:
                update_type, data = self.gui_queue.get_nowait()
                self._apply_gui_update(update_type, data)
        except queue.Empty:
            pass

        # ALWAYS keep processing the queue while the window is open
        # The old logic had a race condition where queue processing could stop
        # before session_complete was received
        self.window.after(50, self._process_gui_queue)

    def _apply_gui_update(self, update_type: str, data: Any):
        """Apply a GUI update in the main thread."""
        try:
            if update_type == 'status':
                self.window.recording_indicator.configure(text=str(data).upper())
            elif update_type == 'sync_status':
                self.window.set_sync_status(str(data))
            elif update_type == 'entry_count':
                self.window.set_entry_count(int(data))
            elif update_type == 'memories':
                self.window.set_memories(data)
            elif update_type == 'topic':
                self.window.set_topic(str(data))
            elif update_type == 'insights':
                self.window.update_insights(str(data))
            elif update_type == 'exploration':
                self.window.update_exploration(str(data))
            elif update_type == 'message':
                text, is_bio = data
                self.window.add_message(text, is_bio)
            elif update_type == 'recording':
                self.window.set_recording(data)
            elif update_type == 'ready':
                self.window.recording_indicator.configure(text="READY - CLICK START SESSION")
            elif update_type == 'paused':
                self.window.set_paused(data)
            elif update_type == 'error':
                self.window.update_insights(f"ERROR: {data}")
            elif update_type == 'summary':
                self.window.show_session_summary(data)
            elif update_type == 'session_complete':
                self.window.set_session_complete()
            elif update_type == 'waiting_for_response':
                self.window.set_waiting_for_response()
            elif update_type == 'set_status':
                self.window.set_status(str(data))
        except Exception as e:
            system_log.error(f"GUI update error ({update_type}): {e}")

    def _on_entry_added(self, table: str, entry_id: int):
        """Callback when a new entry is added to the database."""
        # Update entry count
        if self.enricher:
            total = sum(self.enricher.get_entry_count().values())
            self._update_gui('entry_count', total)

    def start_session(self):
        """Start a voice biographer session."""
        if self.session_active:
            return

        self.session_active = True
        self.running = True
        self.paused = False
        self.pause_event.set()  # Ensure not paused
        self.conversation = []
        self.all_extractions = []

        # Start new session logger
        self.session_logger = SessionLogger()
        if self.biographer:
            self.biographer.session_logger = self.session_logger
        if self.enricher:
            self.enricher.session_logger = self.session_logger

        system_log.info("Starting biographer session")

        # Run session in background thread
        threading.Thread(target=self._session_loop, daemon=True).start()

    def pause_session(self):
        """Pause the current session."""
        if not self.session_active or self.paused:
            return

        self.paused = True
        self.pause_event.clear()  # Block the session loop
        system_log.info("Session paused")

        if self.session_logger:
            self.session_logger.log_event('SESSION_PAUSED')

    def resume_session(self):
        """Resume a paused session."""
        if not self.session_active or not self.paused:
            return

        self.paused = False
        self.pause_event.set()  # Unblock the session loop
        self._update_gui('status', 'Resuming...')
        system_log.info("Session resumed")

        if self.session_logger:
            self.session_logger.log_event('SESSION_RESUMED')

    def done_speaking(self):
        """User clicked 'I'm Done' - stop recording and process."""
        self.user_done_speaking.set()
        if self.voice_input:
            self.voice_input.stop()

    def _session_loop(self):
        """Main session loop (runs in background thread).

        Uses MANUAL recording control - user clicks 'I'm Done' when finished speaking.
        This prevents mid-sentence cutoffs from auto-silence detection.
        """
        try:
            # Load previous session if exists
            has_previous, prev_context = False, ""
            if self.session_manager:
                state = self.session_manager.load_state()
                if state and state.get('last_summary'):
                    has_previous = True
                    prev_context = state.get('last_summary', '')

            # Generate opening
            self._update_gui('set_status', 'THINKING...')
            opening = self.biographer.get_opening(has_previous, prev_context)

            # Speak and display opening
            self._update_gui('message', (opening, True))
            self.conversation.append({'role': 'assistant', 'content': opening})

            if self.voice_output:
                self._update_gui('set_status', 'BIOGRAPHER SPEAKING...')
                self.voice_output.speak(opening)

            # Main conversation loop
            exchange_count = 0
            while self.running and self.session_active:
                exchange_count += 1
                print(f"\n{'='*60}")
                print(f"[SESSION] Starting exchange #{exchange_count}")
                print(f"{'='*60}")

                # Check if paused - wait until resumed
                if self.paused:
                    print(f"[SESSION] Paused - waiting for resume...")
                    self.pause_event.wait()  # Block here until resumed
                    if not self.running or not self.session_active:
                        print(f"[SESSION] Session ended while paused")
                        break  # Exit if session ended while paused
                    continue  # Go back to start of loop after resume

                # Signal that it's user's turn - enable the "I'm Done" button
                print(f"[SESSION] Your turn to speak - click 'I'm Done' when finished")
                self._update_gui('waiting_for_response', True)
                self._update_gui('recording', True)
                self._update_gui('set_status', f'YOUR TURN (EXCHANGE #{exchange_count})')

                # Reset the done speaking event
                self.user_done_speaking.clear()

                # Start recording - continues until user clicks "I'm Done"
                if not self.voice_input:
                    print(f"[SESSION] ERROR: voice_input is None!")
                    break

                # Listen with a VERY long timeout - user clicks "I'm Done" to stop
                # 30 minutes should be plenty for any single response
                print(f"[SESSION] Starting voice_input.listen()...")
                text = self.voice_input.listen(timeout=1800)  # 30 min max per response
                print(f"[SESSION] voice_input.listen() returned: {len(text) if text else 0} chars")

                # Check if we should exit (session ended while listening)
                if not self.running or not self.session_active:
                    print(f"[SESSION] Session ended while listening - exiting loop")
                    break

                if text is None or not text.strip():
                    # Empty response - prompt user to try again
                    print(f"[SESSION] Empty transcription - asking user to try again")
                    self._update_gui('set_status', "DIDN'T CATCH THAT - TRY AGAIN")
                    exchange_count -= 1  # Don't count empty exchanges
                    continue

                # Processing the response
                print(f"[SESSION] Got transcription: '{text[:50]}...' ({len(text)} chars)")

                # PRIORITY #1: Save raw transcription IMMEDIATELY before anything else
                # This ensures we never lose what was said, even if later processing fails
                try:
                    session_id = self.session_logger.session_id if self.session_logger else "unknown"
                    self.enricher.add_transcription(
                        session_date=session_id,
                        duration_seconds=0,  # We don't track this per-utterance
                        topic_prompt=f"Exchange #{exchange_count}",
                        raw_transcription=text
                    )
                    print(f"[SESSION] *** RAW TRANSCRIPTION SAVED TO DATABASE ***")

                    # Also log to session logger for the JSON record
                    if self.session_logger:
                        self.session_logger.log_transcription_saved(text, exchange_count)
                        self.session_logger.log_bill_speaks(text)
                except Exception as e:
                    print(f"[SESSION] WARNING: Failed to save transcription: {e}")
                    # Don't fail the whole session if this doesn't work

                self._update_gui('set_status', 'PROCESSING YOUR RESPONSE...')

                # NOTE: Exit phrase detection REMOVED - use End Session button instead
                # This prevents accidental session termination from Whisper mishearing

                # Display user's speech
                self._update_gui('message', (text, False))
                self.conversation.append({'role': 'user', 'content': text})

                # Generate response
                self._update_gui('set_status', 'BIOGRAPHER THINKING...')
                response = self.biographer.respond(text, self.conversation[:-1])

                # Display and speak response
                self._update_gui('message', (response, True))
                self.conversation.append({'role': 'assistant', 'content': response})

                if self.voice_output:
                    self._update_gui('set_status', 'BIOGRAPHER SPEAKING...')
                    self.voice_output.speak(response)

                # Extract insights after EVERY exchange for maximum capture
                # (do this AFTER speaking, not during)
                self._update_gui('set_status', 'EXTRACTING INSIGHTS...')
                self._extract_and_save_exchange()

        except Exception as e:
            system_log.error(f"Session loop error: {e}", exc_info=True)
            self._update_gui('error', str(e))

        finally:
            self._update_gui('set_status', 'SESSION ENDED')
            self.session_active = False

    def _extract_and_save_exchange(self):
        """Extract insights from the CURRENT exchange only (last 2 messages).

        This runs after every exchange for maximum capture - no information is lost
        waiting for batched extraction.
        """
        try:
            # Get just the current exchange (Bill's response + biographer's response)
            if len(self.conversation) < 2:
                return

            current_exchange = self.conversation[-2:]  # Last 2 messages only

            self._update_gui('status', 'Extracting from this exchange (Opus)...')

            # Extract insights from just this exchange
            result = self.biographer.extract_insights(current_exchange)
            extractions = result.get('extractions', [])

            if extractions:
                # Process and save
                self._update_gui('status', f'Saving {len(extractions)} insights from this exchange...')
                results = self.enricher.process_extractions(extractions, require_confirmation=False)

                # Track for session summary
                for ext in extractions:
                    ext['saved'] = True
                    self.all_extractions.append(ext)

                # Update insights display
                insights_text = self.biographer.generate_session_insights(self.all_extractions)
                self._update_gui('insights', insights_text)

                system_log.info(f"Exchange extraction: {len(extractions)} found, {results['added']} saved")
                print(f"  [EXTRACTION] {len(extractions)} entries from this exchange")
            else:
                print(f"  [EXTRACTION] No entries extracted from this exchange")

        except Exception as e:
            system_log.error(f"Exchange extraction error: {e}", exc_info=True)
            print(f"  [EXTRACTION ERROR] {e}")

    def _extract_and_save(self):
        """Extract insights from recent conversation (used at session end for any missed content)."""
        try:
            self._update_gui('status', 'Final extraction pass...')

            # Get recent conversation (last 6 messages) for any content not yet extracted
            recent = self.conversation[-6:] if len(self.conversation) > 6 else self.conversation

            # Extract insights
            result = self.biographer.extract_insights(recent)
            extractions = result.get('extractions', [])

            if extractions:
                # Process and save
                self._update_gui('status', f'Saving {len(extractions)} final insights...')
                results = self.enricher.process_extractions(extractions, require_confirmation=False)

                # Track for session summary
                for ext in extractions:
                    ext['saved'] = True
                    self.all_extractions.append(ext)

                # Update insights display
                insights_text = self.biographer.generate_session_insights(self.all_extractions)
                self._update_gui('insights', insights_text)

                system_log.info(f"Final extraction: {results['added']} entries")

        except Exception as e:
            system_log.error(f"Final extraction error: {e}", exc_info=True)

    def _end_session_internal(self):
        """End the session and show summary."""
        print(f"\n{'='*60}")
        print("[END SESSION] Starting end session process...")
        print(f"{'='*60}")
        self.running = False

        try:
            print("[END SESSION] Step 1: Final extraction...")
            self._update_gui('set_status', 'ENDING SESSION - EXTRACTING FINAL INSIGHTS...')

            # Final extraction
            if len(self.conversation) > 2:
                self._extract_and_save()
            print("[END SESSION] Step 1 complete.")

            print("[END SESSION] Step 2: Generating summary...")
            self._update_gui('set_status', 'ENDING SESSION - GENERATING SUMMARY...')

            # Generate session summary
            if self.biographer and self.session_logger:
                duration = (datetime.now() - self.session_logger.start_time).total_seconds()
                summary = self.biographer.get_full_session_summary(
                    self.conversation,
                    self.all_extractions,
                    duration
                )
                print("[END SESSION] Step 2 complete.")

                print("[END SESSION] Step 3: Saving state...")
                self._update_gui('set_status', 'ENDING SESSION - SAVING...')

                # Show summary in GUI
                self._update_gui('summary', summary)

                # Generate exploration preview
                exploration = self.biographer.generate_exploration_preview(self.conversation)
                self._update_gui('exploration', exploration)

                # Save session state
                if self.session_manager:
                    self.session_manager.save_state({
                        'conversation': self.conversation,
                        'last_summary': summary.get('summary', ''),
                        'next_topics': summary.get('next_topics', [])
                    })

                # End session log
                self.session_logger.end_session(summary)
                print("[END SESSION] Step 3 complete.")

            # Refresh counts in GUI
            print("[END SESSION] Step 4: Refreshing counts...")
            if self.enricher:
                total_entries = sum(self.enricher.get_entry_count().values())
                self._update_gui('entry_count', total_entries)
            if self.vector_store:
                vector_count = self.vector_store.get_entry_count()
                self._update_gui('sync_status', f'{vector_count} vectors')
            print("[END SESSION] Step 4 complete - counts refreshed.")

            # Signal that session is fully complete and safe to close
            print("[END SESSION] Sending session_complete signal to GUI...")
            self._update_gui('session_complete', True)
            print(f"{'='*60}")
            print("[END SESSION] *** SESSION COMPLETE - SAFE TO CLOSE ***")
            print(f"{'='*60}")
            system_log.info("Session ended successfully - safe to close")

        except Exception as e:
            print(f"[END SESSION] ERROR: {e}")
            system_log.error(f"Session end error: {e}", exc_info=True)
            self._update_gui('error', f"Error ending session: {e}")
            self._update_gui('session_complete', True)  # Still mark as complete so user can close

    def end_session(self):
        """End session (called from GUI button)."""
        self.running = False
        self.paused = False
        self.pause_event.set()  # Unblock if paused, so session loop can exit
        self.user_done_speaking.set()  # Stop any ongoing recording

        # Stop voice input if active
        if self.voice_input:
            self.voice_input.stop()

        # Run end session in background thread
        threading.Thread(target=self._end_session_internal, daemon=True).start()

    def show_visualization(self, viz_type: str):
        """Launch a visualization in the browser."""
        if not self.vector_store:
            self._update_gui('status', 'Vector store not ready yet')
            return

        self._update_gui('status', f'Generating {viz_type} visualization...')

        def run_viz():
            try:
                visualizer = MemoryVisualizer(self.vector_store)

                if viz_type == 'constellation':
                    path = visualizer.create_constellation_map(show=True)
                    msg = 'Constellation map opened in browser'
                elif viz_type == 'coverage':
                    path = visualizer.create_theme_heatmap(show=True)
                    msg = 'Coverage heatmap opened in browser'
                elif viz_type == 'clusters':
                    path = visualizer.create_cluster_view(show=True)
                    msg = 'Cluster view opened in browser'
                elif viz_type == 'gaps':
                    path = visualizer.create_gap_radar(show=True)
                    msg = 'Gap radar opened in browser'
                else:
                    msg = f'Unknown visualization type: {viz_type}'

                self._update_gui('status', msg)
                system_log.info(f"Visualization {viz_type} generated: {path}")
            except Exception as e:
                system_log.error(f"Visualization error: {e}", exc_info=True)
                self._update_gui('status', f'Visualization error: {e}')

        # Run in background to not block GUI
        threading.Thread(target=run_viz, daemon=True).start()

    def run(self):
        """Run the application."""
        self.running = True
        system_log.info("Starting Cognitive Substrate GUI")
        self.window.mainloop()
        system_log.info("GUI closed")


def main():
    """Main entry point."""
    print("=" * 60)
    print("  COGNITIVE SUBSTRATE - Voice Biographer")
    print("=" * 60)
    print()
    print("Starting GUI...")

    app = BiographerApp()
    app.run()


if __name__ == '__main__':
    main()
