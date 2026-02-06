"""
Kokoro Audiobook Agent
----------------------
Converts a book (PDF/EPUB) into a full audiobook using Kokoro TTS.
Supports resuming from where it left off if interrupted.

Kokoro is a fast, local TTS model. This agent:
  1. Extracts text from the book
  2. Splits into chapters/chunks
  3. Converts each chunk to audio with Kokoro
  4. Tracks progress so it can resume on interruption
  5. Concatenates all chunks into the final audiobook
"""

import os
import json
import re
import wave
import struct
from pathlib import Path

import numpy as np
import soundfile as sf

# Text extraction (shared logic with summary agent)
import PyPDF2
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup

PROGRESS_FILENAME = ".audiobook_progress.json"


def _extract_text_pdf(path: Path) -> str:
    text_parts = []
    with open(path, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        for page in reader.pages:
            text_parts.append(page.extract_text() or "")
    return "\n".join(text_parts)


def _extract_text_epub(path: Path) -> str:
    book = epub.read_epub(str(path))
    text_parts = []
    for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
        soup = BeautifulSoup(item.get_content(), "html.parser")
        text_parts.append(soup.get_text(separator="\n"))
    return "\n".join(text_parts)


def _extract_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return _extract_text_pdf(path)
    elif suffix == ".epub":
        return _extract_text_epub(path)
    elif suffix == ".txt":
        return path.read_text()
    else:
        raise ValueError(f"Unsupported format: {suffix}")


def _split_into_chunks(text: str, max_chars: int = 3000) -> list[str]:
    """Split text into TTS-friendly chunks at sentence boundaries."""
    # Clean up text
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r' {2,}', ' ', text)

    sentences = re.split(r'(?<=[.!?])\s+', text)
    chunks = []
    current = []
    current_len = 0

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        if current_len + len(sentence) > max_chars and current:
            chunks.append(" ".join(current))
            current = [sentence]
            current_len = len(sentence)
        else:
            current.append(sentence)
            current_len += len(sentence) + 1

    if current:
        chunks.append(" ".join(current))

    return chunks


def _load_progress(output_dir: Path) -> dict:
    progress_file = output_dir / PROGRESS_FILENAME
    if progress_file.exists():
        return json.loads(progress_file.read_text())
    return {"completed_chunks": [], "total_chunks": 0}


def _save_progress(output_dir: Path, progress: dict):
    progress_file = output_dir / PROGRESS_FILENAME
    progress_file.write_text(json.dumps(progress, indent=2))


def _synthesize_with_kokoro(text: str, output_path: Path, voice: str = "af_heart") -> bool:
    """Synthesize text to audio using Kokoro TTS."""
    try:
        import kokoro
        pipeline = kokoro.KPipeline(lang_code="a")

        all_audio = []
        for _gs, _ps, audio in pipeline(text, voice=voice):
            all_audio.append(audio)

        if all_audio:
            full = np.concatenate(all_audio)
            sf.write(str(output_path), full, 24000)
            return True
        return False
    except ImportError:
        print("[Kokoro] kokoro package not installed. Falling back to OpenAI TTS.")
        return _fallback_tts(text, output_path)
    except Exception as e:
        print(f"[Kokoro] Error: {e}. Falling back to OpenAI TTS.")
        return _fallback_tts(text, output_path)


def _fallback_tts(text: str, output_path: Path) -> bool:
    """Fallback to OpenAI TTS if Kokoro is unavailable."""
    try:
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        # Truncate to API limit
        chunk = text[:4096]
        response = client.audio.speech.create(
            model="tts-1",
            voice="alloy",
            input=chunk,
            response_format="wav",
        )
        output_path.write_bytes(response.content)
        return True
    except Exception as e:
        print(f"[Kokoro] Fallback TTS also failed: {e}")
        return False


def _concatenate_wav_files(wav_files: list[Path], output_path: Path):
    """Concatenate multiple WAV files into one."""
    if not wav_files:
        return

    # Read first file to get params
    data_list = []
    sample_rate = None

    for wf in wav_files:
        data, sr = sf.read(str(wf))
        if sample_rate is None:
            sample_rate = sr
        data_list.append(data)

    combined = np.concatenate(data_list)
    sf.write(str(output_path), combined, sample_rate)


def generate_audiobook(
    book_title: str,
    book_path: Path,
    output_dir: Path,
    voice: str = "af_heart",
) -> dict:
    """
    Full pipeline: extract text -> chunk -> TTS each chunk (resumable) -> concatenate.

    Returns dict with:
      - audiobook_path: Path to final audiobook WAV
      - total_chunks, completed_chunks
      - resumed: whether this was a resumed run
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    chunks_dir = output_dir / "chunks"
    chunks_dir.mkdir(exist_ok=True)

    # Load progress
    progress = _load_progress(output_dir)
    resumed = len(progress["completed_chunks"]) > 0

    if resumed:
        print(f"[Kokoro] Resuming from chunk {len(progress['completed_chunks'])}/{progress['total_chunks']}")

    # Extract and chunk text
    print(f"[Kokoro] Extracting text from {book_path.name}...")
    full_text = _extract_text(book_path)
    chunks = _split_into_chunks(full_text)
    progress["total_chunks"] = len(chunks)
    print(f"[Kokoro] Split into {len(chunks)} chunks")

    # Save chunk manifest for reproducibility
    manifest_path = output_dir / "chunks_manifest.json"
    if not manifest_path.exists():
        manifest_path.write_text(json.dumps(
            [{"index": i, "length": len(c), "preview": c[:80]} for i, c in enumerate(chunks)],
            indent=2
        ))

    # Process each chunk
    completed = set(progress["completed_chunks"])
    failed_chunks = []

    for i, chunk_text in enumerate(chunks):
        if i in completed:
            continue

        chunk_file = chunks_dir / f"chunk_{i:04d}.wav"
        print(f"[Kokoro] Processing chunk {i+1}/{len(chunks)} ({len(chunk_text)} chars)...")

        success = _synthesize_with_kokoro(chunk_text, chunk_file, voice)
        if success:
            completed.add(i)
            progress["completed_chunks"] = sorted(completed)
            _save_progress(output_dir, progress)
            print(f"[Kokoro]   Chunk {i+1} done.")
        else:
            failed_chunks.append(i)
            print(f"[Kokoro]   Chunk {i+1} FAILED.")

    # Concatenate all completed chunks
    print(f"[Kokoro] Concatenating {len(completed)} chunks into final audiobook...")
    wav_files = sorted(chunks_dir.glob("chunk_*.wav"))
    audiobook_path = output_dir / f"{_sanitize(book_title)}_audiobook.wav"

    if wav_files:
        _concatenate_wav_files(wav_files, audiobook_path)
        print(f"[Kokoro] Audiobook saved: {audiobook_path}")
    else:
        print("[Kokoro] No audio chunks were generated.")
        audiobook_path = None

    return {
        "audiobook_path": audiobook_path,
        "total_chunks": len(chunks),
        "completed_chunks": len(completed),
        "failed_chunks": failed_chunks,
        "resumed": resumed,
    }


def _sanitize(name: str) -> str:
    return re.sub(r'[^\w\s-]', '', name).strip().replace(' ', '_')[:80]


if __name__ == "__main__":
    import sys
    from dotenv import load_dotenv
    load_dotenv()

    title = sys.argv[1] if len(sys.argv) > 1 else "Test Book"
    book_file = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("test.pdf")
    out = Path(sys.argv[3]) if len(sys.argv) > 3 else Path("./staging/test_audiobook")

    result = generate_audiobook(title, book_file, out)
    print(f"\nResult: {json.dumps({k: str(v) for k, v in result.items()}, indent=2)}")
