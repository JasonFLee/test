# Face Finder - Reverse Face Search Tool

Find all photos of a person online given a single face photo. Combines multiple search engines and AI-powered face verification.

## How It Works

1. **Face Detection** - Detects and extracts faces from your input photo using DeepFace
2. **Multi-Engine Search** - Searches across Google Lens, Yandex, Bing, TinEye, and more
3. **Face Verification** - Downloads candidate images and verifies they're the same person using Facenet512 embeddings
4. **Report** - Generates an HTML + JSON report with all confirmed matches

## Install

```bash
pip install -r requirements.txt
```

## Quick Start

### Web GUI (Recommended)

```bash
# Launch the interactive web interface
python gui.py

# With API keys for deeper search
python gui.py --serpapi-key YOUR_KEY --bing-key YOUR_KEY

# Custom port
python gui.py --port 8080
```

Then open http://localhost:5000 in your browser. Drag & drop a face photo, hit search, and click any matched face to open the source page.

### Command Line

```bash
# Basic usage - runs direct searches + generates manual search links
python face_finder.py photo.jpg

# With SerpAPI for automated Google Lens + Yandex (best results)
python face_finder.py photo.jpg --serpapi-key YOUR_SERPAPI_KEY

# Custom output dir and stricter matching
python face_finder.py photo.jpg -o results/ -t 0.45

# Skip face verification, just gather URLs
python face_finder.py photo.jpg --no-verify
```

## API Keys (Optional but Recommended)

For the best automated results, get one or more of these API keys:

| Service | What it searches | Free tier | Get key |
|---------|-----------------|-----------|---------|
| **SerpAPI** | Google Lens + Yandex + Google Reverse | 100 searches/month | https://serpapi.com |
| **Bing Visual Search** | Bing image index | 1000 calls/month | https://portal.azure.com |

Set via CLI flags or environment variables:
```bash
export SERPAPI_KEY=your_key
export BING_VISUAL_SEARCH_KEY=your_key
```

## Manual Search (No API Key Needed)

The tool always generates links for manual searching. For finding a lost person, **manually searching these sites gives the best results**:

1. **[Yandex Images](https://yandex.com/images/)** - #1 for face matching among general search engines
2. **[FaceCheck.ID](https://facecheck.id/)** - Dedicated face search engine, free tier available
3. **[PimEyes](https://pimeyes.com/)** - Powerful face search, limited free searches
4. **[Google Lens](https://lens.google.com/)** - Good general reverse image search
5. **[TinEye](https://tineye.com/)** - Finds exact/near-exact copies

## Options

```
--output, -o       Output directory (default: face_finder_results)
--serpapi-key       SerpAPI key for automated search
--bing-key          Bing Visual Search API key
--threshold, -t    Face match threshold, lower=stricter (default: 0.60)
--max-downloads    Max images to download for verification (default: 100)
--no-verify        Skip face verification step
```

## Tips for Best Results

- Use a **clear, well-lit, frontal face photo** as input
- **Yandex** is widely considered the best general search engine for face matching
- **FaceCheck.ID** and **PimEyes** are dedicated face search engines worth trying manually
- Lower the threshold (e.g., `--threshold 0.45`) for stricter matching with fewer false positives
- Use `--serpapi-key` for the most comprehensive automated results
- The tool works best as a **starting point** - combine automated results with manual searching

## Output

Results are saved to the output directory:
- `report.html` - Visual report you can open in a browser
- `report.json` - Machine-readable results
- `search_face.jpg` - The extracted face used for searching
- `downloads/` - Downloaded candidate images
