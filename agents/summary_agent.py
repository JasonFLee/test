"""
Summary Podcast Agent
---------------------
Takes a book file (PDF/EPUB), extracts text, generates an AI summary,
then converts that summary into a podcast-style audio file using TTS.
"""

import os
import json
import re
from pathlib import Path
from openai import OpenAI

# PDF/EPUB text extraction
import PyPDF2
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup


def _extract_text_pdf(path: Path, max_chars: int = 200_000) -> str:
    text_parts = []
    with open(path, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        for page in reader.pages:
            text_parts.append(page.extract_text() or "")
            if sum(len(t) for t in text_parts) > max_chars:
                break
    return "\n".join(text_parts)[:max_chars]


def _extract_text_epub(path: Path, max_chars: int = 200_000) -> str:
    book = epub.read_epub(str(path))
    text_parts = []
    for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
        soup = BeautifulSoup(item.get_content(), "html.parser")
        text_parts.append(soup.get_text(separator="\n"))
        if sum(len(t) for t in text_parts) > max_chars:
            break
    return "\n".join(text_parts)[:max_chars]


def _extract_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return _extract_text_pdf(path)
    elif suffix == ".epub":
        return _extract_text_epub(path)
    elif suffix == ".txt":
        return path.read_text()[:200_000]
    else:
        return f"[Could not extract text from {suffix} file]"


def generate_summary(book_title: str, book_path: Path) -> str:
    """Generate a podcast-style summary script using OpenAI."""
    print(f"[Summary] Extracting text from {book_path.name}...")
    text = _extract_text(book_path)

    if len(text) < 100:
        # Fallback: generate summary from title alone
        print("[Summary] Very little text extracted, summarizing from title only.")
        text = f"Book title: {book_title}"

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    print(f"[Summary] Generating podcast summary for '{book_title}'...")
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a podcast host who creates engaging 10-15 minute "
                    "book summary episodes. Write a complete podcast script that:\n"
                    "1. Opens with a catchy intro about why this book matters\n"
                    "2. Covers the key themes, arguments, and insights\n"
                    "3. Highlights 3-5 most important takeaways\n"
                    "4. Ends with a thoughtful conclusion and recommendation\n\n"
                    "Write it conversationally as if speaking to a listener. "
                    "Use natural transitions. Aim for about 2500-3500 words."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Create a podcast summary episode for the book '{book_title}'.\n\n"
                    f"Here is text from the book to base your summary on:\n\n"
                    f"{text[:100_000]}"
                ),
            },
        ],
        max_tokens=4096,
        temperature=0.7,
    )

    script = response.choices[0].message.content
    print(f"[Summary] Generated {len(script)} chars of podcast script.")
    return script


def create_podcast_audio(script: str, output_path: Path) -> Path:
    """Convert the podcast script to audio using OpenAI TTS."""
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    print(f"[Summary] Converting summary to podcast audio...")

    # Split into chunks if script is very long (TTS has input limits)
    max_chunk = 4096
    chunks = []
    words = script.split()
    current_chunk = []
    current_len = 0
    for word in words:
        if current_len + len(word) + 1 > max_chunk:
            chunks.append(" ".join(current_chunk))
            current_chunk = [word]
            current_len = len(word)
        else:
            current_chunk.append(word)
            current_len += len(word) + 1
    if current_chunk:
        chunks.append(" ".join(current_chunk))

    audio_parts = []
    for i, chunk in enumerate(chunks):
        print(f"[Summary]   TTS chunk {i+1}/{len(chunks)}...")
        response = client.audio.speech.create(
            model="tts-1-hd",
            voice="onyx",
            input=chunk,
        )
        audio_parts.append(response.content)

    # Concatenate audio
    full_audio = b"".join(audio_parts)
    output_path.write_bytes(full_audio)
    print(f"[Summary] Podcast audio saved: {output_path} ({len(full_audio)} bytes)")
    return output_path


def generate_podcast(book_title: str, book_path: Path, output_dir: Path) -> dict:
    """
    Full pipeline: extract -> summarize -> TTS.
    Returns dict with script_path and audio_path.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate script
    script = generate_summary(book_title, book_path)
    script_path = output_dir / "podcast_summary.txt"
    script_path.write_text(script)

    # Generate audio
    audio_path = output_dir / "podcast_summary.mp3"
    create_podcast_audio(script, audio_path)

    return {
        "script_path": script_path,
        "audio_path": audio_path,
        "word_count": len(script.split()),
    }


if __name__ == "__main__":
    import sys
    from dotenv import load_dotenv
    load_dotenv()

    title = sys.argv[1] if len(sys.argv) > 1 else "Atomic Habits"
    book_file = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("test.pdf")
    out = Path(sys.argv[3]) if len(sys.argv) > 3 else Path("./staging/test_summary")

    result = generate_podcast(title, book_file, out)
    print(f"Result: {result}")
