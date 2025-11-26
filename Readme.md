# RAG Pipeline for Course Content

A Retrieval-Augmented Generation (RAG) pipeline that processes both course materials and video content from a PostgreSQL database, generates embeddings using Google's Generative AI, and stores them in Qdrant for efficient semantic search.

## Features

### Material Processing
- **Data Extraction**: Pulls course material content from PostgreSQL database
- **Text Processing**: Chunks and processes text for optimal embedding generation
- **Vector Embeddings**: Uses Google's text-embedding-004 model to generate embeddings
- **Vector Database**: Stores and manages material embeddings in Qdrant for fast semantic search

### Video Processing
- **Video Content Extraction**: Processes video summaries and chapter content from PostgreSQL
- **Smart Chunking**: Intelligently chunks content into 250-word segments while preserving context
- **Hierarchical Organization**: Maintains course → module → resource structure
- **Summary + Chapter Support**: Processes both video summaries and detailed chapter content
- **Indexed Filtering**: Automatic payload indexing for efficient filtering by course_id, module_id, and resource_id
- **Incremental Updates**: Update entire collection, specific courses, or individual resources

### General
- **Flexible Updates**: Full database refresh, course-level, or resource-level updates
- **Index Management**: Automatic creation of Qdrant payload indexes for optimal query performance
- **Scalable Architecture**: Designed to handle large volumes of content efficiently
- **Testing Tools**: Built-in utilities for searching, finding, and deleting chunks

## Prerequisites

- Python 3.8+
- PostgreSQL database with course content
- Qdrant vector database
- Google Generative AI API key
- Required Python packages (see `requirements.txt`)

## Setup

1. **Clone the repository**
```bash
   git clone <repository-url>
   cd industry_pilot_RAG_pipeline
```

2. **Set up virtual environment**
```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
   pip install -r requirements.txt
```

4. **Environment Variables**
   Create a `.env` file in the project root with the following variables:
```env
   # PostgreSQL Configuration
   POSTGRES_HOST=your_postgres_host
   POSTGRES_PORT=5432
   POSTGRES_DB=your_database
   POSTGRES_USER=your_username
   POSTGRES_PASSWORD=your_password
   
   # Qdrant Configuration
   QDRANT_URL=your_qdrant_url
   QDRANT_API_KEY=your_qdrant_api_key
   
   # Collection Names
   QDRANT_COLLECTION_NAME_VIDEO=video_embeddings
   QDRANT_COLLECTION_NAME_MATERIAL=material_embeddings
   
   # Google Generative AI
   GOOGLE_API_KEY=your_google_api_key
```

## Video Processing Pipeline

### Data Flow
1. **Extraction** (`extracter.py`): Fetches course data from PostgreSQL
   - Queries: `course.t_module` + `course.t_resource`
   - Fields: `course_id`, `module_id`, `resource_id`, `summary`, `chapters`
   - Output: `course_data.json`

2. **Transformation**: Processes and cleans data
   - Extracts summary content from JSON structure
   - Parses chapter Topics → Sub-topics → content
   - Filters out empty resources

3. **Chunking**: Splits content into manageable pieces
   - Summary: Single chunk per resource (chunk_index: 0)
   - Chapters: 250-word chunks from sub-topic content
   - Metadata: Preserves topic_title, subtopic_title

4. **Embedding** (`embedder.py`): Generates vector embeddings
   - Model: `text-embedding-004`
   - Batch processing with rate limiting
   - Vector size: 768 dimensions

5. **Storage**: Uploads to Qdrant with payload indexes
- Creates indexes on: `course_id`, `module_id`, `resource_id`
   - Enables efficient filtering and querying
   - Stores full text content in payload

### Chunk Structure
Each chunk in Qdrant contains:
```json
{
  "course_id": 329,
  "module_id": 575,
  "resource_id": 1564,
  "chunk_id": "329_575_1564_0",
  "chunk_type": "summary" | "chapter",
  "chunk_index": 0,
  "text": "actual content...",
  "topic_title": "...",      // chapter chunks only
  "subtopic_title": "..."    // chapter chunks only
}
```

## Usage

### Video Processing

#### 1. Full Pipeline (Complete Refresh)
Clears entire collection and reprocesses all data:
```bash
python video_main.py
```
- Extracts all data from PostgreSQL
- Deletes existing collection
- Creates new collection with indexes
- Uploads all embeddings

#### 2. Course-Level Update
Updates all resources in a specific course:
```bash
# Edit course_updater.py
COURSE_ID = 305

python Video/course_updater.py
```
- Deletes all vectors for the specified course
- Fetches fresh data from PostgreSQL
- Re-embeds and uploads only that course
- Preserves other courses

#### 3. Resource-Level Update (Surgical Update)
Updates a single resource:
```bash
# Edit resource_updater.py
COURSE_ID = 329
MODULE_ID = 575
RESOURCE_ID = 1564

python Video/resource_updater.py
```
- Deletes vectors for specific course+module+resource combination
- Fetches fresh data for that resource only
- Re-embeds and uploads
- Most efficient for single resource changes

### Material Processing

#### 1. Prepare Your Materials
1. Place your PDF files in the `Material/documents/` directory
2. Ensure each PDF filename follows the pattern: `{course_id}_material.pdf`

#### 2. Update a Specific Course
```bash
python Material/material_updater.py
```

#### 3. Update All Courses
```bash
python Material/main.py
```

## Testing & Utility Tools

### 1. Search Chunks (Semantic Search)
Interactive semantic search with optional filtering:
```bash
# Edit test_chunks.py
COURSE_ID = 329      # or None for all courses
MODULE_ID = 575      # or None for all modules
RESOURCE_ID = None   # or specific resource_id

python Video/test_chunks.py
```
- Enter queries interactively
- Returns top 5 semantically similar chunks
- Filters by specified course/module/resource
- Shows relevance scores

### 2. Find Chunks (Direct Lookup)
Find all chunks matching specific criteria:
```bash
# Edit find_chunks.py
COURSE_ID = 329
MODULE_ID = 575      # Set to None for all modules
RESOURCE_ID = 1564   # Set to None for all resources

python TEST/find_chunks.py
```
- Lists all matching chunks with full details
- Shows metadata and content preview
- Summarizes by type and resource
- Useful for verification

### 3. Delete Chunks
Delete specific resource chunks:
```bash
# Edit chunk_deleter.py
COURSE_ID = 329
MODULE_ID = 575
RESOURCE_ID = 1564

python TEST/chunk_deleter.py
```
- Counts chunks before deletion
- Requires `YES` confirmation
- Verifies deletion afterward
- Useful for testing updates

### 4. Create Indexes (One-Time Setup)
If indexes don't exist, create them manually:
```bash
python TEST/create_indexes.py
```
- Creates payload indexes for filtering
- Only needed if pipeline hasn't run yet
- Safe to run multiple times

## Project Structure
```
industry_pilot_RAG_pipeline/
├── Material/                    # Material processing
│   ├── embedder.py             # Material embedding logic
│   ├── material_updater.py     # Update specific materials
│   ├── pdf_converter.py        # PDF processing
│   ├── test_chunks.py          # Test material retrieval
│   └── documents/              # PDF storage directory
│
├── Video/                       # Video processing
│   ├── embedder.py             # Embedding + Qdrant operations
│   ├── extracter.py            # PostgreSQL data extraction
│   ├── course_updater.py       # Update specific course
│   ├── resource_updater.py     # Update specific resource
│   └── test_chunks.py          # Semantic search with filtering
│
├── TEST/                        # Testing utilities
│   ├── find_chunks.py          # Find chunks by ID
│   ├── chunk_deleter.py        # Delete chunks by ID
│   └── create_indexes.py       # Create payload indexes
│
├── video_main.py               # Full video pipeline
├── course_data.json            # Cached course data
├── requirements.txt            # Python dependencies
├── .env                        # Environment variables
└── Readme.md                   # This file
```

## Update Strategies

### When to Use Each Update Method

| Scenario | Method | Command |
|----------|--------|---------|
| Initial setup | Full pipeline | `python video_main.py` |
| New course added | Course update | Edit `COURSE_ID` → `python Video/course_updater.py` |
| Course content changed | Course update | Edit `COURSE_ID` → `python Video/course_updater.py` |
| Single resource changed | Resource update | Edit IDs → `python Video/resource_updater.py` |
| Video summary updated | Resource update | Edit IDs → `python Video/resource_updater.py` |
| Testing changes | Find + Delete | Use `find_chunks.py` + `chunk_deleter.py` |

### Workflow Example: Updating a Single Resource
```bash
# 1. Check current chunks
# Edit TEST/find_chunks.py: COURSE_ID=329, MODULE_ID=575, RESOURCE_ID=1564
python TEST/find_chunks.py

# 2. Delete if needed (optional)
# Edit TEST/chunk_deleter.py: COURSE_ID=329, MODULE_ID=575, RESOURCE_ID=1564
python TEST/chunk_deleter.py

# 3. Upload fresh data
# Edit Video/resource_updater.py: COURSE_ID=329, MODULE_ID=575, RESOURCE_ID=1564
python Video/resource_updater.py

# 4. Verify update
python TEST/find_chunks.py
```

## Best Practices

### Performance Tips
- **Incremental Updates**: Use course/resource updaters instead of full refresh when possible
- **Batch Processing**: Embeddings are processed in batches of 100 with rate limiting
- **Chunk Size**: 250-word chunks balance context and retrieval precision
- **Indexing**: Payload indexes ensure fast filtering - automatically created by updaters

### Data Management
- **Chunk IDs**: Follow pattern `{course_id}_{module_id}_{resource_id}_{chunk_index}`
- **Point IDs**: Auto-increment from max existing ID
- **Content Storage**: Full text stored in payload for retrieval
- **Metadata**: Preserves hierarchical structure (course → module → resource)

### Maintenance
- Monitor Qdrant collection sizes and performance
- Use `find_chunks.py` to audit data quality
- Test updates in staging before production
- Keep database credentials secure and rotate API keys periodically

### Troubleshooting

| Issue | Solution |
|-------|----------|
| "Index required" error | Run `create_indexes.py` or use any updater (auto-creates indexes) |
| No chunks found | Verify IDs in database, check collection name in `.env` |
| Embedding errors | Check `GOOGLE_API_KEY`, verify rate limits |
| Database connection fails | Verify PostgreSQL credentials in `.env` |
| Chunks not deleting | Ensure indexes exist, check ID values match exactly |

## API Rate Limits

### Google Generative AI
- Embeddings processed in batches of 100
- 1-second delay between batches
- Automatic retry on failures

### Qdrant Operations
- Batch uploads: 100 points per batch
- No rate limiting on queries
- Indexes improve query performance significantly

## Index Management

### Automatic Index Creation
All video processing scripts automatically create payload indexes:
- `embedder.py`: Creates during collection setup
- `course_updater.py`: Ensures indexes exist before operations
- `resource_updater.py`: Ensures indexes exist before operations
- `find_chunks.py`: Creates indexes if missing
- `chunk_deleter.py`: Creates indexes if missing

### Manual Index Creation
If needed, create indexes manually:
```bash
python TEST/create_indexes.py
```

Indexes are created for:
- `course_id` (INTEGER)
- `module_id` (INTEGER)
- `resource_id` (INTEGER)

## License

[Specify your license here]

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.