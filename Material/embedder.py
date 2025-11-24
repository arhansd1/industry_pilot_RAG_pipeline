import os
import google.generativeai as genai
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct
from dotenv import load_dotenv
import time

# Load environment variables
load_dotenv()

# Configure Google Generative AI
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))


def create_embeddings(texts, batch_size=100):
    """
    Generate embeddings using Google's text-embedding-004 model.
    """
    embeddings = []
    
    print(f"\n🔮 Generating embeddings for {len(texts)} chunks...")
    
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        
        try:
            result = genai.embed_content(
                model="models/text-embedding-004",
                content=batch,
                task_type="retrieval_document"
            )
            embeddings.extend(result['embedding'])
            
            print(f"  ✓ Batch {i // batch_size + 1}/{(len(texts) + batch_size - 1) // batch_size}")
            
            if i + batch_size < len(texts):
                time.sleep(1)  # Rate limiting
                
        except Exception as e:
            print(f"Error generating embeddings for batch {i}: {e}")
            embeddings.extend([None] * len(batch))
    
    print(f"✅ Generated {len(embeddings)} embeddings")
    return embeddings


def get_next_point_id(client, collection_name):
    """
    Get the next available point ID by finding the max existing ID.
    """
    try:
        points, _ = client.scroll(
            collection_name=collection_name,
            limit=10000,
            with_payload=False,
            with_vectors=False
        )
        
        if points:
            max_id = max(point.id for point in points)
            return max_id + 1
        else:
            return 0
            
    except Exception as e:
        print(f"⚠️  Could not determine next point ID: {e}")
        print("   Starting from ID 0")
        return 0


def upload_chunks_to_qdrant(chunks):
    """
    Generate embeddings for chunks and upload to Qdrant.
    
    Args:
        chunks: List of chunk dictionaries with metadata and text
    """
    print(f"\n📤 Uploading {len(chunks)} chunks to Qdrant...")
    
    # Initialize Qdrant client
    client = QdrantClient(
        url=os.getenv("QDRANT_URL"),
        api_key=os.getenv("QDRANT_API_KEY")
    )
    
    collection_name = os.getenv("QDRANT_COLLECTION_NAME_MATERIAL")
    
    # Get next available point ID
    point_id = get_next_point_id(client, collection_name)
    print(f"✓ Starting from point ID: {point_id}")
    
    # Extract texts for embedding
    texts = [chunk["text"] for chunk in chunks]
    
    # Generate embeddings
    embeddings = create_embeddings(texts)
    
    # Create points
    all_points = []
    
    for chunk, embedding in zip(chunks, embeddings):
        if embedding is not None:
            all_points.append(
                PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload={
                        "course_id": chunk["course_id"],
                        "book_name": chunk["book_name"],
                        "page": chunk["page"],
                        "chunk_id": chunk["chunk_id"],
                        "text": chunk["text"]
                    }
                )
            )
            point_id += 1
    
    # Upload to Qdrant in batches
    if all_points:
        print(f"\n📦 Uploading {len(all_points)} vectors to Qdrant...")
        batch_size = 100
        
        for i in range(0, len(all_points), batch_size):
            batch = all_points[i:i + batch_size]
            client.upsert(
                collection_name=collection_name,
                points=batch
            )
            print(f"  ✓ Batch {i // batch_size + 1}/{(len(all_points) + batch_size - 1) // batch_size}")
        
        print(f"\n✅ Successfully uploaded {len(all_points)} vectors!")
    else:
        print("\n⚠️  No vectors to upload!")