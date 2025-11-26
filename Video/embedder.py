import json
import os
import google.generativeai as genai
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, PayloadSchemaType
from dotenv import load_dotenv
import time

# Load environment variables
load_dotenv()

# Configure Google Generative AI
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))


def chunk_text_by_words(text, max_words=250):
    """
    Split text into chunks of approximately max_words.
    """
    if not text or not isinstance(text, str):
        return []
    
    words = text.split()
    chunks = []
    
    for i in range(0, len(words), max_words):
        chunk = " ".join(words[i:i + max_words])
        chunks.append(chunk)
    
    return chunks


def process_chapters(chapters_data):
    """
    Extract sub-topic content from chapters and split into 250-word chunks.
    Returns list of dicts with chunk text and metadata.
    """
    chunks = []
    
    if not chapters_data or not isinstance(chapters_data, dict):
        return chunks
    
    topics = chapters_data.get("Topics", [])
    
    for topic in topics:
        topic_title = topic.get("title", "")
        sub_topics = topic.get("Sub-topics", [])
        
        for sub_topic in sub_topics:
            subtopic_title = sub_topic.get("title", "")
            content = sub_topic.get("content", "")
            
            if content:
                # Split content into 250-word chunks
                text_chunks = chunk_text_by_words(content, max_words=250)
                
                for chunk_text in text_chunks:
                    chunks.append({
                        "text": chunk_text,
                        "topic_title": topic_title,
                        "subtopic_title": subtopic_title
                    })
    
    return chunks


def create_embeddings(texts, batch_size=100):
    """
    Generate embeddings using Google's text-embedding-004 model.
    Processes in batches to avoid rate limits.
    """
    embeddings = []
    
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        
        try:
            result = genai.embed_content(
                model="models/text-embedding-004",
                content=batch,
                task_type="retrieval_document"
            )
            embeddings.extend(result['embedding'])
            
            # Rate limiting
            if i + batch_size < len(texts):
                time.sleep(1)
                
        except Exception as e:
            print(f"Error generating embeddings for batch {i}: {e}")
            # Return None for failed embeddings
            embeddings.extend([None] * len(batch))
    
    return embeddings


def setup_qdrant_collection(client, collection_name, vector_size=768):
    """
    Create or recreate Qdrant collection with payload indexes.
    """
    try:
        # Delete if exists
        client.delete_collection(collection_name)
        print(f"✓ Deleted existing collection: {collection_name}")
    except:
        pass
    
    # Create new collection
    client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE)
    )
    print(f"✓ Created collection: {collection_name}")
    
    # Create indexes for filtering
    print(f"✓ Creating payload indexes...")
    client.create_payload_index(
        collection_name=collection_name,
        field_name="course_id",
        field_schema=PayloadSchemaType.INTEGER
    )
    client.create_payload_index(
        collection_name=collection_name,
        field_name="module_id",
        field_schema=PayloadSchemaType.INTEGER
    )
    client.create_payload_index(
        collection_name=collection_name,
        field_name="resource_id",
        field_schema=PayloadSchemaType.INTEGER
    )
    print(f"✓ Created indexes for course_id, module_id, resource_id")


def process_and_upload_data(data_file="course_data.json"):
    """
    Main function to process course data and upload to Qdrant.
    """
    # Load data
    print("Loading course data...")
    with open(data_file, "r", encoding="utf-8") as f:
        course_data = json.load(f)
    print(f"✓ Loaded {len(course_data)} resources")
    
    # Initialize Qdrant client
    print("\nConnecting to Qdrant...")
    client = QdrantClient(
        url=os.getenv("QDRANT_URL"),
        api_key=os.getenv("QDRANT_API_KEY")
    )
    print("✓ Connected to Qdrant")
    
    collection_name = os.getenv("QDRANT_COLLECTION_NAME_VIDEO")
    
    # Setup collection
    print(f"\nSetting up collection: {collection_name}")
    setup_qdrant_collection(client, collection_name)
    
    # Process each resource
    all_points = []
    point_id = 0
    
    print("\nProcessing resources...")
    for resource in course_data:
        course_id = resource.get("course_id")
        module_id = resource.get("module_id")
        resource_id = resource.get("resource_id")
        summary = resource.get("summary")
        chapters = resource.get("chapters")
        
        print(f"\nProcessing resource {resource_id} (course: {course_id}, module: {module_id})")
        
        chunks_to_embed = []
        chunk_metadata = []
        
        # Process summary chunk
        if summary:
            chunks_to_embed.append(summary)
            chunk_metadata.append({
                "course_id": course_id,
                "module_id": module_id,
                "resource_id": resource_id,
                "chunk_id": f"{course_id}_{module_id}_{resource_id}_0",
                "chunk_type": "summary",
                "chunk_index": 0,
                "text": summary  # Store the actual text content
            })
            print(f"  + Added summary chunk")
        
        # Process chapter chunks
        if chapters:
            chapter_chunks = process_chapters(chapters)
            
            for idx, chunk_data in enumerate(chapter_chunks, start=1):
                chunks_to_embed.append(chunk_data["text"])
                chunk_metadata.append({
                    "course_id": course_id,
                    "module_id": module_id,
                    "resource_id": resource_id,
                    "chunk_id": f"{course_id}_{module_id}_{resource_id}_{idx}",
                    "chunk_type": "chapter",
                    "chunk_index": idx,
                    "topic_title": chunk_data["topic_title"],
                    "subtopic_title": chunk_data["subtopic_title"],
                    "text": chunk_data["text"]  # Store the actual text content
                })
            
            print(f"  + Added {len(chapter_chunks)} chapter chunks")
        
        # Generate embeddings for this resource
        if chunks_to_embed:
            print(f"  Generating embeddings for {len(chunks_to_embed)} chunks...")
            embeddings = create_embeddings(chunks_to_embed)
            
            # Create points
            for idx, (embedding, metadata) in enumerate(zip(embeddings, chunk_metadata)):
                if embedding is not None:
                    all_points.append(
                        PointStruct(
                            id=point_id,
                            vector=embedding,
                            payload=metadata
                        )
                    )
                    point_id += 1
            
            print(f"  ✓ Created {len(embeddings)} embeddings")
    
    # Upload to Qdrant in batches
    print(f"\nUploading {len(all_points)} points to Qdrant...")
    batch_size = 100
    
    for i in range(0, len(all_points), batch_size):
        batch = all_points[i:i + batch_size]
        client.upsert(
            collection_name=collection_name,
            points=batch
        )
        print(f"  Uploaded batch {i // batch_size + 1}/{(len(all_points) + batch_size - 1) // batch_size}")
    
    print(f"\n✓ Successfully uploaded {len(all_points)} vectors to Qdrant!")
    
    # Print collection info
    collection_info = client.get_collection(collection_name)
    print(f"\nCollection Info:")
    print(f"  Total vectors: {collection_info.points_count}")
    print(f"  Vector size: {collection_info.config.params.vectors.size}")


if __name__ == "__main__":
    process_and_upload_data()