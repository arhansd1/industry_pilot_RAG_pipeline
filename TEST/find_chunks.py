import os
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue, PayloadSchemaType
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ============================================
# CONFIGURE SEARCH CRITERIA HERE
# ============================================
COURSE_ID = 322
MODULE_ID = 556  # Set to None to get all modules in course
RESOURCE_ID = None  # Set to None to get all resources in module
# ============================================


def ensure_indexes_exist(client, collection_name):
    """
    Ensure payload indexes exist for course_id, module_id, resource_id.
    """
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
        except Exception:
            # Index already exists, skip silently
            pass


def find_chunks(course_id, module_id=None, resource_id=None):
    """
    Find all chunks matching the specified criteria.
    
    Logic:
    - If module_id and resource_id are None: Get all chunks for course_id
    - If resource_id is None: Get all chunks for course_id + module_id
    - Otherwise: Get all chunks for course_id + module_id + resource_id
    """
    
    # Initialize Qdrant client
    client = QdrantClient(
        url=os.getenv("QDRANT_URL"),
        api_key=os.getenv("QDRANT_API_KEY")
    )
    
    collection_name = os.getenv("QDRANT_COLLECTION_NAME_VIDEO")
    
    # Ensure indexes exist before querying
    ensure_indexes_exist(client, collection_name)
    
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
    
    # Create filter
    search_filter = Filter(must=filter_conditions)
    
    # Count matching points
    count_result = client.count(
        collection_name=collection_name,
        count_filter=search_filter
    )
    
    total_count = count_result.count
    
    if total_count == 0:
        return []
    
    # Scroll through all matching points
    all_points = []
    offset = None
    
    while True:
        result = client.scroll(
            collection_name=collection_name,
            scroll_filter=search_filter,
            limit=100,
            offset=offset,
            with_payload=True,
            with_vectors=False
        )
        
        points, next_offset = result
        all_points.extend(points)
        
        if next_offset is None:
            break
        
        offset = next_offset
    
    return all_points


def display_chunks(chunks, course_id, module_id, resource_id):
    """
    Display chunks in a well-formatted, detailed manner.
    """
    if not chunks:
        print("\n" + "=" * 80)
        print("NO CHUNKS FOUND")
        print("=" * 80)
        return
    
    # Display header
    print("\n" + "=" * 80)
    print("CHUNK FINDER RESULTS")
    print("=" * 80)
    
    # Display search criteria
    print(f"\n🔍 Search Criteria:")
    print(f"   Course ID   : {course_id}")
    print(f"   Module ID   : {module_id if module_id is not None else 'ALL'}")
    print(f"   Resource ID : {resource_id if resource_id is not None else 'ALL'}")
    print(f"\n📊 Total Chunks Found: {len(chunks)}")
    
    # Sort chunks by course_id, module_id, resource_id, chunk_index
    sorted_chunks = sorted(
        chunks,
        key=lambda x: (
            x.payload.get("course_id", 0),
            x.payload.get("module_id", 0),
            x.payload.get("resource_id", 0),
            x.payload.get("chunk_index", 0)
        )
    )
    
    # Display each chunk
    for idx, point in enumerate(sorted_chunks, 1):
        payload = point.payload
        
        print("\n" + "=" * 80)
        print(f"CHUNK #{idx}")
        print("=" * 80)
        
        print(f"\n📍 Point ID: {point.id}")
        
        print(f"\n📌 Metadata:")
        print(f"   Course ID     : {payload.get('course_id')}")
        print(f"   Module ID     : {payload.get('module_id')}")
        print(f"   Resource ID   : {payload.get('resource_id')}")
        print(f"   Chunk ID      : {payload.get('chunk_id')}")
        print(f"   Chunk Type    : {payload.get('chunk_type')}")
        print(f"   Chunk Index   : {payload.get('chunk_index')}")
        
        if payload.get('chunk_type') == 'chapter':
            topic = payload.get('topic_title', 'N/A')
            subtopic = payload.get('subtopic_title', 'N/A')
            print(f"   Topic         : {topic}")
            print(f"   Subtopic      : {subtopic}")
        
        content = payload.get('text', 'No content available')
        print(f"\n📄 Content:")
        print(f"   {content[:500]}{'...' if len(content) > 500 else ''}")
        
        if idx < len(sorted_chunks):
            print()
    
    # Summary by type
    print("\n" + "=" * 80)
    print("SUMMARY BY CHUNK TYPE")
    print("=" * 80)
    
    summary_count = sum(1 for p in chunks if p.payload.get('chunk_type') == 'summary')
    chapter_count = sum(1 for p in chunks if p.payload.get('chunk_type') == 'chapter')
    
    print(f"\n   Summary chunks  : {summary_count}")
    print(f"   Chapter chunks  : {chapter_count}")
    print(f"   ─────────────────────────")
    print(f"   Total chunks    : {len(chunks)}")
    
    # Summary by resource (if showing multiple resources)
    if resource_id is None:
        print("\n" + "=" * 80)
        print("SUMMARY BY RESOURCE")
        print("=" * 80)
        
        resource_map = {}
        for point in chunks:
            res_id = point.payload.get('resource_id')
            resource_map[res_id] = resource_map.get(res_id, 0) + 1
        
        for res_id in sorted(resource_map.keys()):
            print(f"\n   Resource {res_id}: {resource_map[res_id]} chunks")


def main():
    """
    Main function to find and display chunks.
    """
    print("=" * 80)
    print("CHUNK FINDER - Find Chunks by Course/Module/Resource")
    print("=" * 80)
    
    # Validate COURSE_ID
    if COURSE_ID is None:
        print("\n❌ Error: COURSE_ID must be specified!")
        print("Please set COURSE_ID at the top of the file.")
        return
    
    # Display what we're searching for
    print(f"\n🎯 Searching for:")
    print(f"   Course ID   : {COURSE_ID}")
    print(f"   Module ID   : {MODULE_ID if MODULE_ID is not None else 'ALL'}")
    print(f"   Resource ID : {RESOURCE_ID if RESOURCE_ID is not None else 'ALL'}")
    
    try:
        # Find chunks
        print(f"\n⏳ Fetching chunks from Qdrant...")
        chunks = find_chunks(COURSE_ID, MODULE_ID, RESOURCE_ID)
        
        # Display results
        display_chunks(chunks, COURSE_ID, MODULE_ID, RESOURCE_ID)
        
        print("\n" + "=" * 80)
        print("✅ SEARCH COMPLETED")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()