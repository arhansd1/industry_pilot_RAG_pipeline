import json
import os
import psycopg2
import psycopg2.extras
import google.generativeai as genai
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue, PointStruct, PayloadSchemaType
from dotenv import load_dotenv
import time

# Load environment variables
load_dotenv()

# Configure Google Generative AI
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# ============================================
# CONFIGURE RESOURCE DETAILS HERE
# ============================================
COURSE_ID = 329
MODULE_ID = 575  # Set to None to get all modules in course
RESOURCE_ID = 1564  # Set to None to get all resources in module
# ============================================


def fetch_resource_data(course_id, module_id, resource_id):
    """
    Fetch data for a specific resource from PostgreSQL.
    """
    print(f"\n📥 Fetching data for:")
    print(f"   Course ID   : {course_id}")
    print(f"   Module ID   : {module_id}")
    print(f"   Resource ID : {resource_id}")
    
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
        AND r.module_id = {module_id}
        AND r.id = {resource_id}
    """

    cursor.execute(query)
    row = cursor.fetchone()

    cursor.close()
    conn.close()
    
    if row:
        print(f"✓ Successfully fetched resource data")
    else:
        print(f"✗ No data found for the specified resource")
    
    return row


def transform_resource_data(row):
    """
    Transform and clean resource data.
    """
    if not row:
        return None
    
    print(f"\n🔄 Transforming data...")
    
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

    # Check if both summary and chapters are null/empty
    if not new_row["summary"] and not new_row["chapters"]:
        print(f"⚠️  Warning: Resource has no valid summary or chapters")
        return None

    print(f"✓ Transformation complete")
    return new_row


def ensure_indexes_exist(client, collection_name):
    """
    Ensure payload indexes exist for course_id, module_id, resource_id.
    """
    print(f"\n🔍 Ensuring indexes exist...")
    
    fields_to_index = [
        ("course_id", PayloadSchemaType.INTEGER),
        ("module_id", PayloadSchemaType.INTEGER),
        ("resource_id", PayloadSchemaType.INTEGER)
    ]
    
    for field_name, field_type in fields_to_index:
        try:
            client.create_payload_index(
                collection_name=collection_name,
                field_name=field_name,
                field_schema=field_type
            )
            print(f"  ✓ Created index for {field_name}")
        except Exception:
            # Index already exists
            print(f"  ℹ️  Index for {field_name} already exists")


def delete_resource_vectors(client, collection_name, course_id, module_id, resource_id):
    """
    Delete all vectors related to a specific resource from Qdrant.
    Uses the unique combination of course_id, module_id, and resource_id.
    """
    print(f"\n🗑️  Deleting existing vectors for:")
    print(f"   Course ID   : {course_id}")
    print(f"   Module ID   : {module_id}")
    print(f"   Resource ID : {resource_id}")
    
    try:
        # Count points before deletion
        count_result = client.count(
            collection_name=collection_name,
            count_filter=Filter(
                must=[
                    FieldCondition(key="course_id", match=MatchValue(value=course_id)),
                    FieldCondition(key="module_id", match=MatchValue(value=module_id)),
                    FieldCondition(key="resource_id", match=MatchValue(value=resource_id))
                ]
            )
        )
        
        points_count = count_result.count
        print(f"   Found {points_count} existing chunks to delete")
        
        if points_count == 0:
            print(f"   No existing vectors found for this resource")
            return
        
        # Delete points with matching course_id, module_id, and resource_id
        client.delete(
            collection_name=collection_name,
            points_selector=Filter(
                must=[
                    FieldCondition(key="course_id", match=MatchValue(value=course_id)),
                    FieldCondition(key="module_id", match=MatchValue(value=module_id)),
                    FieldCondition(key="resource_id", match=MatchValue(value=resource_id))
                ]
            )
        )
        print(f"✓ Successfully deleted {points_count} vectors")
        
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


def upload_resource_data(resource_data, client, collection_name):
    """
    Process resource data and upload to Qdrant.
    """
    if not resource_data:
        print("\n⚠️  No data to upload")
        return
    
    course_id = resource_data.get("course_id")
    module_id = resource_data.get("module_id")
    resource_id = resource_data.get("resource_id")
    summary = resource_data.get("summary")
    chapters = resource_data.get("chapters")
    
    print(f"\n📤 Processing resource data...")
    
    # Get next available point ID
    point_id = get_next_point_id(client, collection_name)
    print(f"✓ Starting from point ID: {point_id}")
    
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
            "text": summary
        })
        print(f"  + Summary chunk")
    
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
                "text": chunk_data["text"]
            })
        
        print(f"  + {len(chapter_chunks)} chapter chunks")
    
    # Generate embeddings
    if not chunks_to_embed:
        print("\n⚠️  No chunks to embed!")
        return
    
    print(f"\n  Generating {len(chunks_to_embed)} embeddings...")
    embeddings = create_embeddings(chunks_to_embed)
    
    # Create points
    all_points = []
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
    Main function to update a specific resource in Qdrant.
    """
    print("=" * 70)
    print("RESOURCE UPDATER - Incremental Qdrant Update")
    print("=" * 70)
    print(f"\n🎯 Target Resource:")
    print(f"   Course ID   : {COURSE_ID}")
    print(f"   Module ID   : {MODULE_ID}")
    print(f"   Resource ID : {RESOURCE_ID}")
    
    # Initialize Qdrant client
    client = QdrantClient(
        url=os.getenv("QDRANT_URL"),
        api_key=os.getenv("QDRANT_API_KEY")
    )
    collection_name = os.getenv("QDRANT_COLLECTION_NAME_VIDEO")
    
    # Ensure indexes exist
    ensure_indexes_exist(client, collection_name)
    
    # Step 1: Delete existing resource vectors
    delete_resource_vectors(client, collection_name, COURSE_ID, MODULE_ID, RESOURCE_ID)
    
    # Step 2: Fetch fresh data from PostgreSQL
    row = fetch_resource_data(COURSE_ID, MODULE_ID, RESOURCE_ID)
    
    if not row:
        print(f"\n⚠️  No data found for the specified resource")
        print("Exiting...")
        return
    
    # Step 3: Transform data
    resource_data = transform_resource_data(row)
    
    if not resource_data:
        print(f"\n⚠️  No valid data to upload for the specified resource")
        print("Exiting...")
        return
    
    # Step 4: Upload to Qdrant
    upload_resource_data(resource_data, client, collection_name)
    
    # Summary
    print("\n" + "=" * 70)
    print(f"✅ RESOURCE UPDATE COMPLETED")
    print("=" * 70)
    print(f"\nUpdated Resource:")
    print(f"   Course ID   : {COURSE_ID}")
    print(f"   Module ID   : {MODULE_ID}")
    print(f"   Resource ID : {RESOURCE_ID}")
    
    # Show collection stats
    collection_info = client.get_collection(collection_name)
    print(f"\nCollection Info:")
    print(f"  Total vectors: {collection_info.points_count}")


if __name__ == "__main__":
    main()