# RAG Pipeline for Course Content

A Retrieval-Augmented Generation (RAG) pipeline that processes course content from a PostgreSQL database, generates embeddings using Google's Generative AI, and stores them in Qdrant for efficient semantic search.

##  Features

- **Data Extraction**: Pulls course content from PostgreSQL database
- **Text Processing**: Chunks and processes text for optimal embedding generation
- **Vector Embeddings**: Uses Google's text-embedding-004 model to generate embeddings
- **Vector Database**: Stores and manages embeddings in Qdrant for fast similarity search
- **Incremental Updates**: Supports full database refresh or updating individual courses

##  Prerequisites

- Python 3.8+
- PostgreSQL database with course content
- Qdrant vector database
- Google Generative AI API key
- Required Python packages (see `requirements.txt`)

##  Setup

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
   QDRANT_COLLECTION_NAME= qdrant_collection_name

   
   # Google Generative AI
   GOOGLE_API_KEY=your_google_api_key
   ```

##  Usage

### 1. Full Database Update

To process all courses and update the entire vector database:

```bash
python main.py
```

This will:
1. Extract all course data from PostgreSQL
2. Process and chunk the content
3. Generate embeddings using Google's Generative AI
4. Upload to Qdrant vector database

### 2. Update a Specific Course

To update a single course in the vector database:

1. Open `course_updater.py` and set the `COURSE_ID` variable at the top of the file
2. Run:
   ```bash
   python course_updater.py
   ```

This will:
1. Fetch only the specified course from PostgreSQL
2. Delete existing vectors for this course in Qdrant
3. Process and re-embed the course content
4. Upload the new vectors to Qdrant

##  Project Structure

- `main.py` - Main script for full database updates
- `course_updater.py` - Script for updating individual courses
- `extracter.py` - Handles data extraction from PostgreSQL
- `embedder.py` - Manages embedding generation and Qdrant operations
- `test_chunks.py` - Utility for testing chunk retrieval (not covered in this README)

##  Testing the Pipeline

You can test the retrieval functionality using the included test script:

```bash
python test_chunks.py
```

This will start an interactive session where you can search for relevant course content.

## Notes

- Ensure your PostgreSQL database is properly configured and accessible
- Be mindful of API rate limits when generating embeddings
- The pipeline is designed to handle large volumes of text by chunking content
- Course updates are atomic - either the entire course updates successfully or not at all

##  License

[Specify your license here]

##  Contributing

Contributions are welcome! Please feel free to submit a Pull Request.