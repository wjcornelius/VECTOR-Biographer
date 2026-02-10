"""Voice output module using Edge TTS for natural-sounding neural voices."""

import asyncio
import tempfile
import os
import numpy as np
from typing import Optional
from pathlib import Path
import threading
import queue


def apply_lowpass_filter(audio_data: np.ndarray, sample_rate: int, cutoff_hz: int = 3000) -> np.ndarray:
    """Apply a low-pass filter to reduce harshness in high frequencies."""
    try:
        from scipy.signal import butter, filtfilt

        # Design a butterworth low-pass filter
        nyquist = sample_rate / 2
        normalized_cutoff = cutoff_hz / nyquist

        # Ensure cutoff is valid (must be < 1.0)
        if normalized_cutoff >= 1.0:
            return audio_data

        b, a = butter(4, normalized_cutoff, btype='low')

        # Apply filter (filtfilt for zero phase distortion)
        filtered = filtfilt(b, a, audio_data)
        return filtered.astype(audio_data.dtype)

    except ImportError:
        print("scipy not available for filtering, playing unfiltered")
        return audio_data
    except Exception as e:
        print(f"Filter error: {e}")
        return audio_data


class VoiceOutput:
    """Handles text-to-speech synthesis using Microsoft Edge TTS (neural voices)."""

    def __init__(
        self,
        voice: str = "en-US-AndrewNeural",
        volume: float = 0.25,
    ):
        self.voice = voice
        self.volume = volume
        self.speech_queue = queue.Queue()
        self.is_speaking = False
        self.stop_speaking = False

        # Initialize pygame for audio playback
        try:
            import pygame
            # Pre-init with specific settings to avoid device issues
            pygame.mixer.pre_init(frequency=24000, size=-16, channels=1, buffer=2048)
            pygame.mixer.init()
            self._pygame_available = True
            print("pygame mixer initialized successfully")
        except Exception as e:
            print(f"Warning: pygame mixer init failed: {e}")
            print("Will try pyttsx3 as fallback...")
            self._pygame_available = False

        # Start the speech worker thread
        self._worker_thread = threading.Thread(target=self._speech_worker, daemon=True)
        self._worker_thread.start()

        print(f"Voice output initialized with Edge TTS voice: {voice} at {int(volume*100)}% volume")

    async def _synthesize_edge_tts(self, text: str, temp_path: str) -> bool:
        """Synthesize text to audio using Edge TTS."""
        try:
            import edge_tts

            # Edge TTS volume is in dB, convert from 0-1 scale
            # -100dB is silent, 0dB is full volume
            # For 25% volume, we want significant reduction
            volume_db = int((self.volume - 1.0) * 50)  # 0.25 -> -37.5 dB

            communicate = edge_tts.Communicate(text, self.voice, volume=f"{volume_db:+d}%")
            await communicate.save(temp_path)
            return True

        except Exception as e:
            print(f"Edge TTS synthesis error: {e}")
            return False

    def _synthesize_with_edge_tts(self, text: str) -> Optional[str]:
        """Synthesize text and return path to audio file."""
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as f:
            temp_path = f.name

        try:
            # Run async synthesis
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            success = loop.run_until_complete(self._synthesize_edge_tts(text, temp_path))
            loop.close()

            if success and os.path.exists(temp_path) and os.path.getsize(temp_path) > 0:
                return temp_path
            else:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                return None

        except Exception as e:
            print(f"Synthesis error: {e}")
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            return None

    def _play_audio_file(self, audio_path: str):
        """Play audio file through speakers using pygame, with low-pass filter."""
        if not self._pygame_available:
            print("Cannot play audio: pygame not available")
            return

        try:
            import pygame
            from pydub import AudioSegment
            import io

            # Load MP3 and convert to raw audio for filtering
            audio_segment = AudioSegment.from_mp3(audio_path)
            sample_rate = audio_segment.frame_rate
            samples = np.array(audio_segment.get_array_of_samples())

            # Handle stereo
            if audio_segment.channels == 2:
                samples = samples.reshape((-1, 2))
                # Apply filter to each channel
                filtered_left = apply_lowpass_filter(samples[:, 0].astype(np.float64), sample_rate, 4000)
                filtered_right = apply_lowpass_filter(samples[:, 1].astype(np.float64), sample_rate, 4000)
                filtered = np.column_stack([filtered_left, filtered_right]).astype(np.int16)
            else:
                filtered = apply_lowpass_filter(samples.astype(np.float64), sample_rate, 4000).astype(np.int16)

            # Convert back to AudioSegment
            filtered_audio = AudioSegment(
                filtered.tobytes(),
                frame_rate=sample_rate,
                sample_width=2,  # 16-bit
                channels=audio_segment.channels
            )

            # Export to WAV in memory for pygame
            wav_buffer = io.BytesIO()
            filtered_audio.export(wav_buffer, format='wav')
            wav_buffer.seek(0)

            # Play with pygame
            sound = pygame.mixer.Sound(wav_buffer)
            sound.set_volume(self.volume)
            channel = sound.play()

            # Wait for playback to complete
            while channel.get_busy() and not self.stop_speaking:
                pygame.time.wait(100)

        except ImportError as e:
            # Fallback: play without filtering
            print(f"pydub not available, playing without filter: {e}")
            import pygame
            pygame.mixer.music.load(audio_path)
            pygame.mixer.music.set_volume(self.volume)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy() and not self.stop_speaking:
                pygame.time.wait(100)

        except Exception as e:
            print(f"Audio playback error: {e}")

    def _speech_worker(self):
        """Background worker to process speech queue."""
        while True:
            try:
                text = self.speech_queue.get()
                if text is None:
                    break

                self.is_speaking = True
                self.stop_speaking = False

                # Synthesize with Edge TTS
                audio_path = self._synthesize_with_edge_tts(text)

                if audio_path and not self.stop_speaking:
                    self._play_audio_file(audio_path)

                    # Clean up temp file
                    try:
                        os.unlink(audio_path)
                    except:
                        pass

                self.is_speaking = False
                self.speech_queue.task_done()

            except Exception as e:
                print(f"Speech worker error: {e}")
                self.is_speaking = False

    def speak(self, text: str, blocking: bool = True):
        """
        Speak the given text.

        Args:
            text: Text to speak
            blocking: If True, wait for speech to complete
        """
        if not text.strip():
            return

        self.speech_queue.put(text)

        if blocking:
            self.speech_queue.join()

    def speak_async(self, text: str):
        """Speak text without blocking."""
        self.speak(text, blocking=False)

    def stop(self):
        """Stop current speech."""
        self.stop_speaking = True

        if self._pygame_available:
            try:
                import pygame
                pygame.mixer.music.stop()
            except:
                pass

        # Clear the queue
        while not self.speech_queue.empty():
            try:
                self.speech_queue.get_nowait()
                self.speech_queue.task_done()
            except queue.Empty:
                break

    def wait(self):
        """Wait for all queued speech to complete."""
        self.speech_queue.join()

    def shutdown(self):
        """Shutdown the voice output system."""
        self.stop()
        self.speech_queue.put(None)
        self._worker_thread.join(timeout=2)

        if self._pygame_available:
            try:
                import pygame
                pygame.mixer.quit()
            except:
                pass


class SimpleTTS:
    """Simple TTS using Edge TTS - wrapper for quick usage."""

    def __init__(self, volume: float = 0.25, voice: str = "en-US-AndrewNeural"):
        self.volume = volume
        self.voice = voice

        # Initialize pygame
        try:
            import pygame
            pygame.mixer.init()
            self._pygame_available = True
        except Exception as e:
            print(f"Warning: pygame not available: {e}")
            self._pygame_available = False

        print(f"SimpleTTS initialized with Edge TTS (voice: {voice}, volume: {int(volume*100)}%)")

    def speak(self, text: str):
        """Speak text using Edge TTS with low-pass filter for softer sound."""
        if not text.strip():
            return

        try:
            import edge_tts
            import pygame
            from pydub import AudioSegment
            import io

            # Create temp file for audio
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as f:
                temp_path = f.name

            # Synthesize
            volume_db = int((self.volume - 1.0) * 50)

            async def synthesize():
                communicate = edge_tts.Communicate(text, self.voice, volume=f"{volume_db:+d}%")
                await communicate.save(temp_path)

            asyncio.run(synthesize())

            # Load, filter, and play
            if self._pygame_available and os.path.exists(temp_path):
                # Load MP3 and apply low-pass filter
                audio_segment = AudioSegment.from_mp3(temp_path)
                sample_rate = audio_segment.frame_rate
                samples = np.array(audio_segment.get_array_of_samples())

                # Handle stereo
                if audio_segment.channels == 2:
                    samples = samples.reshape((-1, 2))
                    filtered_left = apply_lowpass_filter(samples[:, 0].astype(np.float64), sample_rate, 4000)
                    filtered_right = apply_lowpass_filter(samples[:, 1].astype(np.float64), sample_rate, 4000)
                    filtered = np.column_stack([filtered_left, filtered_right]).astype(np.int16)
                else:
                    filtered = apply_lowpass_filter(samples.astype(np.float64), sample_rate, 4000).astype(np.int16)

                # Convert back to AudioSegment
                filtered_audio = AudioSegment(
                    filtered.tobytes(),
                    frame_rate=sample_rate,
                    sample_width=2,
                    channels=audio_segment.channels
                )

                # Export to WAV in memory
                wav_buffer = io.BytesIO()
                filtered_audio.export(wav_buffer, format='wav')
                wav_buffer.seek(0)

                # Play
                sound = pygame.mixer.Sound(wav_buffer)
                sound.set_volume(self.volume)
                channel = sound.play()

                while channel.get_busy():
                    pygame.time.wait(100)

            # Cleanup
            if os.path.exists(temp_path):
                os.unlink(temp_path)

        except ImportError as e:
            print(f"Missing dependency for filtered audio: {e}")
            # Fallback without filter
            self._speak_unfiltered(text)
        except Exception as e:
            print(f"TTS error: {e}")

    def _speak_unfiltered(self, text: str):
        """Fallback: speak without low-pass filter."""
        try:
            import edge_tts
            import pygame

            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as f:
                temp_path = f.name

            volume_db = int((self.volume - 1.0) * 50)

            async def synthesize():
                communicate = edge_tts.Communicate(text, self.voice, volume=f"{volume_db:+d}%")
                await communicate.save(temp_path)

            asyncio.run(synthesize())

            if self._pygame_available and os.path.exists(temp_path):
                pygame.mixer.music.load(temp_path)
                pygame.mixer.music.set_volume(self.volume)
                pygame.mixer.music.play()

                while pygame.mixer.music.get_busy():
                    pygame.time.wait(100)

            if os.path.exists(temp_path):
                os.unlink(temp_path)

        except Exception as e:
            print(f"TTS error: {e}")

    def stop(self):
        """Stop speaking."""
        if self._pygame_available:
            try:
                import pygame
                pygame.mixer.music.stop()
            except:
                pass


def test_voice_output():
    """Test the voice output system."""
    print("Testing Voice Output...")

    # Try simple TTS first (works on Windows out of box)
    tts = SimpleTTS()

    test_phrases = [
        "Hello Bill, this is your voice biographer speaking.",
        "I'm ready to learn more about your life story.",
        "Shall we begin our conversation?",
    ]

    for phrase in test_phrases:
        print(f"Speaking: {phrase}")
        tts.speak(phrase)
        import time
        time.sleep(0.5)

    print("Test complete!")


if __name__ == "__main__":
    test_voice_output()
