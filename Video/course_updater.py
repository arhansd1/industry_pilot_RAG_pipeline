import json
import os
import psycopg2
import psycopg2.extras
import google.generativeai as genai
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue, PointStruct
from dotenv import load_dotenv
import time

# Load environment variables
load_dotenv()

# Configure Google Generative AI
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# ============================================
# CONFIGURE COURSE ID HERE
# ============================================
COURSE_ID = 305  # Change this to update different course
# ============================================


def fetch_course_data(course_id):
    """
    Fetch data for a specific course from PostgreSQL.
    """
    print(f"\n📥 Fetching data for course_id: {course_id}...")
    
    conn = psycopg2.connect(
        host=os.getenv("POSTGRES_HOST"),
        port=int(os.getenv("POSTGRES_PORT")),
        database=os.getenv("POSTGRES_DB"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD")
    )

    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    query = f"""
        SELECT
            m.course_id AS course_id,
            r.module_id AS module_id,
            r.id AS resource_id,
            r.summary AS summary,
            r.chapters AS chapters
        FROM course.t_module m 
        JOIN course.t_resource r 
        ON m.id = r.module_id 
        WHERE m.course_id = {course_id}
    """

    cursor.execute(query)
    rows = cursor.fetchall()

    cursor.close()
    conn.close()
    
    print(f"✓ Fetched {len(rows)} resources for course {course_id}")
    
    return rows


def transform_course_data(rows):
    """
    Transform and clean course data.
    """
    print(f"\n🔄 Transforming data...")
    
    transformed = []

    for row in rows:
        new_row = dict(row)

        summary = new_row.get("summary")
        chapters = new_row.get("chapters")

        # Parse summary if it's a string
        if isinstance(summary, str):
            try:
                summary = json.loads(summary)
            except Exception:
                summary = None

        # Extract summary content
        if isinstance(summary, dict) and "content" in summary:
            new_row["summary"] = summary["content"]
        else:
            new_row["summary"] = None

        # Parse chapters if it's a string
        if isinstance(chapters, str):
            try:
                chapters = json.loads(chapters)
            except Exception:
                chapters = None

        new_row["chapters"] = chapters

        # Skip if both summary and chapters are null/empty
        if not new_row["summary"] and not new_row["chapters"]:
            continue

        transformed.append(new_row)

    print(f"✓ Transformed {len(transformed)} valid resources")
    return transformed


def delete_course_vectors(client, collection_name, course_id):
    """
    Delete all vectors related to a specific course_id from Qdrant.
    """
    print(f"\n🗑️  Deleting existing vectors for course_id: {course_id}...")
    
    try:
        # Delete points with matching course_id
        client.delete(
            collection_name=collection_name,
            points_selector=Filter(
                must=[
                    FieldCondition(
                        key="course_id",
                        match=MatchValue(value=course_id)
                    )
                ]
            )
        )
        print(f"✓ Deleted all vectors for course_id: {course_id}")
    except Exception as e:
        print(f"⚠️  Warning: Could not delete vectors: {e}")
        print("   Continuing with upload...")


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
            
            if i + batch_size < len(texts):
                time.sleep(1)
                
        except Exception as e:
            print(f"Error generating embeddings for batch {i}: {e}")
            embeddings.extend([None] * len(batch))
    
    return embeddings


def get_next_point_id(client, collection_name):
    """
    Get the next available point ID by finding the max existing ID.
    """
    try:
        # Scroll through all points to find max ID
        points, _ = client.scroll(
            collection_name=collection_name,
            limit=10000,  # Adjust if you have more points
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


def upload_course_data(course_data, course_id):
    """
    Process course data and upload to Qdrant.
    """
    print(f"\n📤 Uploading data for course_id: {course_id}...")
    
    # Initialize Qdrant client
    client = QdrantClient(
        url=os.getenv("QDRANT_URL"),
        api_key=os.getenv("QDRANT_API_KEY")
    )
    
    collection_name = os.getenv("QDRANT_COLLECTION_NAME_VIDEO")
    
    # Get next available point ID
    point_id = get_next_point_id(client, collection_name)
    print(f"✓ Starting from point ID: {point_id}")
    
    # Process each resource
    all_points = []
    
    for resource in course_data:
        course_id_val = resource.get("course_id")
        module_id = resource.get("module_id")
        resource_id = resource.get("resource_id")
        summary = resource.get("summary")
        chapters = resource.get("chapters")
        
        print(f"\n  Processing resource {resource_id} (module: {module_id})")
        
        chunks_to_embed = []
        chunk_metadata = []
        
        # Process summary chunk
        if summary:
            chunks_to_embed.append(summary)
            chunk_metadata.append({
                "course_id": course_id_val,
                "module_id": module_id,
                "resource_id": resource_id,
                "chunk_id": f"{course_id_val}_{module_id}_{resource_id}_0",
                "chunk_type": "summary",
                "chunk_index": 0,
                "text": summary
            })
            print(f"    + Summary chunk")
        
        # Process chapter chunks
        if chapters:
            chapter_chunks = process_chapters(chapters)
            
            for idx, chunk_data in enumerate(chapter_chunks, start=1):
                chunks_to_embed.append(chunk_data["text"])
                chunk_metadata.append({
                    "course_id": course_id_val,
                    "module_id": module_id,
                    "resource_id": resource_id,
                    "chunk_id": f"{course_id_val}_{module_id}_{resource_id}_{idx}",
                    "chunk_type": "chapter",
                    "chunk_index": idx,
                    "topic_title": chunk_data["topic_title"],
                    "subtopic_title": chunk_data["subtopic_title"],
                    "text": chunk_data["text"]
                })
            
            print(f"    + {len(chapter_chunks)} chapter chunks")
        
        # Generate embeddings
        if chunks_to_embed:
            print(f"    Generating {len(chunks_to_embed)} embeddings...")
            embeddings = create_embeddings(chunks_to_embed)
            
            # Create points
            for embedding, metadata in zip(embeddings, chunk_metadata):
                if embedding is not None:
                    all_points.append(
                        PointStruct(
                            id=point_id,
                            vector=embedding,
                            payload=metadata
                        )
                    )
                    point_id += 1
    
    # Upload to Qdrant
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
        
        print(f"\n✓ Successfully uploaded {len(all_points)} vectors!")
    else:
        print("\n⚠️  No vectors to upload!")


def main():
    """
    Main function to update a specific course in Qdrant.
    """
    print("=" * 70)
    print("COURSE UPDATER - Incremental Qdrant Update")
    print("=" * 70)
    print(f"\n🎯 Target Course ID: {COURSE_ID}")
    
    # Initialize Qdrant client
    client = QdrantClient(
        url=os.getenv("QDRANT_URL"),
        api_key=os.getenv("QDRANT_API_KEY")
    )
    collection_name = os.getenv("QDRANT_COLLECTION_NAME_VIDEO")
    
    # Step 1: Delete existing course vectors
    delete_course_vectors(client, collection_name, COURSE_ID)
    
    # Step 2: Fetch fresh data from PostgreSQL
    rows = fetch_course_data(COURSE_ID)
    
    if not rows:
        print(f"\n⚠️  No data found for course_id: {COURSE_ID}")
        print("Exiting...")
        return
    
    # Step 3: Transform data
    course_data = transform_course_data(rows)
    
    if not course_data:
        print(f"\n⚠️  No valid data to upload for course_id: {COURSE_ID}")
        print("Exiting...")
        return
    
    # Step 4: Upload to Qdrant
    upload_course_data(course_data, COURSE_ID)
    
    # Summary
    print("\n" + "=" * 70)
    print(f"✅ COURSE UPDATE COMPLETED FOR COURSE_ID: {COURSE_ID}")
    print("=" * 70)
    
    # Show collection stats
    collection_info = client.get_collection(collection_name)
    print(f"\nCollection Info:")
    print(f"  Total vectors: {collection_info.points_count}")


if __name__ == "__main__":
    main()