import os
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue, PayloadSchemaType
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ============================================
# CONFIGURE DELETION CRITERIA HERE
# ============================================
COURSE_ID = 329          # Required: Must specify course_id
MODULE_ID = None         # Optional: None = all modules in course
RESOURCE_ID = None       # Optional: None = all resources in module
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


def delete_vectors(client, collection_name, course_id, module_id=None, resource_id=None):
    """
    Delete vectors based on specified scope - FLEXIBLE VERSION.
    
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
        # Build filter conditions CONDITIONALLY
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
        print(f"\n📊 Found {points_count} existing chunks to delete")
        
        if points_count == 0:
            print(f"\n✓ No existing vectors found for this scope")
            print("   Nothing to delete.")
            return
        
        # Determine scope description
        if module_id is None and resource_id is None:
            scope = f"entire course {course_id}"
        elif resource_id is None:
            scope = f"all resources in module {module_id}"
        else:
            scope = f"resource {resource_id}"
        
        # Confirm deletion
        print(f"\n⚠️  WARNING: This will permanently delete {points_count} chunks from {scope}!")
        confirmation = input("   Type 'YES' to confirm deletion: ").strip()
        
        if confirmation != 'YES':
            print("\n✖ Deletion cancelled by user")
            return
        
        # Delete points
        print(f"\n⏳ Deleting {points_count} chunks...")
        client.delete(
            collection_name=collection_name,
            points_selector=delete_filter
        )
        print(f"✓ Successfully deleted {points_count} vectors")
        
        # Verify deletion
        print(f"\n🔍 Verifying deletion...")
        verify_result = client.count(
            collection_name=collection_name,
            count_filter=delete_filter
        )
        
        remaining_count = verify_result.count
        
        if remaining_count == 0:
            print(f"✓ Verification successful: All chunks deleted")
        else:
            print(f"⚠️  Warning: {remaining_count} chunks still remain")
        
    except Exception as e:
        print(f"\n✖ Error during deletion: {e}")
        import traceback
        traceback.print_exc()


def main():
    """
    Main function to delete chunks based on specified scope.
    """
    print("=" * 70)
    print("CHUNK DELETER - Flexible Deletion by Course/Module/Resource")
    print("=" * 70)
    
    # Validate COURSE_ID
    if COURSE_ID is None:
        print("\n✖ Error: COURSE_ID is required!")
        print("Please set COURSE_ID at the top of the file.")
        return
    
    # Determine scope description
    if MODULE_ID is None and RESOURCE_ID is None:
        scope = f"entire course {COURSE_ID}"
    elif RESOURCE_ID is None:
        scope = f"all resources in module {MODULE_ID}"
    else:
        scope = f"resource {RESOURCE_ID}"
    
    print(f"\n🎯 Deletion Scope:")
    print(f"   Course ID   : {COURSE_ID}")
    print(f"   Module ID   : {MODULE_ID if MODULE_ID is not None else 'ALL'}")
    print(f"   Resource ID : {RESOURCE_ID if RESOURCE_ID is not None else 'ALL'}")
    print(f"\n📋 This will delete: {scope}")
    
    try:
        # Initialize Qdrant client
        print(f"\n⏳ Connecting to Qdrant...")
        client = QdrantClient(
            url=os.getenv("QDRANT_URL"),
            api_key=os.getenv("QDRANT_API_KEY")
        )
        print(f"✓ Connected to Qdrant")
        
        collection_name = os.getenv("QDRANT_COLLECTION_NAME_VIDEO")
        print(f"✓ Using collection: {collection_name}")
        
        # Ensure indexes exist before deletion
        ensure_indexes_exist(client, collection_name)
        
        # Delete chunks
        delete_vectors(client, collection_name, COURSE_ID, MODULE_ID, RESOURCE_ID)
        
        # Show collection stats
        print("\n" + "=" * 70)
        print("COLLECTION STATISTICS")
        print("=" * 70)
        
        collection_info = client.get_collection(collection_name)
        print(f"\n   Total vectors in collection: {collection_info.points_count}")
        
        print("\n" + "=" * 70)
        print("✅ DELETION PROCESS COMPLETED")
        print("=" * 70)
        print("\n💡 TIP: Use find_chunks.py to verify the chunks are deleted")
        
    except Exception as e:
        print(f"\n✖ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()