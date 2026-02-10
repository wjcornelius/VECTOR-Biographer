# Comprehensive Logging System for Cognitive Substrate
"""
Provides structured logging for all biographer operations.
Creates detailed session logs for debugging and review.
"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from functools import wraps


# Paths
SOUL_DIR = Path(__file__).parent.parent
LOGS_DIR = SOUL_DIR / "biographer" / "logs"
SESSIONS_DIR = LOGS_DIR / "sessions"
SYSTEM_DIR = LOGS_DIR / "system"
EXTRACTIONS_DIR = LOGS_DIR / "extractions"

# Ensure directories exist
for dir_path in [SESSIONS_DIR, SYSTEM_DIR, EXTRACTIONS_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)


class SessionLogger:
    """
    Logs all events during a biographer session.
    Creates both human-readable and structured (JSON) logs.
    """

    def __init__(self, session_id: Optional[str] = None):
        """Initialize a session logger."""
        self.session_id = session_id or datetime.now().strftime("%Y%m%d_%H%M%S")
        self.start_time = datetime.now()
        self.events: List[Dict[str, Any]] = []

        # Create log files
        self.log_file = SESSIONS_DIR / f"session_{self.session_id}.log"
        self.json_file = SESSIONS_DIR / f"session_{self.session_id}.json"

        # Setup file handler
        self.file_handler = logging.FileHandler(self.log_file, encoding='utf-8')
        self.file_handler.setFormatter(
            logging.Formatter('[%(asctime)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
        )

        self.logger = logging.getLogger(f'session_{self.session_id}')
        self.logger.setLevel(logging.DEBUG)
        self.logger.addHandler(self.file_handler)

        # Log session start
        self.log_event('SESSION_START', {'session_id': self.session_id})

    def log_event(self, event_type: str, data: Optional[Dict[str, Any]] = None):
        """Log an event with optional data."""
        timestamp = datetime.now()
        event = {
            'timestamp': timestamp.isoformat(),
            'type': event_type,
            'data': data or {}
        }
        self.events.append(event)

        # Write to text log
        if data:
            data_str = json.dumps(data, default=str, ensure_ascii=False)
            if len(data_str) > 500:
                data_str = data_str[:500] + '...'
            self.logger.info(f"{event_type}: {data_str}")
        else:
            self.logger.info(event_type)

    def log_vector_query(self, query: str, results: List[Dict[str, Any]]):
        """Log a vector search query and results."""
        self.log_event('VECTOR_QUERY', {
            'query': query,
            'num_results': len(results),
            'top_scores': [r.get('score', 0) for r in results[:5]]
        })

        # Log individual results
        for i, r in enumerate(results[:5]):
            self.logger.info(f"  Result {i+1}: [{r.get('score', 0):.2f}] {r.get('text', '')[:80]}...")

    def log_biographer_speaks(self, text: str):
        """Log when biographer speaks."""
        self.log_event('BIOGRAPHER_SPEAKS', {'text': text})

    def log_bill_speaks(self, text: str, duration_seconds: float = 0):
        """Log when Bill speaks (transcription)."""
        self.log_event('BILL_SPEAKS', {
            'text': text,
            'word_count': len(text.split()),
            'duration_seconds': duration_seconds
        })

    def log_transcription_saved(self, text: str, exchange_num: int):
        """Log when a raw transcription is saved to the database.

        This is logged IMMEDIATELY after saving, before any other processing,
        to ensure we always have a record even if later steps fail.
        """
        self.log_event('TRANSCRIPTION_SAVED', {
            'exchange': exchange_num,
            'word_count': len(text.split()),
            'char_count': len(text),
            'preview': text[:200] + '...' if len(text) > 200 else text
        })

    def log_extraction(self, entries: List[Dict[str, Any]]):
        """Log extraction results."""
        self.log_event('EXTRACTION_COMPLETE', {
            'num_entries': len(entries),
            'tables': list(set(e.get('category', e.get('table', 'unknown')) for e in entries))
        })

        for entry in entries:
            table = entry.get('category', entry.get('table', '?'))
            self.logger.info(f"  Extracted ({table}): {str(entry.get('content', ''))[:100]}...")

        # Also save to extractions directory
        extraction_file = EXTRACTIONS_DIR / f"extraction_{self.session_id}.json"
        with open(extraction_file, 'w', encoding='utf-8') as f:
            json.dump({
                'session_id': self.session_id,
                'timestamp': datetime.now().isoformat(),
                'entries': entries
            }, f, indent=2, ensure_ascii=False)

    def log_db_write(self, table: str, entry_id: int):
        """Log database write."""
        self.log_event('DB_WRITE', {'table': table, 'entry_id': entry_id})

    def log_vector_sync(self, entry_id: str):
        """Log vector database sync."""
        self.log_event('VECTOR_SYNC', {'entry_id': entry_id})

    def log_error(self, error_type: str, error_msg: str, context: Optional[Dict] = None):
        """Log an error."""
        self.log_event('ERROR', {
            'error_type': error_type,
            'message': error_msg,
            'context': context or {}
        })
        self.logger.error(f"ERROR [{error_type}]: {error_msg}")

    def log_vad_event(self, event: str, duration: float = 0):
        """Log voice activity detection events."""
        self.log_event(f'VAD_{event.upper()}', {'duration_seconds': duration})

    def log_tts_event(self, event: str, duration: float = 0):
        """Log text-to-speech events."""
        self.log_event(f'TTS_{event.upper()}', {'duration_seconds': duration})

    def end_session(self, summary: Optional[Dict[str, Any]] = None):
        """End the session and save all logs."""
        duration = (datetime.now() - self.start_time).total_seconds()

        self.log_event('SESSION_END', {
            'duration_seconds': duration,
            'total_events': len(self.events),
            'summary': summary or {}
        })

        # Save structured JSON log
        session_data = {
            'session_id': self.session_id,
            'start_time': self.start_time.isoformat(),
            'end_time': datetime.now().isoformat(),
            'duration_seconds': duration,
            'events': self.events,
            'summary': summary or {}
        }

        with open(self.json_file, 'w', encoding='utf-8') as f:
            json.dump(session_data, f, indent=2, ensure_ascii=False)

        # Close file handler
        self.file_handler.close()
        self.logger.removeHandler(self.file_handler)

        return self.log_file, self.json_file


class SystemLogger:
    """
    Logs system-wide events (not session-specific).
    """

    def __init__(self):
        today = datetime.now().strftime("%Y%m%d")

        # Main system log
        self.log_file = SYSTEM_DIR / f"biographer_{today}.log"
        self.error_file = SYSTEM_DIR / f"errors_{today}.log"

        # Setup loggers
        self.logger = logging.getLogger('biographer_system')
        self.logger.setLevel(logging.DEBUG)

        if not self.logger.handlers:
            handler = logging.FileHandler(self.log_file, encoding='utf-8')
            handler.setFormatter(
                logging.Formatter('[%(asctime)s] [%(levelname)s] %(message)s')
            )
            self.logger.addHandler(handler)

        self.error_logger = logging.getLogger('biographer_errors')
        self.error_logger.setLevel(logging.ERROR)

        if not self.error_logger.handlers:
            error_handler = logging.FileHandler(self.error_file, encoding='utf-8')
            error_handler.setFormatter(
                logging.Formatter('[%(asctime)s] %(message)s')
            )
            self.error_logger.addHandler(error_handler)

    def info(self, message: str):
        self.logger.info(message)

    def warning(self, message: str):
        self.logger.warning(message)

    def error(self, message: str, exc_info: bool = False):
        self.logger.error(message, exc_info=exc_info)
        self.error_logger.error(message, exc_info=exc_info)

    def debug(self, message: str):
        self.logger.debug(message)


# Global system logger instance
system_log = SystemLogger()


def log_function_call(func):
    """Decorator to log function calls."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        func_name = func.__name__
        system_log.debug(f"Calling {func_name}")
        try:
            result = func(*args, **kwargs)
            system_log.debug(f"{func_name} completed successfully")
            return result
        except Exception as e:
            system_log.error(f"{func_name} raised {type(e).__name__}: {e}")
            raise
    return wrapper


def get_recent_sessions(limit: int = 10) -> List[Dict[str, Any]]:
    """Get list of recent session logs."""
    sessions = []
    for json_file in sorted(SESSIONS_DIR.glob("session_*.json"), reverse=True)[:limit]:
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                sessions.append({
                    'session_id': data.get('session_id'),
                    'start_time': data.get('start_time'),
                    'duration': data.get('duration_seconds'),
                    'events': len(data.get('events', [])),
                    'file': str(json_file)
                })
        except Exception:
            pass
    return sessions


def get_session_log(session_id: str) -> Optional[Dict[str, Any]]:
    """Load a specific session log."""
    json_file = SESSIONS_DIR / f"session_{session_id}.json"
    if json_file.exists():
        with open(json_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None
