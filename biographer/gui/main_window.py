# Main Window for Cognitive Substrate GUI
"""
Full-screen GUI for the Voice Biographer system.
Optimized for TV display.
"""

import customtkinter as ctk
from typing import Callable, Optional, List, Dict, Any
from datetime import datetime, timedelta
import threading

from .styles import TV_SETTINGS, COLORS, FONTS, apply_tv_theme, get_memory_color


class ErrorBanner(ctk.CTkFrame):
    """A HUGE, FLASHING RED error banner that's IMPOSSIBLE to miss."""

    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color='#FF0000', corner_radius=0, **kwargs)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.is_flashing = False
        self.flash_state = True

        # Giant warning text
        self.error_label = ctk.CTkLabel(
            self,
            text="",
            font=("Arial", 48, "bold"),  # HUGE font
            text_color='white',
            anchor='center',
            justify='center'
        )
        self.error_label.grid(row=0, column=0, pady=40, padx=40, sticky='nsew')

        # Big dismiss button
        self.dismiss_btn = ctk.CTkButton(
            self,
            text="DISMISS ERROR",
            font=("Arial", 28, "bold"),
            fg_color='#660000',
            hover_color='#440000',
            text_color='white',
            height=70,
            width=300,
            command=self._dismiss
        )
        self.dismiss_btn.grid(row=1, column=0, pady=(0, 30))

        # Initially hidden
        self.place_forget()

    def show_error(self, message: str):
        """Show the error banner with the given message - COVERS ENTIRE SCREEN."""
        self.error_label.configure(
            text=f"⚠️  CRITICAL ERROR  ⚠️\n\n{message}\n\n⚠️  SESSION INTERRUPTED  ⚠️"
        )
        # Place over ENTIRE window
        self.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.lift()  # Bring to absolute front
        self.is_flashing = True
        self._flash()

    def _flash(self):
        """Flash between bright red and dark red to grab attention."""
        if not self.is_flashing:
            return

        if self.flash_state:
            self.configure(fg_color='#FF0000')  # Bright red
            self.error_label.configure(text_color='white')
        else:
            self.configure(fg_color='#CC0000')  # Dark red
            self.error_label.configure(text_color='#FFFF00')  # Yellow text

        self.flash_state = not self.flash_state
        self.after(400, self._flash)  # Flash every 400ms

    def _dismiss(self):
        """Hide the error banner."""
        self.is_flashing = False
        self.place_forget()


class MemoryCard(ctk.CTkFrame):
    """A card displaying a single retrieved memory."""

    def __init__(self, master, memory_text: str, score: float, table: str, **kwargs):
        super().__init__(master, fg_color=COLORS['bg_card'], corner_radius=8, **kwargs)

        self.grid_columnconfigure(0, weight=1)

        # Score badge
        score_color = COLORS['accent_primary'] if score > 0.8 else COLORS['text_secondary']
        score_label = ctk.CTkLabel(
            self,
            text=f"{score:.2f}",
            font=FONTS['small'],
            text_color=score_color,
            anchor='w'
        )
        score_label.grid(row=0, column=0, sticky='w', padx=10, pady=(8, 2))

        # Memory text (truncated)
        display_text = memory_text[:150] + '...' if len(memory_text) > 150 else memory_text
        text_label = ctk.CTkLabel(
            self,
            text=display_text,
            font=FONTS['small'],
            text_color=COLORS['text_primary'],
            anchor='w',
            justify='left',
            wraplength=300
        )
        text_label.grid(row=1, column=0, sticky='w', padx=10, pady=(2, 8))

        # Table indicator
        table_color = get_memory_color(table)
        table_label = ctk.CTkLabel(
            self,
            text=table.replace('_', ' ').title(),
            font=FONTS['status'],
            text_color=table_color,
            anchor='e'
        )
        table_label.grid(row=0, column=0, sticky='e', padx=10, pady=(8, 2))


class ConversationBubble(ctk.CTkFrame):
    """A chat bubble for conversation display."""

    def __init__(self, master, text: str, is_biographer: bool, **kwargs):
        bg_color = COLORS['bg_panel'] if is_biographer else COLORS['bg_card']
        super().__init__(master, fg_color=bg_color, corner_radius=12, **kwargs)

        self.grid_columnconfigure(0, weight=1)

        # Speaker label
        speaker = "BIOGRAPHER" if is_biographer else "BILL"
        speaker_color = COLORS['accent_primary'] if is_biographer else COLORS['accent_secondary']

        speaker_label = ctk.CTkLabel(
            self,
            text=speaker,
            font=FONTS['small'],
            text_color=speaker_color,
            anchor='w'
        )
        speaker_label.grid(row=0, column=0, sticky='w', padx=15, pady=(10, 2))

        # Message text
        text_label = ctk.CTkLabel(
            self,
            text=text,
            font=FONTS['body'],
            text_color=COLORS['text_primary'],
            anchor='w',
            justify='left',
            wraplength=600
        )
        text_label.grid(row=1, column=0, sticky='w', padx=15, pady=(2, 12))


class MainWindow(ctk.CTk):
    """Main application window for the Cognitive Substrate GUI."""

    def __init__(self):
        super().__init__()

        apply_tv_theme()

        # Window setup
        self.title("Cognitive Substrate - Voice Biographer")
        self.configure(fg_color=COLORS['bg_primary'])

        # Start maximized (for TV display)
        self.state('zoomed')

        # Track state
        self.session_start_time = None
        self.entry_count = 0
        self.is_recording = False
        self.is_paused = False
        self.pause_start_time = None
        self.paused_duration = timedelta(0)  # Total time spent paused
        self.current_topic = "Initializing..."

        # Callbacks (set by main.py)
        self.on_start_session: Optional[Callable] = None
        self.on_end_session: Optional[Callable] = None
        self.on_pause_session: Optional[Callable] = None
        self.on_resume_session: Optional[Callable] = None
        self.on_done_speaking: Optional[Callable] = None  # User finished their response

        # Build the UI
        self._create_layout()
        self._create_menu_bar()
        self._create_main_panels()
        self._create_status_bar()

        # Create error banner (covers entire screen when shown)
        self.error_banner = ErrorBanner(self)

        # Bind escape to exit fullscreen
        self.bind('<Escape>', lambda e: self.state('normal'))
        self.bind('<F11>', lambda e: self.state('zoomed'))

    def _create_layout(self):
        """Create the main layout grid."""
        self.grid_columnconfigure(0, weight=6)  # Conversation area
        self.grid_columnconfigure(1, weight=4)  # Sidebar
        self.grid_rowconfigure(0, weight=0)     # Menu
        self.grid_rowconfigure(1, weight=3)     # Main content
        self.grid_rowconfigure(2, weight=1)     # Bottom panels
        self.grid_rowconfigure(3, weight=0)     # Status bar

    def _create_menu_bar(self):
        """Create the top menu bar."""
        self.menu_frame = ctk.CTkFrame(self, fg_color=COLORS['bg_secondary'], height=50)
        self.menu_frame.grid(row=0, column=0, columnspan=2, sticky='ew', padx=10, pady=(10, 5))
        self.menu_frame.grid_columnconfigure(1, weight=1)

        # Title
        title = ctk.CTkLabel(
            self.menu_frame,
            text="COGNITIVE SUBSTRATE",
            font=FONTS['title'],
            text_color=COLORS['accent_primary']
        )
        title.grid(row=0, column=0, padx=20, pady=10)

        # Uniform button styling - all buttons same size, high contrast
        BTN_WIDTH = 100
        BTN_HEIGHT = 38
        BTN_FONT = FONTS['small']  # 28px - readable from couch

        # Session controls
        self.start_btn = ctk.CTkButton(
            self.menu_frame,
            text="Start",
            font=BTN_FONT,
            fg_color='#22c55e',  # Bright green
            hover_color='#16a34a',
            text_color='#000000',  # Black text on green
            command=self._handle_start,
            width=BTN_WIDTH,
            height=BTN_HEIGHT
        )
        self.start_btn.grid(row=0, column=2, padx=5, pady=10)

        # Pause/Resume button
        self.pause_btn = ctk.CTkButton(
            self.menu_frame,
            text="Pause",
            font=BTN_FONT,
            fg_color='#eab308',  # Bright yellow
            hover_color='#ca8a04',
            text_color='#000000',  # Black text on yellow
            command=self._handle_pause,
            width=BTN_WIDTH,
            height=BTN_HEIGHT,
            state='disabled'
        )
        self.pause_btn.grid(row=0, column=3, padx=5, pady=10)

        self.end_btn = ctk.CTkButton(
            self.menu_frame,
            text="End",
            font=BTN_FONT,
            fg_color='#ef4444',  # Bright red
            hover_color='#dc2626',
            text_color='#000000',  # Black text on red
            command=self._handle_end,
            width=BTN_WIDTH,
            height=BTN_HEIGHT,
            state='disabled'
        )
        self.end_btn.grid(row=0, column=4, padx=5, pady=10)

        # "I'm Done" button - slightly wider since it's primary action
        self.done_btn = ctk.CTkButton(
            self.menu_frame,
            text="I'M DONE",
            font=BTN_FONT,
            fg_color='#06b6d4',  # Bright cyan
            hover_color='#0891b2',
            text_color='#000000',  # Black text on cyan
            command=self._handle_done_speaking,
            width=130,
            height=BTN_HEIGHT,
            state='disabled'
        )
        self.done_btn.grid(row=0, column=5, padx=(15, 10), pady=10)

        # Visualization buttons - wider to fit full names
        viz_frame = ctk.CTkFrame(self.menu_frame, fg_color='transparent')
        viz_frame.grid(row=0, column=6, padx=(10, 10), pady=10)

        VIZ_BTN_WIDTH = 130  # Wider buttons for full names

        self.viz_constellation_btn = ctk.CTkButton(
            viz_frame,
            text="Constellation",
            font=BTN_FONT,
            fg_color='#7c3aed',  # Purple
            hover_color='#6d28d9',
            text_color='#ffffff',  # White text on purple
            width=VIZ_BTN_WIDTH,
            height=BTN_HEIGHT,
            command=lambda: self._handle_visualization('constellation')
        )
        self.viz_constellation_btn.grid(row=0, column=0, padx=3)

        self.viz_coverage_btn = ctk.CTkButton(
            viz_frame,
            text="Coverage",
            font=BTN_FONT,
            fg_color='#7c3aed',
            hover_color='#6d28d9',
            text_color='#ffffff',
            width=VIZ_BTN_WIDTH,
            height=BTN_HEIGHT,
            command=lambda: self._handle_visualization('coverage')
        )
        self.viz_coverage_btn.grid(row=0, column=1, padx=3)

        self.viz_clusters_btn = ctk.CTkButton(
            viz_frame,
            text="Clusters",
            font=BTN_FONT,
            fg_color='#7c3aed',
            hover_color='#6d28d9',
            text_color='#ffffff',
            width=VIZ_BTN_WIDTH,
            height=BTN_HEIGHT,
            command=lambda: self._handle_visualization('clusters')
        )
        self.viz_clusters_btn.grid(row=0, column=2, padx=3)

        self.viz_gaps_btn = ctk.CTkButton(
            viz_frame,
            text="Gaps",
            font=BTN_FONT,
            fg_color='#dc2626',  # Red - attention needed
            hover_color='#b91c1c',
            text_color='#ffffff',  # White text on red
            width=VIZ_BTN_WIDTH,
            height=BTN_HEIGHT,
            command=lambda: self._handle_visualization('gaps')
        )
        self.viz_gaps_btn.grid(row=0, column=3, padx=3)

        # Callbacks for visualizations (set by main_gui.py)
        self.on_visualization: Optional[Callable[[str], None]] = None

    def _handle_visualization(self, viz_type: str):
        """Handle visualization button clicks."""
        if self.on_visualization:
            self.on_visualization(viz_type)

    def _create_main_panels(self):
        """Create the main content panels."""
        # Left side: Conversation area
        self.conversation_frame = ctk.CTkFrame(self, fg_color=COLORS['bg_secondary'])
        self.conversation_frame.grid(row=1, column=0, sticky='nsew', padx=(10, 5), pady=5)
        self.conversation_frame.grid_rowconfigure(1, weight=1)
        self.conversation_frame.grid_columnconfigure(0, weight=1)

        conv_header = ctk.CTkLabel(
            self.conversation_frame,
            text="CONVERSATION",
            font=FONTS['heading'],
            text_color=COLORS['text_secondary']
        )
        conv_header.grid(row=0, column=0, sticky='w', padx=15, pady=10)

        # Scrollable conversation area
        self.conversation_scroll = ctk.CTkScrollableFrame(
            self.conversation_frame,
            fg_color='transparent'
        )
        self.conversation_scroll.grid(row=1, column=0, sticky='nsew', padx=5, pady=5)
        self.conversation_scroll.grid_columnconfigure(0, weight=1)
        self.conversation_items = []

        # Right side: Memory sidebar
        self.sidebar_frame = ctk.CTkFrame(self, fg_color=COLORS['bg_secondary'])
        self.sidebar_frame.grid(row=1, column=1, sticky='nsew', padx=(5, 10), pady=5)
        self.sidebar_frame.grid_rowconfigure(2, weight=1)
        self.sidebar_frame.grid_columnconfigure(0, weight=1)

        # Current topic
        topic_header = ctk.CTkLabel(
            self.sidebar_frame,
            text="CURRENT TOPIC",
            font=FONTS['small'],
            text_color=COLORS['text_secondary']
        )
        topic_header.grid(row=0, column=0, sticky='w', padx=15, pady=(10, 2))

        self.topic_label = ctk.CTkLabel(
            self.sidebar_frame,
            text="Waiting to start...",
            font=FONTS['body_bold'],
            text_color=COLORS['accent_primary']
        )
        self.topic_label.grid(row=1, column=0, sticky='w', padx=15, pady=(2, 10))

        # Retrieved memories
        mem_header = ctk.CTkLabel(
            self.sidebar_frame,
            text="RETRIEVED MEMORIES",
            font=FONTS['heading'],
            text_color=COLORS['text_secondary']
        )
        mem_header.grid(row=1, column=0, sticky='w', padx=15, pady=(20, 5))

        self.memories_scroll = ctk.CTkScrollableFrame(
            self.sidebar_frame,
            fg_color='transparent'
        )
        self.memories_scroll.grid(row=2, column=0, sticky='nsew', padx=5, pady=5)
        self.memories_scroll.grid_columnconfigure(0, weight=1)
        self.memory_cards = []

        # Bottom left: Session insights
        self.insights_frame = ctk.CTkFrame(self, fg_color=COLORS['bg_secondary'])
        self.insights_frame.grid(row=2, column=0, sticky='nsew', padx=(10, 5), pady=5)
        self.insights_frame.grid_rowconfigure(1, weight=1)
        self.insights_frame.grid_columnconfigure(0, weight=1)

        insights_header = ctk.CTkLabel(
            self.insights_frame,
            text="SESSION INSIGHTS",
            font=FONTS['heading'],
            text_color=COLORS['text_secondary']
        )
        insights_header.grid(row=0, column=0, sticky='w', padx=15, pady=10)

        self.insights_text = ctk.CTkTextbox(
            self.insights_frame,
            font=FONTS['small'],
            fg_color=COLORS['bg_panel'],
            text_color=COLORS['text_primary'],
            wrap='word'
        )
        self.insights_text.grid(row=1, column=0, sticky='nsew', padx=10, pady=(0, 10))
        self.insights_text.insert('1.0', "Insights will appear here as the session progresses...")
        self.insights_text.configure(state='disabled')

        # Bottom right: Next exploration
        self.exploration_frame = ctk.CTkFrame(self, fg_color=COLORS['bg_secondary'])
        self.exploration_frame.grid(row=2, column=1, sticky='nsew', padx=(5, 10), pady=5)
        self.exploration_frame.grid_rowconfigure(1, weight=1)
        self.exploration_frame.grid_columnconfigure(0, weight=1)

        explore_header = ctk.CTkLabel(
            self.exploration_frame,
            text="NEXT EXPLORATION",
            font=FONTS['heading'],
            text_color=COLORS['text_secondary']
        )
        explore_header.grid(row=0, column=0, sticky='w', padx=15, pady=10)

        self.exploration_text = ctk.CTkTextbox(
            self.exploration_frame,
            font=FONTS['small'],
            fg_color=COLORS['bg_panel'],
            text_color=COLORS['text_primary'],
            wrap='word'
        )
        self.exploration_text.grid(row=1, column=0, sticky='nsew', padx=10, pady=(0, 10))
        self.exploration_text.insert('1.0', "Topics to explore next will appear here...")
        self.exploration_text.configure(state='disabled')

    def _create_status_bar(self):
        """Create the bottom status bar."""
        self.status_frame = ctk.CTkFrame(
            self,
            fg_color=COLORS['bg_secondary'],
            height=TV_SETTINGS['status_bar_height']
        )
        self.status_frame.grid(row=3, column=0, columnspan=2, sticky='ew', padx=10, pady=(5, 10))
        self.status_frame.grid_columnconfigure(1, weight=1)

        # Recording indicator
        self.recording_indicator = ctk.CTkLabel(
            self.status_frame,
            text="STANDBY",
            font=FONTS['body_bold'],
            text_color=COLORS['text_muted']
        )
        self.recording_indicator.grid(row=0, column=0, padx=20, pady=10)

        # Session timer
        self.timer_label = ctk.CTkLabel(
            self.status_frame,
            text="Session: --:--:--",
            font=FONTS['body'],
            text_color=COLORS['text_secondary']
        )
        self.timer_label.grid(row=0, column=1, padx=20, pady=10)

        # Entry count
        self.entry_label = ctk.CTkLabel(
            self.status_frame,
            text="Entries: 0",
            font=FONTS['body'],
            text_color=COLORS['text_secondary']
        )
        self.entry_label.grid(row=0, column=2, padx=20, pady=10)

        # Sync status
        self.sync_label = ctk.CTkLabel(
            self.status_frame,
            text="Vector Sync: --",
            font=FONTS['body'],
            text_color=COLORS['text_secondary']
        )
        self.sync_label.grid(row=0, column=3, padx=20, pady=10)

    # --- Public methods for updating the GUI ---

    def add_message(self, text: str, is_biographer: bool):
        """Add a message to the conversation display."""
        bubble = ConversationBubble(self.conversation_scroll, text, is_biographer)
        bubble.grid(row=len(self.conversation_items), column=0, sticky='ew', pady=5, padx=10)
        self.conversation_items.append(bubble)

        # Scroll to bottom
        self.conversation_scroll._parent_canvas.yview_moveto(1.0)

    def update_transcription(self, text: str):
        """Update with real-time transcription (replaces last user message)."""
        # For now, just add as a new message. Could be enhanced to update in-place.
        self.add_message(text, is_biographer=False)

    def set_memories(self, memories: List[Dict[str, Any]]):
        """Display retrieved memories in the sidebar."""
        # Clear existing
        for card in self.memory_cards:
            card.destroy()
        self.memory_cards = []

        # Add new
        for i, mem in enumerate(memories[:10]):  # Show top 10
            card = MemoryCard(
                self.memories_scroll,
                memory_text=mem.get('text', ''),
                score=mem.get('score', 0.0),
                table=mem.get('table', 'unknown')
            )
            card.grid(row=i, column=0, sticky='ew', pady=3, padx=5)
            self.memory_cards.append(card)

    def set_topic(self, topic: str):
        """Update the current topic display."""
        self.current_topic = topic
        self.topic_label.configure(text=topic)

    def update_insights(self, text: str):
        """Update the session insights panel. Shows HUGE error banner if it's an error."""
        # Check if this is an error - show big flashing banner!
        if text.upper().startswith('ERROR:') or 'ERROR:' in text.upper():
            self.show_error(text)
            return

        self.insights_text.configure(state='normal')
        self.insights_text.delete('1.0', 'end')
        self.insights_text.insert('1.0', text)
        self.insights_text.configure(state='disabled')

    def show_error(self, message: str):
        """Show a HUGE flashing red error banner that covers the entire screen."""
        # Clean up the message if it has ERROR: prefix
        clean_message = message.replace('ERROR:', '').strip()
        self.error_banner.show_error(clean_message)

    def update_exploration(self, text: str):
        """Update the next exploration panel."""
        self.exploration_text.configure(state='normal')
        self.exploration_text.delete('1.0', 'end')
        self.exploration_text.insert('1.0', text)
        self.exploration_text.configure(state='disabled')

    def set_recording(self, is_recording: bool):
        """Update recording status indicator."""
        self.is_recording = is_recording
        if self.is_paused:
            return  # Don't change indicator while paused
        if is_recording:
            self.recording_indicator.configure(
                text="RECORDING - CLICK 'I'M DONE' WHEN FINISHED",
                text_color=COLORS['recording_active']
            )
            # Enable the done button when recording
            self.done_btn.configure(state='normal', text="I'M DONE")
        else:
            self.recording_indicator.configure(
                text="LISTENING",
                text_color=COLORS['accent_success']
            )

    def set_status(self, status: str):
        """Set status indicator to a specific message."""
        # Map common statuses to colors
        color_map = {
            'THINKING...': COLORS['accent_primary'],
            'SPEAKING...': COLORS['accent_primary'],
            'PROCESSING...': COLORS['accent_primary'],
            'EXTRACTING INSIGHTS...': '#8b5cf6',  # Purple
            'SAVING...': '#8b5cf6',
            'ENDING SESSION...': '#f59e0b',  # Amber
            'SESSION COMPLETE': COLORS['accent_success'],
            'READY': COLORS['text_muted'],
        }
        color = color_map.get(status.upper(), COLORS['text_secondary'])
        self.recording_indicator.configure(text=status.upper(), text_color=color)

    def set_waiting_for_response(self):
        """Set state to waiting for user to speak."""
        self.recording_indicator.configure(
            text="YOUR TURN - SPEAK, THEN CLICK 'I'M DONE'",
            text_color=COLORS['accent_success']
        )
        self.done_btn.configure(state='normal', text="I'M DONE")

    def set_paused(self, paused: bool):
        """Set the paused state (called from app logic)."""
        self.is_paused = paused
        if paused:
            self.pause_btn.configure(text="Resume", fg_color='#22c55e', hover_color='#16a34a', text_color='#000000')
            self.recording_indicator.configure(text="PAUSED", text_color='#eab308')
        else:
            self.pause_btn.configure(text="Pause", fg_color='#eab308', hover_color='#ca8a04', text_color='#000000')

    def set_entry_count(self, count: int):
        """Update the entry count display."""
        old_count = self.entry_count
        self.entry_count = count
        if count > old_count:
            self.entry_label.configure(text=f"Entries: {old_count} \u2192 {count}")
        else:
            self.entry_label.configure(text=f"Entries: {count}")

    def set_sync_status(self, status: str):
        """Update vector sync status."""
        color = COLORS['accent_success'] if status == 'OK' else COLORS['text_secondary']
        self.sync_label.configure(text=f"Vector Sync: {status}", text_color=color)

    def start_session_timer(self):
        """Start the session timer."""
        self.session_start_time = datetime.now()
        self._update_timer()

    def _update_timer(self):
        """Update the session timer display."""
        if self.session_start_time:
            # Don't update time display while paused (but keep scheduling)
            if not self.is_paused:
                elapsed = datetime.now() - self.session_start_time - self.paused_duration
                hours, remainder = divmod(int(elapsed.total_seconds()), 3600)
                minutes, seconds = divmod(remainder, 60)
                self.timer_label.configure(text=f"Session: {hours:02d}:{minutes:02d}:{seconds:02d}")
            self.after(1000, self._update_timer)

    def _handle_start(self):
        """Handle start session button."""
        self.start_btn.configure(state='disabled')
        self.pause_btn.configure(state='normal')
        self.end_btn.configure(state='normal')
        self.done_btn.configure(state='disabled')  # Enable after biographer speaks
        self.is_paused = False
        self.pause_start_time = None
        self.paused_duration = timedelta(0)  # Reset paused time
        self.start_session_timer()
        self.recording_indicator.configure(text="STARTING SESSION...", text_color=COLORS['accent_primary'])

        if self.on_start_session:
            # Run in thread to not block GUI
            threading.Thread(target=self.on_start_session, daemon=True).start()

    def _handle_pause(self):
        """Handle pause/resume button."""
        if self.is_paused:
            # Resume - add the paused duration to total
            if self.pause_start_time:
                self.paused_duration += datetime.now() - self.pause_start_time
                self.pause_start_time = None
            self.is_paused = False
            self.pause_btn.configure(text="Pause", fg_color='#eab308', hover_color='#ca8a04', text_color='#000000')
            self.recording_indicator.configure(text="RESUMING...", text_color=COLORS['accent_primary'])
            if self.on_resume_session:
                threading.Thread(target=self.on_resume_session, daemon=True).start()
        else:
            # Pause - record when we started pausing
            self.pause_start_time = datetime.now()
            self.is_paused = True
            self.pause_btn.configure(text="Resume", fg_color='#22c55e', hover_color='#16a34a', text_color='#000000')
            self.recording_indicator.configure(text="PAUSED", text_color='#eab308')
            if self.on_pause_session:
                self.on_pause_session()

    def _handle_done_speaking(self):
        """Handle 'I'm Done' button - user finished their response."""
        # Disable the button while processing
        self.done_btn.configure(state='disabled', text="PROCESSING...")
        self.recording_indicator.configure(text="PROCESSING YOUR RESPONSE...", text_color=COLORS['accent_primary'])

        if self.on_done_speaking:
            self.on_done_speaking()

    def _handle_end(self):
        """Handle end session button."""
        # Disable all buttons during shutdown
        self.start_btn.configure(state='disabled')
        self.pause_btn.configure(state='disabled', text="Pause", fg_color='#eab308')
        self.end_btn.configure(state='disabled')
        self.done_btn.configure(state='disabled', text="ENDING...")
        self.is_paused = False

        # Show clear feedback that we're ending
        self.recording_indicator.configure(text="ENDING SESSION - PLEASE WAIT...", text_color='#eab308')

        if self.on_end_session:
            self.on_end_session()

    def set_session_complete(self):
        """Called when session is fully ended and safe to close."""
        self.start_btn.configure(state='normal')
        self.done_btn.configure(text="I'M DONE")
        self.session_start_time = None
        self.recording_indicator.configure(
            text="SESSION COMPLETE - SAFE TO CLOSE",
            text_color=COLORS['accent_success']
        )
        self.timer_label.configure(text="Session ended")

    def show_session_summary(self, summary: Dict[str, Any]):
        """Display end-of-session summary in a popup."""
        summary_window = ctk.CTkToplevel(self)
        summary_window.title("Session Summary")
        summary_window.geometry("800x600")
        summary_window.configure(fg_color=COLORS['bg_primary'])

        # Make it modal
        summary_window.transient(self)
        summary_window.grab_set()

        # Header
        header = ctk.CTkLabel(
            summary_window,
            text="SESSION SUMMARY",
            font=FONTS['title'],
            text_color=COLORS['accent_primary']
        )
        header.pack(pady=20)

        # Summary content
        content = ctk.CTkTextbox(
            summary_window,
            font=FONTS['body'],
            fg_color=COLORS['bg_secondary'],
            text_color=COLORS['text_primary'],
            wrap='word'
        )
        content.pack(fill='both', expand=True, padx=20, pady=10)

        # Build summary text
        text = f"Duration: {summary.get('duration', 'Unknown')}\n"
        text += f"Exchanges: {summary.get('exchanges', 0)}\n\n"

        text += "NEW ENTRIES ADDED:\n"
        for table, count in summary.get('entries_by_table', {}).items():
            text += f"  {table}: {count}\n"

        text += "\nPATTERNS DETECTED:\n"
        for pattern in summary.get('patterns', []):
            text += f"  - {pattern}\n"

        text += "\nSUGGESTED TOPICS FOR NEXT SESSION:\n"
        for topic in summary.get('next_topics', []):
            text += f"  - {topic}\n"

        content.insert('1.0', text)
        content.configure(state='disabled')

        # Close button
        close_btn = ctk.CTkButton(
            summary_window,
            text="Close",
            font=FONTS['body_bold'],
            text_color='black',
            command=summary_window.destroy
        )
        close_btn.pack(pady=20)


def run_gui():
    """Launch the GUI application."""
    app = MainWindow()
    app.mainloop()


if __name__ == '__main__':
    run_gui()
