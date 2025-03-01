# Automated Media Transcriber

This is a Python-based automated media transcription system that monitors a folder for new audio/video files, transcribes them using Whisper, and saves the transcripts as text files.

## Features
- **Automated Monitoring**: Detects new media files in the `media_files` directory.
- **Multi-Process Transcription**: Utilizes multiple workers for parallel processing.
- **Persistent Tracking**: Keeps track of processed files to avoid redundant transcriptions.
- **Real-Time Handling**: Responds to file creation, renaming, and deletion events.
- **Supports Multiple Formats**: Works with `.mp3`, `.wav`, `.mp4`, `.mkv`, `.mov`, `.flv`, `.aac`, `.m4a`.

## Installation

1. Clone this repository:
   ```sh
   git clone https://github.com/kshitizsinghal13/Auto-transcriber.git
   cd media-transcriber
   ```

2. Install dependencies:
   ```sh
   pip install -r requirements.txt
   ```

3. Create the monitored folder:
   ```sh
   mkdir media_files
   ```

## Usage

To start the transcription system, run:
```sh
python app.py
```

## How It Works

- The script monitors the `media_files` folder for new files.
- When a supported media file is detected, it gets added to the transcription queue.
- A multi-process setup ensures efficient transcription using `faster-whisper`.
- Transcripts are saved in the same directory as the media file.

## File Handling

- If a transcript file is deleted, the system re-transcribes the media.
- If a media file is moved/renamed, its transcription is updated accordingly.
- Already transcribed files are skipped unless their transcript is missing.

## Configuration

You can modify the script to change:
- `MONITORED_FOLDER`: Folder to watch for new media files.
- `SUPPORTED_FORMATS`: File formats to transcribe.
- `NUM_WORKERS`: Number of concurrent transcription processes.



🚀 **Developed by [Kshitiz Singhal]** 🚀
