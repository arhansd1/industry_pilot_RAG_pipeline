import os
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue, PayloadSchemaType
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ============================================
# CONFIGURE DELETION CRITERIA HERE
# ============================================
COURSE_ID = 329
MODULE_ID = 575  # Set to None to get all modules in course
RESOURCE_ID = 1564  # Set to None to get all resources in module
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


def delete_resource_vectors(client, collection_name, course_id, module_id, resource_id):
    """
    Delete all vectors related to a specific resource from Qdrant.
    Uses the unique combination of course_id, module_id, and resource_id.
    
    This is the EXACT same deletion logic used in resource_updater.py
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
        print(f"\n📊 Found {points_count} existing chunks to delete")
        
        if points_count == 0:
            print(f"\n✓ No existing vectors found for this resource")
            print("   Nothing to delete.")
            return
        
        # Confirm deletion
        print(f"\n⚠️  WARNING: This will permanently delete {points_count} chunks!")
        confirmation = input("   Type 'YES' to confirm deletion: ").strip()
        
        if confirmation != 'YES':
            print("\n❌ Deletion cancelled by user")
            return
        
        # Delete points with matching course_id, module_id, and resource_id
        print(f"\n⏳ Deleting {points_count} chunks...")
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
        
        # Verify deletion
        print(f"\n🔍 Verifying deletion...")
        verify_result = client.count(
            collection_name=collection_name,
            count_filter=Filter(
                must=[
                    FieldCondition(key="course_id", match=MatchValue(value=course_id)),
                    FieldCondition(key="module_id", match=MatchValue(value=module_id)),
                    FieldCondition(key="resource_id", match=MatchValue(value=resource_id))
                ]
            )
        )
        
        remaining_count = verify_result.count
        
        if remaining_count == 0:
            print(f"✓ Verification successful: All chunks deleted")
        else:
            print(f"⚠️  Warning: {remaining_count} chunks still remain")
        
    except Exception as e:
        print(f"\n❌ Error during deletion: {e}")
        import traceback
        traceback.print_exc()


def main():
    """
    Main function to delete chunks for a specific resource.
    """
    print("=" * 70)
    print("CHUNK DELETER - Delete Resource Chunks from Qdrant")
    print("=" * 70)
    print(f"\n🎯 Target Resource:")
    print(f"   Course ID   : {COURSE_ID}")
    print(f"   Module ID   : {MODULE_ID}")
    print(f"   Resource ID : {RESOURCE_ID}")
    
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
        delete_resource_vectors(client, collection_name, COURSE_ID, MODULE_ID, RESOURCE_ID)
        
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
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()