import os
import time
import threading
import multiprocessing
import json
from queue import Empty
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from faster_whisper import WhisperModel

MONITORED_FOLDER = "media_files"
SUPPORTED_FORMATS = {".mp3", ".wav", ".mp4", ".mkv", ".mov", ".flv", ".aac", ".m4a"}
NUM_WORKERS = min(4, multiprocessing.cpu_count())
PROCESSED_FILES_DB = "processed_files.json"

os.makedirs(MONITORED_FOLDER, exist_ok=True)

task_queue = multiprocessing.Queue()
processed_files = set()

def load_processed_files():
    """Load already transcribed files to avoid redundant processing."""
    global processed_files
    if os.path.exists(PROCESSED_FILES_DB):
        try:
            with open(PROCESSED_FILES_DB, "r") as f:
                processed_files = set(json.load(f))
        except (json.JSONDecodeError, FileNotFoundError):
            processed_files = set()  # Reset if the file is corrupted

def save_processed_files():
    """Save processed file list persistently."""
    with open(PROCESSED_FILES_DB, "w") as f:
        json.dump(list(processed_files), f)

def get_transcription_path(file_path):
    """Store transcript in the same directory as the media file."""
    return os.path.join(os.path.dirname(file_path), f"{os.path.splitext(os.path.basename(file_path))[0]}.txt")

def save_transcription(transcript_path, transcript):
    """Save the transcript to a file."""
    with open(transcript_path, "w", encoding="utf-8") as f:
        f.write(transcript)
    print(f"📄 Transcription saved: {transcript_path}")

def transcriber_worker(worker_id, task_queue):
    """Worker process to handle transcription tasks."""
    print(f"🔄 Worker-{worker_id}: Loading Whisper Model...")
    model = WhisperModel("tiny", compute_type="float32")

    while True:
        try:
            file_path = task_queue.get(timeout=10)
            if file_path is None:
                print(f"✅ Worker-{worker_id} shutting down...")
                break
            transcript_path = get_transcription_path(file_path)

            # Skip already processed files **only if transcription exists**
            if file_path in processed_files and os.path.exists(transcript_path):
                print(f"⏭️ Worker-{worker_id}: Skipping already transcribed file {file_path}")
                continue

            print(f"📝 Worker-{worker_id} processing: {file_path}")
            segments, _ = model.transcribe(file_path, beam_size=1, word_timestamps=False, language="en")
            transcript = " ".join(segment.text for segment in segments)

            save_transcription(transcript_path, transcript)
            processed_files.add(file_path)
            save_processed_files()

        except Empty:
            continue
        except Exception as e:
            print(f"⚠️ Worker-{worker_id} error: {e}")

def process_untranscribed_files():
    """Scan directory and subdirectories for unprocessed media files."""
    print("🔍 Checking for missing transcriptions...")
    load_processed_files()

    for root, _, files in os.walk(MONITORED_FOLDER):
        for file in files:
            file_path = os.path.join(root, file)
            transcript_path = get_transcription_path(file_path)

            # Process only if the transcription file **does not exist**
            if any(file.endswith(ext) for ext in SUPPORTED_FORMATS) and not os.path.exists(transcript_path):
                print(f"⏳ New file detected: {file}")
                task_queue.put(file_path)
                processed_files.add(file_path)

    save_processed_files()

class MediaFileHandler(FileSystemEventHandler):
    """Handles new, moved, and deleted media files in real-time."""
    
    def on_created(self, event):
        """Detect new media files and add them for transcription."""
        if not event.is_directory and any(event.src_path.endswith(ext) for ext in SUPPORTED_FORMATS):
            print(f"📂 New file detected: {event.src_path}")
            time.sleep(3)
            transcript_path = get_transcription_path(event.src_path)
            if os.path.exists(event.src_path) and not os.path.exists(transcript_path):
                task_queue.put(event.src_path)
    
    def on_moved(self, event):
        """Handle renamed or moved files."""
        if not event.is_directory and any(event.dest_path.endswith(ext) for ext in SUPPORTED_FORMATS):
            print(f"🔄 File renamed: {event.src_path} → {event.dest_path}")
            transcript_path = get_transcription_path(event.dest_path)
            if not os.path.exists(transcript_path):
                task_queue.put(event.dest_path)

    def on_deleted(self, event):
        """Handle deleted transcription files and trigger re-transcription if needed."""
        if not event.is_directory and event.src_path.endswith(".txt"):
            filename = os.path.basename(event.src_path).replace(".txt", "")
            media_file_path = None
            for ext in SUPPORTED_FORMATS:
                potential_path = os.path.join(MONITORED_FOLDER, f"{filename}{ext}")
                if os.path.exists(potential_path):
                    media_file_path = potential_path
                    break
            if media_file_path:
                print(f"⚠️ Transcription deleted! Re-transcribing: {media_file_path}")
                task_queue.put(media_file_path)

def start_monitoring():
    """Start watchdog observer to monitor files in real-time."""
    observer = Observer()
    observer.schedule(MediaFileHandler(), path=MONITORED_FOLDER, recursive=True)
    observer.start()
    print(f"👀 Monitoring folder: {MONITORED_FOLDER}")

    try:
        while True:
            time.sleep(5)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

if __name__ == "__main__":
    multiprocessing.freeze_support()
    process_untranscribed_files()

    workers = []
    for i in range(NUM_WORKERS):
        worker = multiprocessing.Process(target=transcriber_worker, args=(i, task_queue))
        worker.start()
        workers.append(worker)

    monitoring_thread = threading.Thread(target=start_monitoring, daemon=True)
    monitoring_thread.start()

    try:
        while True:
            time.sleep(10)
    except KeyboardInterrupt:
        print("🛑 Shutting down...")

    for _ in range(NUM_WORKERS):
        task_queue.put(None)
    
    for worker in workers:
        worker.join()
