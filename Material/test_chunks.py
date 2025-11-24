import os
import google.generativeai as genai
from qdrant_client import QdrantClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure Google Generative AI
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))


def search_similar_chunks(query, top_k=5, course_id=None):
    """
    Search for similar chunks in Qdrant based on the query.
    
    Args:
        query: Search query string
        top_k: Number of results to return
        course_id: Optional course_id filter
        
    Returns:
        List of top_k most similar chunks with their metadata
    """
    # Initialize Qdrant client
    client = QdrantClient(
        url=os.getenv("QDRANT_URL"),
        api_key=os.getenv("QDRANT_API_KEY")
    )
    
    collection_name = os.getenv("QDRANT_COLLECTION_NAME_MATERIAL")
    
    # Generate embedding for the query
    result = genai.embed_content(
        model="models/text-embedding-004",
        content=query,
        task_type="retrieval_query"
    )
    query_embedding = result['embedding']
    
    # Build filter if course_id is provided
    query_filter = None
    if course_id is not None:
        from qdrant_client.models import Filter, FieldCondition, MatchValue
        query_filter = Filter(
            must=[
                FieldCondition(
                    key="course_id",
                    match=MatchValue(value=course_id)
                )
            ]
        )
    
    # Search in Qdrant
    search_results = client.query_points(
        collection_name=collection_name,
        query=query_embedding,
        query_filter=query_filter,
        limit=top_k
    ).points
    
    return search_results


def display_chunks(search_results):
    """
    Display search results in a readable format.
    """
    if not search_results:
        print("\n❌ No relevant chunks found.")
        return
    
    print("\n" + "=" * 80)
    print(f"TOP {len(search_results)} RELEVANT CHUNKS")
    print("=" * 80)
    
    for idx, result in enumerate(search_results, 1):
        payload = result.payload
        score = result.score
        
        print(f"\n{'='*80}")
        print(f"CHUNK #{idx} | Relevance Score: {score:.4f}")
        print(f"{'='*80}")
        
        print(f"\n📌 Metadata:")
        print(f"   Course ID     : {payload.get('course_id')}")
        print(f"   Book Name     : {payload.get('book_name')}")
        print(f"   Page Number   : {payload.get('page')}")
        print(f"   Chunk ID      : {payload.get('chunk_id')}")
        
        content = payload.get('text', 'No content available')
        print(f"\n📄 Content:")
        print(f"   {content[:500]}{'...' if len(content) > 500 else ''}")
        print()


def main():
    """
    Main interface to search and display material chunks.
    """
    print("=" * 80)
    print("QDRANT MATERIAL CHUNK RETRIEVAL TOOL")
    print("=" * 80)
    print("\nSearch for relevant chunks from course materials (PDFs).")
    print("Type 'exit' or 'quit' to end.\n")
    
    # Optional: Ask for course_id filter
    filter_by_course = input("🔍 Filter by course_id? (Enter course_id or press Enter to skip): ").strip()
    course_filter = None
    
    if filter_by_course.isdigit():
        course_filter = int(filter_by_course)
        print(f"✓ Filtering results for course_id: {course_filter}")
    else:
        print("✓ Searching across all courses")
    
    while True:
        # Get user input
        user_query = input("\n🔎 Enter search query: ").strip()
        
        if not user_query:
            continue
        
        if user_query.lower() in ['exit', 'quit', 'bye']:
            print("\n👋 Goodbye!")
            break
        
        try:
            # Search for relevant chunks
            print(f"\n⏳ Searching for: '{user_query}'...")
            search_results = search_similar_chunks(user_query, top_k=5, course_id=course_filter)
            
            if not search_results:
                print("\n❌ No relevant chunks found.")
                continue
            
            # Display the chunks
            display_chunks(search_results)
            
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()
            print("Please try again.")


if __name__ == "__main__":
    main()