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


def fetch_data(course_id, module_id=None, resource_id=None):
    """
    Fetch data from PostgreSQL based on specified scope.
    
    Scope Logic:
    - course_id only: All resources in that course
    - course_id + module_id: All resources in that module
    - course_id + module_id + resource_id: Single resource
    """
    print(f"\n📥 Fetching data for:")
    print(f"   Course ID   : {course_id}")
    print(f"   Module ID   : {module_id if module_id is not None else 'ALL'}")
    print(f"   Resource ID : {resource_id if resource_id is not None else 'ALL'}")
    
    conn = psycopg2.connect(
        host=os.getenv("POSTGRES_HOST"),
        port=int(os.getenv("POSTGRES_PORT")),
        database=os.getenv("POSTGRES_DB"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD")
    )

    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # Build query based on provided parameters
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
    
    if module_id is not None:
        query += f" AND r.module_id = {module_id}"
    
    if resource_id is not None:
        query += f" AND r.id = {resource_id}"

    cursor.execute(query)
    rows = cursor.fetchall()

    cursor.close()
    conn.close()
    
    if rows:
        print(f"✓ Successfully fetched {len(rows)} resource(s)")
    else:
        print(f"✗ No data found for the specified criteria")
    
    return rows


def transform_data(rows):
    """
    Transform and clean data.
    """
    if not rows:
        return []
    
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

    print(f"✓ Transformed {len(transformed)} valid resource(s)")
    return transformed


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


def delete_vectors(client, collection_name, course_id, module_id=None, resource_id=None):
    """
    Delete vectors based on specified scope.
    
    Scope Logic:
    - course_id only: Delete all vectors for that course
    - course_id + module_id: Delete all vectors for that module
    - course_id + module_id + resource_id: Delete vectors for that resource
    """
    print(f"\n🗑️  Deleting existing vectors for:")
    print(f"   Course ID   : {course_id}")
    print(f"   Module ID   : {module_id if module_id is not None else 'ALL'}")
    print(f"   Resource ID : {resource_id if resource_id is not None else 'ALL'}")
    
    try:
        # Build filter conditions
        filter_conditions = [
            FieldCondition(key="course_id", match=MatchValue(value=course_id))
        ]
        
        if module_id is not None:
            filter_conditions.append(
                FieldCondition(key="module_id", match=MatchValue(value=module_id))
            )
        
        if resource_id is not None:
            filter_conditions.append(
                FieldCondition(key="resource_id", match=MatchValue(value=resource_id))
            )
        
        delete_filter = Filter(must=filter_conditions)
        
        # Count points before deletion
        count_result = client.count(
            collection_name=collection_name,
            count_filter=delete_filter
        )
        
        points_count = count_result.count
        print(f"   Found {points_count} existing chunks to delete")
        
        if points_count == 0:
            print(f"   No existing vectors found for this scope")
            return
        
        # Delete points
        client.delete(
            collection_name=collection_name,
            points_selector=delete_filter
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


def upload_data(data, client, collection_name):
    """
    Process data and upload to Qdrant.
    """
    if not data:
        print("\n⚠️  No data to upload")
        return
    
    print(f"\n📤 Uploading data...")
    
    # Get next available point ID
    point_id = get_next_point_id(client, collection_name)
    print(f"✓ Starting from point ID: {point_id}")
    
    # Process each resource
    all_points = []
    
    for resource in data:
        course_id = resource.get("course_id")
        module_id = resource.get("module_id")
        resource_id = resource.get("resource_id")
        summary = resource.get("summary")
        chapters = resource.get("chapters")
        
        print(f"\n  Processing resource {resource_id} (course: {course_id}, module: {module_id})")
        
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
            print(f"    + Summary chunk")
        
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


def update_resource(course_id, module_id=None, resource_id=None):
    """
    Main function to update Qdrant based on specified scope.
    
    Args:
        course_id (int): Required - Course ID to update
        module_id (int, optional): Module ID to update. None = all modules in course
        resource_id (int, optional): Resource ID to update. None = all resources in module/course
    
    Returns:
        dict: Summary of the update operation
    
    Example Usage:
        # Update entire course
        update_resource(course_id=329)
        
        # Update all resources in a module
        update_resource(course_id=329, module_id=575)
        
        # Update specific resource
        update_resource(course_id=329, module_id=575, resource_id=1564)
    """
    print("=" * 70)
    print("RESOURCE UPDATER - Flexible Incremental Update")
    print("=" * 70)
    
    # Validate COURSE_ID
    if course_id is None:
        raise ValueError("course_id is required!")
    
    # Display update scope
    print(f"\n🎯 Update Scope:")
    print(f"   Course ID   : {course_id}")
    print(f"   Module ID   : {module_id if module_id is not None else 'ALL'}")
    print(f"   Resource ID : {resource_id if resource_id is not None else 'ALL'}")
    
    # Determine scope description
    if module_id is None and resource_id is None:
        scope = f"entire course {course_id}"
    elif resource_id is None:
        scope = f"all resources in module {module_id}"
    else:
        scope = f"resource {resource_id}"
    
    print(f"\n📋 This will update: {scope}")
    
    try:
        # Step 1: Fetch data from PostgreSQL FIRST
        rows = fetch_data(course_id, module_id, resource_id)
        
        if not rows:
            print(f"\n⚠️  No data found in PostgreSQL for the specified criteria")
            print(f"❌ Process stopped - cannot proceed without data")
            return {
                "success": False,
                "message": "No data found in PostgreSQL",
                "reason": "PostgreSQL query returned no results",
                "course_id": course_id,
                "module_id": module_id,
                "resource_id": resource_id
            }
        
        # Step 2: Transform data
        transformed_data = transform_data(rows)
        
        if not transformed_data:
            print(f"\n⚠️  No valid data after transformation")
            print(f"❌ Process stopped - all fetched data is invalid or empty")
            return {
                "success": False,
                "message": "No valid data after transformation",
                "reason": "All resources have empty summary and chapters",
                "course_id": course_id,
                "module_id": module_id,
                "resource_id": resource_id
            }
        
        print(f"\n✓ Data validation passed - proceeding with update")
        
        # Initialize Qdrant client
        client = QdrantClient(
            url=os.getenv("QDRANT_URL"),
            api_key=os.getenv("QDRANT_API_KEY")
        )
        collection_name = os.getenv("QDRANT_COLLECTION_NAME_VIDEO")
        
        # Step 3: Ensure indexes exist
        ensure_indexes_exist(client, collection_name)
        
        # Step 4: Delete existing vectors (now safe since we have valid data)
        delete_vectors(client, collection_name, course_id, module_id, resource_id)
        
        # Step 5: Upload to Qdrant
        upload_data(transformed_data, client, collection_name)
        
        # Get collection info
        collection_info = client.get_collection(collection_name)
        
        # Summary
        print("\n" + "=" * 70)
        print(f"✅ UPDATE COMPLETED")
        print("=" * 70)
        print(f"\nUpdated Scope:")
        print(f"   Course ID   : {course_id}")
        print(f"   Module ID   : {module_id if module_id is not None else 'ALL'}")
        print(f"   Resource ID : {resource_id if resource_id is not None else 'ALL'}")
        print(f"   Description : {scope}")
        print(f"\nCollection Info:")
        print(f"  Total vectors: {collection_info.points_count}")
        
        return {
            "success": True,
            "message": f"Successfully updated {scope}",
            "course_id": course_id,
            "module_id": module_id,
            "resource_id": resource_id,
            "resources_processed": len(transformed_data),
            "total_vectors": collection_info.points_count
        }
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "message": str(e),
            "reason": "Exception occurred during execution",
            "course_id": course_id,
            "module_id": module_id,
            "resource_id": resource_id
        }


# For backwards compatibility - can still run as standalone script
if __name__ == "__main__":
    # Configure these when running as standalone script
    COURSE_ID = 329          # Required: Must specify course_id
    MODULE_ID = 575          # Optional: None = all modules in course
    RESOURCE_ID = 1564       # Optional: None = all resources in module
    
    result = update_resource(COURSE_ID, MODULE_ID, RESOURCE_ID)
    
    if result["success"]:
        print("\n✅ Script completed successfully!")
    else:
        print(f"\n❌ Script failed: {result['message']}")