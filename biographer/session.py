"""Session management for maintaining conversation continuity."""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any


class Session:
    """Manages conversation sessions with persistence."""

    def __init__(self, session_dir: Optional[Path] = None):
        if session_dir is None:
            session_dir = Path(__file__).parent / "sessions"
        self.session_dir = Path(session_dir)
        self.session_dir.mkdir(parents=True, exist_ok=True)

        self.current_session_file = self.session_dir / "current_session.json"
        self.history_dir = self.session_dir / "history"
        self.history_dir.mkdir(parents=True, exist_ok=True)

        # Current session state
        self.session_id: Optional[str] = None
        self.started_at: Optional[str] = None
        self.messages: List[Dict[str, str]] = []
        self.topics_explored: List[str] = []
        self.topics_remaining: List[str] = []
        self.insights_gathered: List[Dict[str, Any]] = []
        self.metadata: Dict[str, Any] = {}

    def start_new_session(self) -> str:
        """Start a new session."""
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.started_at = datetime.now().isoformat()
        self.messages = []
        self.topics_explored = []
        self.insights_gathered = []
        self.metadata = {
            "session_number": self._get_session_count() + 1,
        }
        self._save()
        return self.session_id

    def load_previous_session(self) -> bool:
        """Load the previous session if it exists."""
        if not self.current_session_file.exists():
            return False

        try:
            with open(self.current_session_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            self.session_id = data.get('session_id')
            self.started_at = data.get('started_at')
            self.messages = data.get('messages', [])
            self.topics_explored = data.get('topics_explored', [])
            self.topics_remaining = data.get('topics_remaining', [])
            self.insights_gathered = data.get('insights_gathered', [])
            self.metadata = data.get('metadata', {})

            return True
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Error loading session: {e}")
            return False

    def add_message(self, role: str, content: str):
        """Add a message to the conversation history."""
        self.messages.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
        self._save()

    def add_topic_explored(self, topic: str):
        """Mark a topic as explored."""
        if topic not in self.topics_explored:
            self.topics_explored.append(topic)
            if topic in self.topics_remaining:
                self.topics_remaining.remove(topic)
            self._save()

    def set_topics_remaining(self, topics: List[str]):
        """Set the list of topics to explore."""
        self.topics_remaining = [t for t in topics if t not in self.topics_explored]
        self._save()

    def add_insight(self, insight: Dict[str, Any]):
        """Add a gathered insight."""
        insight['gathered_at'] = datetime.now().isoformat()
        self.insights_gathered.append(insight)
        self._save()

    def get_conversation_context(self, max_messages: int = 20) -> List[Dict[str, str]]:
        """Get recent messages for context."""
        # Return the most recent messages
        recent = self.messages[-max_messages:] if len(self.messages) > max_messages else self.messages
        # Convert to Claude format
        return [{"role": m["role"], "content": m["content"]} for m in recent]

    def get_summary(self) -> str:
        """Generate a summary of the current session."""
        duration = ""
        if self.started_at:
            start = datetime.fromisoformat(self.started_at)
            elapsed = datetime.now() - start
            minutes = int(elapsed.total_seconds() / 60)
            duration = f"{minutes} minutes"

        summary = f"""Session Summary
===============
Session ID: {self.session_id}
Duration: {duration}
Messages exchanged: {len(self.messages)}
Topics explored: {len(self.topics_explored)}
Topics remaining: {len(self.topics_remaining)}
Insights gathered: {len(self.insights_gathered)}

Topics Covered:
{chr(10).join(f"  - {t}" for t in self.topics_explored) if self.topics_explored else "  (none yet)"}

Topics Remaining:
{chr(10).join(f"  - {t}" for t in self.topics_remaining[:5]) if self.topics_remaining else "  (none)"}
"""
        return summary

    def end_session(self, archive: bool = True):
        """End the current session and optionally archive it."""
        if archive and self.session_id:
            # Save to history
            archive_file = self.history_dir / f"session_{self.session_id}.json"
            self._save_to_file(archive_file)

        # Clear current session
        if self.current_session_file.exists():
            self.current_session_file.unlink()

        self.session_id = None
        self.messages = []
        self.topics_explored = []
        self.topics_remaining = []
        self.insights_gathered = []

    def _save(self):
        """Save current session to disk."""
        self._save_to_file(self.current_session_file)

    def _save_to_file(self, filepath: Path):
        """Save session data to a specific file."""
        import time

        data = {
            "session_id": self.session_id,
            "started_at": self.started_at,
            "last_updated": datetime.now().isoformat(),
            "messages": self.messages,
            "topics_explored": self.topics_explored,
            "topics_remaining": self.topics_remaining,
            "insights_gathered": self.insights_gathered,
            "metadata": self.metadata,
        }

        # Try atomic write first, with retries for OneDrive sync issues
        temp_file = filepath.with_suffix('.tmp')
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        # Retry the replace operation a few times (OneDrive can lock files during sync)
        for attempt in range(5):
            try:
                temp_file.replace(filepath)
                return
            except PermissionError:
                if attempt < 4:
                    time.sleep(0.2)  # Wait a bit and retry
                else:
                    # Fallback: just write directly to the file
                    try:
                        with open(filepath, 'w', encoding='utf-8') as f:
                            json.dump(data, f, indent=2, ensure_ascii=False)
                        if temp_file.exists():
                            temp_file.unlink()
                    except Exception as e:
                        print(f"Warning: Could not save session: {e}")

    def _get_session_count(self) -> int:
        """Get the total number of archived sessions."""
        return len(list(self.history_dir.glob("session_*.json")))

    def get_all_past_insights(self) -> List[Dict[str, Any]]:
        """Get insights from all past sessions."""
        all_insights = []

        for session_file in sorted(self.history_dir.glob("session_*.json")):
            try:
                with open(session_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    insights = data.get('insights_gathered', [])
                    for insight in insights:
                        insight['session_id'] = data.get('session_id')
                    all_insights.extend(insights)
            except (json.JSONDecodeError, KeyError):
                continue

        return all_insights

    def load_state(self) -> Optional[Dict[str, Any]]:
        """Load the previous session state as a dictionary.

        Returns None if no previous session exists.
        Used by GUI for session continuity.
        """
        state_file = self.session_dir / "gui_state.json"
        if not state_file.exists():
            return None

        try:
            with open(state_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading GUI state: {e}")
            return None

    def save_state(self, state: Dict[str, Any]) -> bool:
        """Save session state as a dictionary.

        Used by GUI to persist conversation context between sessions.
        """
        state_file = self.session_dir / "gui_state.json"
        state['saved_at'] = datetime.now().isoformat()

        try:
            temp_file = state_file.with_suffix('.tmp')
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2, ensure_ascii=False)

            # Try atomic replace with retry for OneDrive
            import time
            for attempt in range(5):
                try:
                    temp_file.replace(state_file)
                    return True
                except PermissionError:
                    if attempt < 4:
                        time.sleep(0.2)
                    else:
                        # Fallback: direct write
                        with open(state_file, 'w', encoding='utf-8') as f:
                            json.dump(state, f, indent=2, ensure_ascii=False)
                        if temp_file.exists():
                            temp_file.unlink()
                        return True
        except Exception as e:
            print(f"Error saving GUI state: {e}")
            return False

        return True


def test_session():
    """Test session management."""
    print("Testing Session Management...")

    session = Session()

    # Start new session
    session_id = session.start_new_session()
    print(f"Started session: {session_id}")

    # Add some messages
    session.add_message("assistant", "Hello Bill, ready to continue our conversation?")
    session.add_message("user", "Yes, let's talk about my childhood.")
    session.add_message("assistant", "Tell me about your earliest memories.")

    # Add topics
    session.set_topics_remaining(["childhood", "career", "relationships", "philosophy"])
    session.add_topic_explored("childhood")

    # Add insight
    session.add_insight({
        "category": "self_knowledge",
        "insight": "Bill's earliest memories involve music",
        "evidence": "Mentioned learning piano at age 5"
    })

    # Get summary
    print("\n" + session.get_summary())

    # Test loading
    session2 = Session()
    if session2.load_previous_session():
        print(f"\nLoaded session: {session2.session_id}")
        print(f"Messages: {len(session2.messages)}")
    else:
        print("No previous session to load")

    print("\nSession test complete!")


if __name__ == "__main__":
    test_session()
