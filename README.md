# GravityCar D&D 1st Edition RAG System

A Retrieval-Augmented Generation (RAG) system for Advanced Dungeons & Dragons 1st Edition rulebooks, featuring intelligent chunking, entity-aware retrieval, and adaptive semantic filtering.

---

## 🎲 What Is This?

A semantic search and question-answering system that allows you to query AD&D 1st Edition rules using natural language. Ask about monster stats, spell descriptions, character progression, or game mechanics—the system retrieves relevant information and provides accurate answers using GPT-4.

**Example queries:**
- "How many experience points does a fighter need to reach 9th level?"
- "Compare the stats of a black dragon versus a gold dragon"
- "What are the unique abilities that only thieves have?"
- "What happens when you cast charm person on someone?"

---

## ✨ Key Features

### **Intelligent Chunking**
- **Category-Aware** (Monster Manual): Recognizes monster categories (DEMON, DRAGON, etc.) and nested entries
- **Table-Aware** (Player's Handbook): Preserves table structure, merges related notes
- **Statistics Integration**: Monster stats embedded in searchable text for LLM access

### **High-Quality PDF Conversion**
- Uses **Docling** for superior markdown conversion with table preservation
- Preserves document structure, reading order, and formatting
- Maintains complete paragraphs (no truncation like other parsers)

### **Entity-Aware Retrieval**
- Automatically detects comparison queries ("X vs Y", "compare X and Y")
- Ensures both entities are retrieved before ranking
- Smart category context for nested monsters (e.g., specific demon types)

### **Adaptive Gap Detection**
- Returns 2-10 results based on semantic similarity drop-offs, not arbitrary k values
- Gap threshold of 0.1 identifies "semantic cliffs" where relevance drops
- Distance threshold fallback (0.4) when no clear gap exists
- Constraint application: minimum 2 results, maximum k (default 5)

### **Production-Ready Architecture**
- Organized package structure (`src/chunkers`, `src/embedders`, `src/query`, `src/converters`)
- Comprehensive dependency management (`requirements.txt`)
- Automated setup scripts
- Extensive documentation

---

## 🏗️ Architecture

```
Query → Embedding → ChromaDB Vector Search → Gap Detection → 
Entity-Aware Ranking → Context Assembly → OpenAI GPT-4 → Answer
```

### Technologies

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Vector Database** | ChromaDB 1.1.1 | Stores embeddings and metadata |
| **Embedding Model** | all-mpnet-base-v2 (768d) | Semantic text embeddings |
| **LLM** | OpenAI GPT-4o-mini | Answer generation |
| **PDF Conversion** | Docling 2.55.1 | High-quality markdown extraction |
| **Configuration** | python-dotenv | Environment variable management |

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.10+** (tested with Python 3.12.3)
- **OpenAI API Key**
- **ChromaDB** (running on localhost:8060)

### 1. Installation

```bash
# Clone or navigate to project directory
cd /path/to/chroma

# Run automated setup (recommended)
./scripts/setup_venv.sh

# Or manual setup
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Environment

Create a `.env` file in the project root:

```bash
# OpenAI API Configuration
OPENAI_API_KEY=sk-your-api-key-here

# ChromaDB Configuration (optional, defaults shown)
CHROMA_HOST=localhost
CHROMA_PORT=8060
```

### 3. Start ChromaDB

```bash
# Using the provided script
./scripts/start_chroma.sh

# Or manually with Docker
docker run -p 8060:8000 chromadb/chroma

# Or with pip install
pip install chromadb
chroma run --path ./chroma_data --port 8060
```

### 4. Process a Book

#### Convert PDF to Markdown (if needed):
```bash
python src/converters/pdf_converter.py
# Follow prompts to convert PDFs to markdown
```

#### Chunk the Markdown:
```bash
# Monster Manual
python src/chunkers/monster_encyclopedia.py data/markdown/Monster_Manual_(1e).md

# Player's Handbook
python src/chunkers/players_handbook.py data/markdown/Players_Handbook_(1e).md
```

#### Embed and Store:
```bash
# Monster Manual
python src/embedders/docling_embedder.py \
  data/chunks/chunks_Monster_Manual_(1e).json \
  dnd_monster_manual

# Player's Handbook
python src/embedders/docling_embedder.py \
  data/chunks/chunks_Players_Handbook_(1e).json \
  dnd_players_handbook
```

### 5. Query the System

```bash
# Single query
python src/query/docling_query.py "How many HP does a beholder have?"

# Interactive mode
python src/query/docling_query.py

# With options
python src/query/docling_query.py "Compare black dragon vs gold dragon" \
  --collection dnd_monster_manual \
  --k 5 \
  --distance-threshold 0.4 \
  --debug
```

---

## 📁 Project Structure

```
/home/mike/projects/rag/chroma/          # ChromaDB host (shared resource)
├── [GUID directories...]                 # ChromaDB collection data
├── chroma.sqlite3                        # ChromaDB metadata
├── .env                                  # Configuration (API keys)
│
├── src/                                  # Python package
│   ├── chunkers/                         # Document chunking
│   │   ├── monster_encyclopedia.py       # Monster Manual chunker
│   │   └── players_handbook.py           # Player's Handbook chunker
│   ├── embedders/                        # Embedding generation
│   │   └── docling_embedder.py           # Universal embedder
│   ├── query/                            # Query/RAG system
│   │   └── docling_query.py              # Main query interface
│   ├── converters/                       # PDF conversion
│   │   └── pdf_converter.py              # PDF to markdown converter
│   └── utils/                            # Utilities
│
├── scripts/                              # Executable scripts
│   ├── setup_venv.sh                     # Setup virtual environment
│   ├── start_chroma.sh                   # Start ChromaDB server
│   ├── setup_docling.sh                  # Setup Docling
│   ├── benchmark_models.py               # Model benchmarking
│   └── list_chromadb_collections.py      # List collections
│
├── data/                                 # Data files
│   ├── source_pdfs/                      # Original PDFs
│   ├── markdown/                         # Converted markdown
│   └── chunks/                           # Chunked JSON files
│
├── docs/                                 # Documentation
│   ├── implementations/                  # Implementation details
│   ├── setup/                            # Setup guides
│   ├── architecture/                     # System architecture
│   ├── implementation_notes/             # Development notes
│   ├── early_notes/                      # Historical context
│   ├── questions/                        # Q&A log
│   └── todos/                            # Project planning
│
├── tests/                                # Test files (empty)
├── archive/                              # Archived code
├── venv/                                 # Virtual environment
├── requirements.txt                      # Core dependencies
├── requirements-dev.txt                  # Dev dependencies
└── README.md                             # This file
```

---

## 📖 Usage Examples

### Basic Queries

```bash
# Monster information
python src/query/docling_query.py "Tell me about beholders"

# Spell descriptions
python src/query/docling_query.py "What does the charm person spell do?"

# Character progression
python src/query/docling_query.py "How many XP does a fighter need for 9th level?"

# Game mechanics
python src/query/docling_query.py "What are the thief's backstab rules?"
```

### Comparison Queries (Entity-Aware)

```bash
# Monster comparisons
python src/query/docling_query.py "Black dragon vs gold dragon"
python src/query/docling_query.py "Compare owlbear and orc"
python src/query/docling_query.py "Differences between beholder and medusa"

# The system automatically:
# 1. Detects comparison pattern
# 2. Retrieves BOTH entities
# 3. Ranks them at top of results
# 4. Provides comprehensive comparison
```

### Advanced Options

```bash
# Retrieve more chunks
python src/query/docling_query.py "fighter abilities" -k 10

# Show debug information (gap detection)
python src/query/docling_query.py "dragon stats" --debug

# Adjust distance threshold
python src/query/docling_query.py "spell list" --distance-threshold 0.5

# Show context sent to GPT
python src/query/docling_query.py "paladin rules" --show-context

# Use different OpenAI model
python src/query/docling_query.py "thief abilities" --model gpt-4

# Specify collection
python src/query/docling_query.py "fireball spell" \
  --collection dnd_players_handbook
```

### Test Mode

```bash
# Run predefined test queries
python src/query/docling_query.py --test
```

---

## 🔧 Development Setup

### Create Development Environment

```bash
# Install dev dependencies
source venv/bin/activate
pip install -r requirements-dev.txt

# This includes:
# - pytest (testing)
# - black (code formatting)
# - flake8 (linting)
# - ipython (interactive shell)
# - mypy (type checking)
```

### Run Tests

```bash
# (Tests directory currently empty - coming soon!)
pytest tests/
```

### Code Quality

```bash
# Format code
black src/

# Lint code
flake8 src/

# Type check
mypy src/
```

---

## 📚 Documentation

For detailed documentation, see:

- **[Setup Guides](docs/setup/)** - Installation, ChromaDB setup
- **[Implementation Details](docs/implementations/)** - Deep dives into algorithms
- **[Architecture](docs/architecture/)** - System design and data flow
- **[Development Notes](docs/implementation_notes/)** - Technical decisions
- **[Project Planning](docs/todos/)** - Roadmap and cleanup tasks

---

## 🎯 The Critical Test: Fighter XP Table

This was the **acid test** for data quality. Previous parsing methods failed to extract this table correctly:

```bash
python src/query/docling_query.py \
  "How many experience points does a fighter need to become 9th level?"
```

**Expected Result:**
- ✅ Retrieved chunk contains the complete FIGHTERS TABLE
- ✅ Table shows: `250,001—500,000 | 9 | 9 | Lord`
- ✅ GPT correctly answers: "A fighter needs **250,001 experience points** to reach 9th level (Lord)"

**Why This Matters:**
- Tests table extraction quality
- Tests chunking strategy (table must stay intact)
- Tests retrieval accuracy (must find right table)
- Tests LLM understanding (must parse table correctly)

---

## 🔍 How It Works

### 1. PDF → Markdown Conversion

**Docling** intelligently parses PDFs:
- Preserves document structure
- Extracts tables accurately
- Maintains reading order
- Complete paragraphs (no truncation)

### 2. Intelligent Chunking

**Monster Manual**: Category-aware chunking
- Detects top-level categories (DEMON, DRAGON, etc.)
- Identifies nested monster entries
- Extracts and structures statistics
- Links monsters to parent categories

**Player's Handbook**: Table-aware chunking
- Each spell = 1 chunk
- Tables + related notes merged
- Section hierarchy preserved
- Metadata captured (type, title, character count)

### 3. Embedding & Storage

- **Model**: `all-mpnet-base-v2` (768 dimensions)
- **Strategy**: Statistics prepended to text for better searchability
- **Metadata**: Type, title, page, category, parent relationships
- **Storage**: ChromaDB with efficient indexing

### 4. Entity-Aware Retrieval

When a comparison query is detected:
1. **Expand search**: Retrieve k×3 results (max 15)
2. **Entity matching**: Find exact entity names in results
3. **Priority reordering**: Move matched entities to front
4. **Gap detection**: Apply adaptive filtering

### 5. Adaptive Gap Detection

Instead of returning fixed k results:
1. Calculate gaps between consecutive similarity scores
2. Skip first gap (avoid cutting after exceptional match)
3. Find largest gap starting from position 2
4. If gap ≥ 0.1: cut at that position (semantic cliff)
5. Else: use distance threshold (best + 0.4)
6. Apply constraints: min 2, max k

**Benefits:**
- Returns relevant results only
- Stops before semantic cliff
- Adapts to query difficulty
- More accurate than fixed k

---

## 🚧 Comparison to Previous Approaches

| Phase | Method | Tables | Prose | Result |
|-------|--------|--------|-------|--------|
| 1-2 | OCR text files | ❌ Broken | ❌ Broken | Garbage |
| 3A | Docling (CPU) | ⚠️ N/A | ⚠️ N/A | CPU incompatible |
| 3B | PyMuPDF | ❌ Broken | ✅ Good | Unusable tables |
| 4 | LlamaParse | ✅ Perfect | ❌ Truncated | Great tables, broken prose |
| **5** | **Docling (AVX2)** | **✅ Perfect** | **✅ Perfect** | **✅ Winner!** |

---

## 🔧 Troubleshooting

### ChromaDB Connection Error

```bash
# Check if ChromaDB is running
curl http://localhost:8060/api/v1/heartbeat

# Should return: {}

# If not running, start it
./scripts/start_chroma.sh
```

### OpenAI API Key Error

```bash
# Verify .env file exists
cat .env | grep OPENAI_API_KEY

# Should show: OPENAI_API_KEY=sk-...
```

### "Collection not found" Error

```bash
# List available collections
python scripts/list_chromadb_collections.py

# Re-run embedding step if collection missing
python src/embedders/docling_embedder.py data/chunks/chunks_X.json collection_name
```

### Import Errors

```bash
# Make sure virtual environment is activated
source venv/bin/activate

# Verify Python version
python --version  # Should be 3.10+

# Reinstall dependencies
pip install -r requirements.txt
```

### Module Not Found

```bash
# Run scripts from project root
cd /home/mike/projects/rag/chroma
python src/query/docling_query.py "your query"
```

---

## 🛣️ Roadmap

### Completed ✅
- High-quality PDF conversion (Docling)
- Intelligent chunking (category-aware, table-aware)
- Entity-aware retrieval
- Adaptive gap detection
- Project reorganization
- Comprehensive documentation

### In Progress 🚧
- Testing framework
- Additional rulebooks (Fiend Folio, Monster Manual II)

### Planned 📋
- Web interface
- Hybrid search (BM25 + semantic)
- Cross-encoder reranking
- Multi-book queries
- Citation tracking
- Docker deployment

---

## 📄 License

[Your license here]

---

## 🙏 Acknowledgments

- **Docling**: For excellent PDF parsing
- **ChromaDB**: For efficient vector storage
- **OpenAI**: For powerful language models
- **Sentence Transformers**: For quality embeddings
- **TSR**: For Advanced Dungeons & Dragons 1st Edition

---

## 📞 Contact

[Your contact information]

---

**Package Name**: `gravitycar_dnd1st_rag_system`  
**Python**: 3.10+  
**Status**: Production Ready ✅
