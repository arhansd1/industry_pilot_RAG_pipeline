# RAG Pipeline for Course Content

A Retrieval-Augmented Generation (RAG) pipeline that processes course materials and video content from PostgreSQL, generates embeddings using Google's Generative AI, and stores them in Qdrant for semantic search.

## Quick Start - Video Processing

### Use as Function (Recommended)
Import and call from any pipeline:

```python
from Video.resource_updater import update_resource

# Update specific resource
result = update_resource(course_id=329, module_id=575, resource_id=1564)

# Update all resources in a module
result = update_resource(course_id=329, module_id=575)

# Update entire course
result = update_resource(course_id=329)

# Check result
if result["success"]:
    print(f"✓ Updated {result['resources_processed']} resources")
    print(f"Total vectors: {result['total_vectors']}")
else:
    print(f"✗ Failed: {result['message']}")
```

**Result Structure:**
```python
{
    "success": True,
    "message": "Successfully updated resource 1564",
    "course_id": 329,
    "module_id": 575,
    "resource_id": 1564,
    "resources_processed": 1,
    "total_vectors": 15234
}
```

### Run as Standalone Script
Edit the configuration at the top of `resource_updater.py`:

```python
# CONFIGURE UPDATE SCOPE HERE
COURSE_ID = 329          # Required
MODULE_ID = 575          # Optional: None = all modules
RESOURCE_ID = 1564       # Optional: None = all resources
```

Then run:
```bash
python Video/resource_updater.py
```

### What It Does
Single command that:
1. ✓ **Deletes** existing vectors for the specified scope
2. ✓ **Fetches** fresh data from PostgreSQL
3. ✓ **Transforms** and chunks content (250 words)
4. ✓ **Generates** embeddings (Google text-embedding-004)
5. ✓ **Uploads** to Qdrant with automatic indexing

## Prerequisites

- Python 3.8+
- PostgreSQL database with course content
- Qdrant vector database
- Google Generative AI API key

## Setup

1. **Install dependencies**
```bash
pip install -r requirements.txt
```

2. **Configure `.env` file**
```env
# PostgreSQL
POSTGRES_HOST=your_host
POSTGRES_PORT=5432
POSTGRES_DB=your_db
POSTGRES_USER=your_user
POSTGRES_PASSWORD=your_password

# Qdrant
QDRANT_URL=your_qdrant_url
QDRANT_API_KEY=your_api_key
QDRANT_COLLECTION_NAME_VIDEO=video_embeddings
QDRANT_COLLECTION_NAME_MATERIAL=material_embeddings

# Google AI
GOOGLE_API_KEY=your_google_api_key
```

## Video Processing Details

### Flexible Scope Control

Three levels of granularity:

| Scope | Parameters | Use Case |
|-------|-----------|----------|
| **Resource** | `course_id`, `module_id`, `resource_id` | Single resource changed |
| **Module** | `course_id`, `module_id` | All resources in module updated |
| **Course** | `course_id` | Entire course needs refresh |

### Data Flow

```
PostgreSQL → Extraction → Transformation → Chunking → Embedding → Qdrant
   (course.t_resource)      (JSON parsing)    (250 words)   (768 dims)  (with indexes)
```

### Chunk Structure
```json
{
  "course_id": 329,
  "module_id": 575,
  "resource_id": 1564,
  "chunk_id": "329_575_1564_0",
  "chunk_type": "summary" | "chapter",
  "chunk_index": 0,
  "text": "content...",
  "topic_title": "...",      // chapters only
  "subtopic_title": "..."    // chapters only
}
```

## Material Processing

Place PDFs in `Material/documents/` as `{course_id}_material.pdf`

**Update specific course:**
```bash
python Material/material_updater.py
```

**Update all courses:**
```bash
python Material/main.py
```

## Testing & Utilities

### 1. Semantic Search
```bash
# Edit test_chunks.py: set COURSE_ID, MODULE_ID, RESOURCE_ID
python Video/test_chunks.py
```
Interactive search with filtering, returns top 5 similar chunks.

### 2. Find Chunks (Direct Lookup)
```bash
# Edit find_chunks.py: set IDs
python TEST/find_chunks.py
```
Lists all chunks matching criteria with full metadata.

### 3. Delete Chunks
```bash
# Edit chunk_deleter.py: set IDs
python TEST/chunk_deleter.py
```
Deletes chunks by scope (requires `YES` confirmation).

### 4. Full Pipeline (Complete Refresh)
```bash
python video_main.py
```
Clears entire video collection and reprocesses all data.

## Project Structure
```
industry_pilot_RAG_pipeline/
├── Video/
│   ├── resource_updater.py     # Main update function
│   ├── embedder.py             # Embedding operations
│   ├── extracter.py            # PostgreSQL extraction
│   └── test_chunks.py          # Semantic search
├── Material/
│   ├── material_updater.py     # Material updates
│   └── documents/              # PDF storage
├── TEST/
│   ├── find_chunks.py          # Chunk lookup
│   ├── chunk_deleter.py        # Chunk deletion
│   └── create_indexes.py       # Manual indexing
├── video_main.py               # Full pipeline
└── .env                        # Configuration
```

## Best Practices

- **Use function import** for pipeline integration
- **Run standalone** for manual updates or testing
- **Scope appropriately**: resource > module > course for efficiency
- Indexes are auto-created by all operations
- Full text stored in payload for retrieval
- Batch processing with rate limiting built-in

## Troubleshooting

| Issue | Solution |
|-------|----------|
| No chunks found | Verify IDs exist in PostgreSQL |
| Embedding errors | Check `GOOGLE_API_KEY` |
| Connection fails | Verify credentials in `.env` |
| "Index required" | Run any updater (auto-creates) |

## License

[Specify your license here]