import os
import google.generativeai as genai
from qdrant_client import QdrantClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure Google Generative AI
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))


def search_similar_chunks(query, top_k=5):
    """
    Search for similar chunks in Qdrant based on the query.
    Returns top_k most similar chunks with their metadata.
    """
    # Initialize Qdrant client
    client = QdrantClient(
        url=os.getenv("QDRANT_URL"),
        api_key=os.getenv("QDRANT_API_KEY")
    )
    
    collection_name = os.getenv("QDRANT_COLLECTION_NAME")
    
    # Generate embedding for the query
    result = genai.embed_content(
        model="models/text-embedding-004",
        content=query,
        task_type="retrieval_query"
    )
    query_embedding = result['embedding']
    
    # Search in Qdrant
    search_results = client.query_points(
        collection_name=collection_name,
        query=query_embedding,
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
    print("QDRANT CHUNK RETRIEVAL TOOL")
    print("=" * 80)
    print("\nSearch for relevant chunks from the course database.")
    print("Type 'exit' or 'quit' to end.\n")
    
    while True:
        # Get user input
        user_query = input("\n🔍 Enter search query: ").strip()
        
        if not user_query:
            continue
        
        if user_query.lower() in ['exit', 'quit', 'bye']:
            print("\n👋 Goodbye!")
            break
        
        try:
            # Search for relevant chunks
            print(f"\n⏳ Searching for: '{user_query}'...")
            search_results = search_similar_chunks(user_query, top_k=5)
            
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