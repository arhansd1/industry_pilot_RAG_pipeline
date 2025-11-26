import os
import google.generativeai as genai
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure Google Generative AI
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# ============================================
# CONFIGURE FILTER CRITERIA HERE
# ============================================
COURSE_ID = 329  # Set to course_id or None for all courses
MODULE_ID = 575   # Set to module_id or None for all modules
RESOURCE_ID = 1564  # Set to resource_id or None for all resources
# ============================================


def search_similar_chunks(query, course_id=None, module_id=None, resource_id=None, top_k=5):
    """
    Search for similar chunks in Qdrant based on the query.
    Optionally filter by course_id, module_id, and/or resource_id.
    Returns top_k most similar chunks with their metadata.
    
    Filter Logic:
    - If all None: Search across all chunks
    - If course_id only: Search within that course
    - If course_id + module_id: Search within that module
    - If course_id + module_id + resource_id: Search within that resource
    """
    # Initialize Qdrant client
    client = QdrantClient(
        url=os.getenv("QDRANT_URL"),
        api_key=os.getenv("QDRANT_API_KEY")
    )
    
    collection_name = os.getenv("QDRANT_COLLECTION_NAME_VIDEO")
    
    # Generate embedding for the query
    result = genai.embed_content(
        model="models/text-embedding-004",
        content=query,
        task_type="retrieval_query"
    )
    query_embedding = result['embedding']
    
    # Build filter conditions
    filter_conditions = []
    
    if course_id is not None:
        filter_conditions.append(
            FieldCondition(key="course_id", match=MatchValue(value=course_id))
        )
    
    if module_id is not None:
        filter_conditions.append(
            FieldCondition(key="module_id", match=MatchValue(value=module_id))
        )
    
    if resource_id is not None:
        filter_conditions.append(
            FieldCondition(key="resource_id", match=MatchValue(value=resource_id))
        )
    
    # Create filter if conditions exist
    search_filter = Filter(must=filter_conditions) if filter_conditions else None
    
    # Search in Qdrant
    search_results = client.query_points(
        collection_name=collection_name,
        query=query_embedding,
        query_filter=search_filter,
        limit=top_k
    ).points
    
    return search_results


def display_chunks(search_results, course_id=None, module_id=None, resource_id=None):
    """
    Display search results in a readable format.
    """
    if not search_results:
        print("\n❌ No relevant chunks found.")
        return
    
    print("\n" + "=" * 80)
    print(f"TOP {len(search_results)} RELEVANT CHUNKS")
    print("=" * 80)
    
    # Display filter criteria if any
    if course_id is not None or module_id is not None or resource_id is not None:
        print(f"\n🔍 Filtered by:")
        if course_id is not None:
            print(f"   Course ID   : {course_id}")
        if module_id is not None:
            print(f"   Module ID   : {module_id}")
        if resource_id is not None:
            print(f"   Resource ID : {resource_id}")
    else:
        print(f"\n🔍 Searching across ALL courses/modules/resources")
    
    for idx, result in enumerate(search_results, 1):
        payload = result.payload
        score = result.score
        
        print(f"\n{'='*80}")
        print(f"CHUNK #{idx} | Relevance Score: {score:.4f}")
        print(f"{'='*80}")
        
        print(f"\n📌 Metadata:")
        print(f"   Course ID     : {payload.get('course_id')}")
        print(f"   Module ID     : {payload.get('module_id')}")
        print(f"   Resource ID   : {payload.get('resource_id')}")
        print(f"   Chunk ID      : {payload.get('chunk_id')}")
        print(f"   Type          : {payload.get('chunk_type')}")
        print(f"   Chunk Index   : {payload.get('chunk_index')}")
        
        if payload.get('chunk_type') == 'chapter':
            print(f"   Topic         : {payload.get('topic_title', 'N/A')}")
            print(f"   Subtopic      : {payload.get('subtopic_title', 'N/A')}")
        
        content = payload.get('text', 'No content available')
        print(f"\n📄 Content:")
        print(f"   {content}")
        print()


def main():
    """
    Main interface to search and display chunks.
    """
    print("=" * 80)
    print("QDRANT CHUNK RETRIEVAL TOOL (WITH FILTERING)")
    print("=" * 80)
    
    # Display filter settings
    print("\n🎯 Filter Settings:")
    print(f"   Course ID   : {COURSE_ID if COURSE_ID is not None else 'ALL'}")
    print(f"   Module ID   : {MODULE_ID if MODULE_ID is not None else 'ALL'}")
    print(f"   Resource ID : {RESOURCE_ID if RESOURCE_ID is not None else 'ALL'}")
    
    print("\nSearch for relevant chunks from the course database.")
    print("Type 'exit' or 'quit' to end.\n")
    
    while True:
        # Get user input
        user_query = input("\n🔎 Enter search query: ").strip()
        
        if not user_query:
            continue
        
        if user_query.lower() in ['exit', 'quit', 'bye']:
            print("\n👋 Goodbye!")
            break
        
        try:
            # Search for relevant chunks with filters
            print(f"\n⏳ Searching for: '{user_query}'...")
            search_results = search_similar_chunks(
                user_query, 
                course_id=COURSE_ID,
                module_id=MODULE_ID,
                resource_id=RESOURCE_ID,
                top_k=5
            )
            
            if not search_results:
                print("\n❌ No relevant chunks found.")
                continue
            
            # Display the chunks
            display_chunks(search_results, COURSE_ID, MODULE_ID, RESOURCE_ID)
            
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()
            print("Please try again.")


if __name__ == "__main__":
    main()