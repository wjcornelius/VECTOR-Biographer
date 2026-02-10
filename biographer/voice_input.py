"""Voice input module with simple audio level detection and Whisper transcription."""

import numpy as np
import sounddevice as sd
import whisper
import tempfile
import wave
import os
import time
import queue
from typing import Optional, Callable


class VoiceInput:
    """Handles voice detection and speech-to-text transcription using simple audio levels."""

    def __init__(
        self,
        whisper_model: str = "medium",  # medium model for better accuracy (was: small)
        sample_rate: int = 16000,
        silence_threshold: float = 8.0,  # seconds of silence before processing
        min_speech_duration: float = 0.5,  # minimum speech to be valid
        noise_threshold: float = 0.0002,  # audio level below this is considered silence
        on_transcription: Optional[Callable[[str], None]] = None,
    ):
        self.sample_rate = sample_rate
        self.silence_threshold = silence_threshold
        self.min_speech_duration = min_speech_duration
        self.noise_threshold = noise_threshold
        self.on_transcription = on_transcription

        print(f"Loading Whisper model ({whisper_model})...")
        # Use in_memory=False for large models (medium, large) to avoid memory read errors
        self.whisper_model = whisper.load_model(whisper_model, in_memory=False)

        # Audio collection queue
        self.audio_queue = queue.Queue()
        self.stop_flag = False
        self.is_recording = False  # Track if we're actively recording

        print("Voice input initialized (using simple audio level detection).")

    def _audio_callback(self, indata, frames, time_info, status):
        """Called for each audio chunk - just collect, don't process."""
        if status and 'overflow' not in str(status).lower():
            print(f"Audio status: {status}")
        self.audio_queue.put(indata[:, 0].copy())

    def _get_audio_level(self, audio: np.ndarray) -> float:
        """Get the RMS audio level."""
        return np.sqrt(np.mean(audio ** 2))

    def _collect_until_stopped(self, timeout: float = 300.0) -> Optional[np.ndarray]:
        """Collect audio until stop() is called (manual mode - NO silence detection).

        This is for use with a manual "I'm Done" button - we record everything
        until the user explicitly signals they're finished.
        """
        all_audio = []
        last_status_time = time.time()
        start_time = time.time()

        print(f"  [DEBUG] Starting collection with timeout={timeout}s, stop_flag={self.stop_flag}")

        while not self.stop_flag:
            elapsed = time.time() - start_time

            # Check timeout
            if elapsed > timeout:
                print(f"  [DEBUG] TIMEOUT after {elapsed:.1f}s - this should NOT happen normally!")
                break

            try:
                # Get audio chunk (blocks for up to 0.1s)
                chunk = self.audio_queue.get(timeout=0.1)
                all_audio.append(chunk)

                # Status every 30 seconds to confirm still recording
                if time.time() - last_status_time >= 30.0:
                    print(f"  [{elapsed:.0f}s] Still recording... (stop_flag={self.stop_flag})")
                    last_status_time = time.time()

            except queue.Empty:
                continue

        # Log WHY we exited
        elapsed = time.time() - start_time
        if self.stop_flag:
            print(f"  [DEBUG] Loop exited: stop_flag=True after {elapsed:.1f}s (user clicked button)")
        else:
            print(f"  [DEBUG] Loop exited: timeout after {elapsed:.1f}s")

        if not all_audio:
            print("  [DEBUG] No audio collected!")
            return None

        # Combine all audio
        full_audio = np.concatenate(all_audio)
        duration = len(full_audio) / self.sample_rate

        print(f"  Recording stopped - {duration:.1f}s of audio collected")

        # Check minimum duration
        if duration < self.min_speech_duration:
            print("  Audio too short, discarding")
            return None

        return full_audio

    def _transcribe(self, audio: np.ndarray) -> str:
        """Transcribe audio using Whisper."""
        duration = len(audio) / self.sample_rate
        print(f"\nProcessing {duration:.1f}s of audio...")

        # Save to temp file
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
            temp_path = f.name

        try:
            with wave.open(temp_path, 'wb') as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(self.sample_rate)
                audio_int16 = (audio * 32767).astype(np.int16)
                wav_file.writeframes(audio_int16.tobytes())

            result = self.whisper_model.transcribe(
                temp_path,
                language='en',
                fp16=False
            )
            return result['text'].strip()

        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def listen_once(self, timeout: float = 1800.0) -> Optional[str]:
        """Listen for a single utterance and return the transcription.

        Uses MANUAL mode - recording continues until stop() is called.
        No automatic silence detection - user must click "I'm Done".
        Default timeout is 30 minutes.
        """
        print(f"\n" + "="*60)
        print(f"[DEBUG] listen_once called with timeout={timeout}s ({timeout/60:.0f} minutes)")
        print(f"[DEBUG] RESETTING stop_flag from {self.stop_flag} to False")
        self.stop_flag = False
        print(f"[DEBUG] stop_flag is now: {self.stop_flag}")
        print("="*60)

        # Clear any old audio in queue
        while not self.audio_queue.empty():
            try:
                self.audio_queue.get_nowait()
            except queue.Empty:
                break

        print("="*60)
        print("RECORDING... (waiting for 'I'm Done' button)")
        print("="*60)

        result = None
        try:
            self.is_recording = True
            print(f"[DEBUG] is_recording set to True")
            with sd.InputStream(
                samplerate=self.sample_rate,
                channels=1,
                dtype='float32',
                blocksize=4096,
                callback=self._audio_callback
            ):
                print(f"[DEBUG] Audio stream started successfully")
                audio = self._collect_until_stopped(timeout)
                print(f"[DEBUG] _collect_until_stopped returned")
                if audio is not None:
                    result = self._transcribe(audio)

        except Exception as e:
            print(f"[ERROR] Error during listening: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.is_recording = False
            print(f"[DEBUG] is_recording set to False")

        return result

    def listen_continuous(self, on_speech: Callable[[str], bool]):
        """Continuously listen and call on_speech for each utterance."""
        print("Starting continuous listening (Ctrl+C to stop)...")

        try:
            while True:
                text = self.listen_once(timeout=120)
                if text:
                    should_continue = on_speech(text)
                    if not should_continue:
                        break
        except KeyboardInterrupt:
            print("\nStopped listening.")

    def stop(self):
        """Signal to stop listening."""
        import traceback
        print(f"\n" + "="*60)
        print(f"[DEBUG] stop() called!")
        print(f"[DEBUG] Current state: is_recording={self.is_recording}, stop_flag={self.stop_flag}")
        if not self.is_recording:
            print(f"[DEBUG] WARNING: stop() called but is_recording=False - ignoring")
            print("="*60)
            return
        print(f"[DEBUG] Setting stop_flag=True")
        print(f"[DEBUG] Call stack:")
        traceback.print_stack(limit=5)
        self.stop_flag = True
        print("="*60)

    def listen(self, timeout: float = 1800.0) -> Optional[str]:
        """Alias for listen_once() for compatibility with GUI.

        Default timeout is 30 minutes - user clicks 'I'm Done' to stop.
        """
        print(f"[DEBUG] listen() called with timeout={timeout}s ({timeout/60:.0f} minutes)")
        return self.listen_once(timeout)


def test_voice_input():
    """Test the voice input system."""
    print("Testing Voice Input...")
    print("Speak something, then wait for it to be transcribed.")
    print("Press Ctrl+C to stop.\n")

    vi = VoiceInput(whisper_model="medium")

    def on_speech(text: str) -> bool:
        print(f"\n>>> You said: {text}\n")
        lower = text.lower()
        if "stop" in lower or "quit" in lower or "exit" in lower:
            print("Stop phrase detected. Exiting.")
            return False
        return True

    vi.listen_continuous(on_speech)


if __name__ == "__main__":
    test_voice_input()
