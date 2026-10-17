# Realtime Source Code Analyzer

A Flask web app that lets you paste a **GitHub repository URL**, downloads and indexes its Python source code, and then lets you **chat with the codebase** in plain English ("What does `helper.py` do?", "Where is the model trained?"). It is a Retrieval-Augmented Generation (RAG) project built with LangChain, ChromaDB, HuggingFace embeddings and a Groq-hosted LLM.

---

## Table of Contents

1. [Features](#features)
2. [How It Works](#how-it-works)
3. [Tech Stack](#tech-stack)
4. [Project Structure](#project-structure)
5. [File-by-File Explanation](#file-by-file-explanation)
6. [API Endpoints](#api-endpoints)
7. [Installation & Setup](#installation--setup)
8. [Usage](#usage)
9. [Configuration](#configuration)
10. [Troubleshooting](#troubleshooting)
11. [Known Limitations](#known-limitations)
12. [Future Improvements](#future-improvements)
13. [License](#license)

---

## Features

- Paste any public GitHub repo URL; the app clones and indexes it automatically.
- Live status message in the UI: *downloading...*, *indexed N chunks*, or the exact error.
- Ask natural-language questions about the code in a chat window.
- Conversation memory: follow-up questions understand earlier context.
- Type `clear` to delete the downloaded repo, its index and the chat memory, then load a new repo without restarting the server.
- Loading a new URL without clearing also works; it replaces the previous repo.

## How It Works

The app runs in two phases.

### Phase 1: Ingestion (when you click **Send** with a URL)

```
GitHub URL
   |
   v
git clone  ->  repo/ folder           (src/helper.py: repo_ingestion)
   |
   v
Load all **/*.py files                (src/helper.py: load_repo, LanguageParser)
   |
   v
Split into ~2000-char chunks          (src/helper.py: text_splitter, 200 overlap)
   |
   v
Embed each chunk (all-MiniLM-L6-v2)   (src/helper.py: load_embeddings)
   |
   v
Store vectors in ChromaDB             (db/ folder)
```

### Phase 2: Question answering (when you chat)

```
Your question
   |
   v
Retriever finds the 8 most relevant chunks (MMR search)
   |
   v
Chunks + question + chat history  ->  Groq LLM (openai/gpt-oss-120b)
   |
   v
Answer shown in the chat window
```

`ConversationalRetrievalChain` combines retrieval with `ConversationSummaryMemory`, which keeps a running summary of the conversation so follow-up questions work.

## Tech Stack

| Area | Technology |
|------|-----------|
| Web framework | Flask |
| Frontend | HTML, CSS, jQuery, Bootstrap |
| LLM | Groq API, model `openai/gpt-oss-120b` (via `langchain-groq`) |
| Orchestration | LangChain (`langchain`, `langchain-classic`, `langchain-community`) |
| Embeddings | HuggingFace `sentence-transformers/all-MiniLM-L6-v2` (runs locally) |
| Vector database | ChromaDB (`langchain-chroma`), persisted in `db/` |
| Repo download | GitPython |
| Config | python-dotenv |

## Project Structure

```
Realtime-Source-Code-Analyzer/
├── app.py                 # Flask app: routes, LLM, retrieval chain
├── store_index.py         # Standalone script to index a repo from the command line
├── template.py            # One-time scaffold script that created the project files
├── setup.py               # Makes `src` installable as a package (pip install -e .)
├── requrirements.txt      # Python dependencies
├── .env                   # Secrets (GROQ_API_KEY) - NOT committed
├── LICENSE                # MIT License
├── src/
│   ├── __init__.py
│   ├── helper.py          # Clone, load, split, embed functions
│   └── prompt.py          # Reserved for custom prompts (currently empty)
├── templates/
│   └── index.html         # UI: URL box + chat window
├── static/
│   ├── style.css          # Chat window styling
│   └── jquery.min.js      # Local jQuery copy (page currently loads jQuery from CDN)
├── research/
│   └── trials.ipynb       # Notebook used to experiment before building the app
├── repo/                  # (generated) the cloned GitHub repo
└── db/                    # (generated) ChromaDB vector store
```

## File-by-File Explanation

### `app.py`
The main application.
- Loads the `GROQ_API_KEY` from `.env`.
- Creates the embeddings model and opens the Chroma store in `db/`.
- Creates the Groq chat model, the summary memory and the `ConversationalRetrievalChain` (MMR retriever, `k=8`).
- `clear_everything()` deletes `repo/`, empties the vector store and wipes chat memory.
- Defines the three routes listed under [API Endpoints](#api-endpoints).

### `src/helper.py`
Reusable building blocks:
| Function | Purpose |
|----------|---------|
| `repo_ingestion(repo_url)` | Deletes any old `repo/` folder, then clones the given URL into `repo/` |
| `clear_repo()` | Deletes `repo/` (handles Windows read-only git files) |
| `load_repo(path)` | Loads every `.py` file with a Python-aware parser (`LanguageParser`) |
| `text_splitter(docs)` | Splits code into 2000-character chunks with 200 overlap, respecting Python syntax |
| `load_embeddings()` | Loads the HuggingFace MiniLM embedding model |

### `store_index.py`
Command-line alternative to the UI. Clones a repo and builds the Chroma index in `db/`:
```bash
python store_index.py https://github.com/<user>/<repo>
```
With no argument it uses a default sample URL set in the file.

### `templates/index.html`
Two parts on one page:
1. **URL box + Send button.** Sends the URL to `/chatbot` and shows the status message (blue/green/red text).
2. **Chat window.** Sends each message to `/get` and shows the reply.

### `template.py`
A one-time helper that generated the empty project skeleton (folders and files). Not used at runtime.

### `setup.py`
Lets the `src` package be imported anywhere after `pip install -e .` (the `-e .` line in the requirements file does this).

### `research/trials.ipynb`
Notebook used to prototype the pipeline (loading, splitting, embedding) before moving the code into `src/helper.py`.

## API Endpoints

| Route | Method | Body | Description |
|-------|--------|------|-------------|
| `/` | GET | - | Serves the web UI |
| `/chatbot` | POST | `question=<GitHub URL or "clear">` | Clones and indexes the repo, or clears everything. Returns JSON `{"response": "..."}`; errors return status 500 with the message |
| `/get` | POST | `msg=<your question or "clear">` | Answers a question about the indexed code, or clears everything |

Example:
```bash
curl -X POST http://127.0.0.1:8080/chatbot -d "question=https://github.com/<user>/<repo>"
# {"response": "Indexed 5 chunks from https://github.com/<user>/<repo>"}
```

## Installation & Setup

### Prerequisites
- Python 3.10+
- Git installed and available on your PATH
- A free [Groq API key](https://console.groq.com/keys)
- Internet access (GitHub, Groq, and the first-time embedding model download)

### Steps

```bash
# 1. Clone this project
git clone https://github.com/sauravyadav7721/Realtime-Source-Code-Analyzer.git
cd Realtime-Source-Code-Analyzer

# 2. Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS / Linux

# 3. Install dependencies
pip install -r requrirements.txt
```

### Add your API key

Create a file named `.env` in the project root:

```
GROQ_API_KEY=your_groq_api_key_here
```

Never commit this file (it is already in `.gitignore`).

### Run

```bash
python app.py
```

Open **http://127.0.0.1:8080** in your browser. The first start is slow because the embedding model is downloaded.

## Usage

1. Open the app in your browser.
2. Paste a public GitHub URL (for example `https://github.com/user/project`) into the top box and click **Send**.
3. Wait for the green message: *"Indexed N chunks from <url>"*.
4. Ask questions in the chat window, for example:
   - "Give me an overview of this project"
   - "Which function loads the dataset?"
   - "Explain the training pipeline"
5. To switch repos, type `clear` (in either box), then paste a new URL.

| Message colour | Meaning |
|----------------|---------|
| Black | Working (downloading / clearing) |
| Green | Success |
| Red | Error (bad URL, private repo, network problem, empty input) |

## Configuration

| Setting | Where | Default |
|---------|-------|---------|
| Groq API key | `.env` -> `GROQ_API_KEY` | none (required) |
| LLM model | `app.py` -> `ChatGroq(model=...)` | `openai/gpt-oss-120b` |
| Embedding model | `src/helper.py` -> `load_embeddings` | `all-MiniLM-L6-v2` |
| Chunk size / overlap | `src/helper.py` -> `text_splitter` | 2000 / 200 |
| Chunks retrieved per question | `app.py` -> `search_kwargs={"k": 8}` | 8 |
| Port | `app.py` -> `app.run(port=...)` | 8080 |
| Vector store folder | `app.py` -> `persist_directory` | `db` |

## Troubleshooting

| Problem | Cause / Fix |
|---------|-------------|
| Send button does nothing | jQuery failed to load. Check your internet connection (the page loads jQuery from a CDN) |
| `destination path 'repo' already exists` | Old version of the code. Update `src/helper.py` - it now clears `repo/` before cloning |
| `Failed to index repo: ...` in red | Read the message: usually a wrong/private URL or no network |
| `TypeError` about `GROQ_API_KEY` at startup | `.env` is missing or the key name is wrong |
| `ModuleNotFoundError` | Re-run `pip install -r requrirements.txt` inside your activated virtual environment |
| Answers ignore the new repo | Type `clear`, then load the URL again |

## Known Limitations

- Only **Python files** (`**/*.py`) are indexed; other languages, notebooks and docs are ignored.
- Only **public** repositories can be cloned (no authentication is set up).
- One repo at a time, shared by everyone using the server (no per-user sessions).
- Large repositories can be slow to embed.
- `debug=True` and `host="0.0.0.0"` in `app.py` are for development only; do not expose it publicly as is.
- `repo/` and `db/` are generated at runtime and are excluded from git via `.gitignore`.

## Future Improvements

- Support more languages and file types (JS, Java, Markdown, notebooks).
- Support private repositories with a GitHub token.
- Per-user sessions and a separate index per repo.
- Show source file names alongside each answer.
- Custom prompt templates in `src/prompt.py`.
- Docker setup for easy deployment.

## License

Released under the [MIT License](LICENSE). Copyright (c) 2026 Saurav Yadav.
