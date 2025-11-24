# RAG Pipeline for Course Content

A Retrieval-Augmented Generation (RAG) pipeline that processes both course materials and video content from a PostgreSQL database, generates embeddings using Google's Generative AI, and stores them in Qdrant for efficient semantic search.

## Features

### Material Processing
- **Data Extraction**: Pulls course material content from PostgreSQL database
- **Text Processing**: Chunks and processes text for optimal embedding generation
- **Vector Embeddings**: Uses Google's text-embedding-004 model to generate embeddings
- **Vector Database**: Stores and manages material embeddings in Qdrant for fast semantic search

### Video Processing
- **Video Content Extraction**: Processes video transcripts and metadata
- **Temporal Chunking**: Intelligently chunks video content while preserving context
- **Multimodal Support**: Handles both video metadata and transcript text
- **Dual Collections**: Maintains separate Qdrant collections for video and material content

### General
- **Incremental Updates**: Supports full database refresh or updating individual courses
- **Scalable Architecture**: Designed to handle large volumes of content efficiently

##  Prerequisites

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
   ```
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
   QDRANT_COLLECTION_NAME_VIDEO=qdrant_collection_name_video
   QDRANT_COLLECTION_NAME_MATERIAL=qdrant_collection_name_material
   
   # Google Generative AI
   GOOGLE_API_KEY=your_google_api_key
   ```

## Data Processing Pipeline

### Material Processing Flow
1. **Extraction**: Fetches course material data from PostgreSQL
2. **Transformation**: Processes JSON structures and normalizes data
3. **Chunking**: Splits content into manageable chunks (default: 250 words)
4. **Embedding**: Generates vector embeddings for each chunk
5. **Storage**: Uploads to the material collection in Qdrant

### Video Processing Flow
1. **Extraction**: Retrieves video metadata and transcripts
2. **Temporal Chunking**: Splits video content while maintaining temporal context
3. **Metadata Enrichment**: Combines transcript text with video metadata
4. **Embedding**: Generates vector embeddings for video chunks
5. **Storage**: Uploads to the video collection in Qdrant

## Usage

### Updating Course Materials

#### 1. Prepare Your Materials
1. Place your PDF files in the `Material/documents/` directory
2. Ensure each PDF filename follows the pattern: `{course_id}_material.pdf`

#### 2. Update a Specific Course
```bash
# Update materials for a specific course
python Material/material_updater.py
```

#### 3. Update All Courses
```bash
# Process all materials
python Material/main.py
```

### Updating Video Content

#### 1. Full Video Database Update
```bash
# Process all videos
python Video/embedder.py
```

#### 2. Extract Video Data Only
```bash
# Extract video metadata and transcripts
python Video/extracter.py
```

### Environment Configuration
- Set `QDRANT_COLLECTION_NAME_VIDEO` and `QDRANT_COLLECTION_NAME_MATERIAL` in `.env`
- Configure database connections and API keys in `.env`
- Adjust chunking parameters in respective configuration files

## Project Structure

### Core Components
- `Material/` - Directory containing material processing scripts
  - `main.py` - Main script for processing all materials
  - `material_updater.py` - Script for updating specific course materials
  - `documents/` - Directory to store PDF files for processing
- `requirements.txt` - Python dependencies

### Video Processing
- `Video/embedder.py` - Handles video content embedding and Qdrant operations
- `Video/extracter.py` - Extracts and processes video data from PostgreSQL
- `Video/test_chunks.py` - Utility for testing video chunk processing

### Data Files
- `course_data.json` - Cached course data (generated during processing)

## Testing the Pipeline

### Test Material Retrieval
```bash
python test_chunks.py
```

### Test Video Retrieval
```bash
python Video/test_chunks.py
```

These scripts start an interactive session where you can search for relevant content from both material and video sources.

## Best Practices

### Performance Tips
- **Batch Processing**: Process videos and materials in batches to optimize API usage
- **Chunk Size**: Adjust chunk sizes based on content type (smaller for dense content, larger for general text)
- **Error Handling**: The pipeline includes retry logic for API calls and database operations

### Maintenance
- Monitor Qdrant collection sizes and performance
- Regularly update the Google Generative AI client library for latest features
- Keep database credentials secure and rotate API keys periodically

### Troubleshooting
- Check logs for detailed error messages
- Verify database connections and API quotas
- Ensure all environment variables are correctly set in `.env`

##  License

[Specify your license here]

##  Contributing

Contributions are welcome! Please feel free to submit a Pull Request.