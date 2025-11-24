import os
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue
from dotenv import load_dotenv
from pdf_converter import process_pdf_to_chunks
from embedder import upload_chunks_to_qdrant

# Load environment variables
load_dotenv()

# ============================================
# CONFIGURE COURSE AND PDF HERE
# ============================================
COURSE_ID = 313
PDF_PATH = "Material/Generative AI_ A Beginner's Guide.pdf"
BOOK_NAME = "Generative AI_ A Beginner's Guide"  # Short identifier for the book
# ============================================


def delete_course_material_vectors(client, collection_name, course_id):
    """
    Delete all material vectors related to a specific course_id from Qdrant.
    """
    print(f"\n🗑️  Deleting existing material vectors for course_id: {course_id}...")
    
    try:
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
        print(f"✓ Deleted all material vectors for course_id: {course_id}")
    except Exception as e:
        print(f"⚠️  Warning: Could not delete vectors: {e}")
        print("   Continuing with upload...")


def main():
    """
    Main function to update course material in Qdrant.
    
    Process:
    1. Delete existing material vectors for the course
    2. Convert PDF to chunks
    3. Generate embeddings and upload to Qdrant
    """
    print("=" * 70)
    print("COURSE MATERIAL UPDATER - PDF to Qdrant Pipeline")
    print("=" * 70)
    print(f"\n🎯 Target Course ID: {COURSE_ID}")
    print(f"📄 PDF Path: {PDF_PATH}")
    print(f"📚 Book Name: {BOOK_NAME}")
    
    # Validate PDF exists
    if not os.path.exists(PDF_PATH):
        print(f"\n❌ Error: PDF file not found at {PDF_PATH}")
        print("Please check the PDF_PATH configuration.")
        return
    
    # Initialize Qdrant client
    client = QdrantClient(
        url=os.getenv("QDRANT_URL"),
        api_key=os.getenv("QDRANT_API_KEY")
    )
    collection_name = os.getenv("QDRANT_COLLECTION_NAME_MATERIAL")
    
    # Step 1: Delete existing course material vectors
    delete_course_material_vectors(client, collection_name, COURSE_ID)
    
    # Step 2: Convert PDF to chunks
    print("\n" + "=" * 70)
    print("STEP 1: PDF CONVERSION")
    print("=" * 70)
    
    try:
        chunks = process_pdf_to_chunks(PDF_PATH, COURSE_ID, BOOK_NAME)
        
        if not chunks:
            print(f"\n⚠️  No chunks created from PDF")
            print("Exiting...")
            return
            
    except Exception as e:
        print(f"\n❌ Error converting PDF: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Step 3: Generate embeddings and upload to Qdrant
    print("\n" + "=" * 70)
    print("STEP 2: EMBEDDING & UPLOAD")
    print("=" * 70)
    
    try:
        upload_chunks_to_qdrant(chunks)
    except Exception as e:
        print(f"\n❌ Error uploading to Qdrant: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Summary
    print("\n" + "=" * 70)
    print(f"✅ MATERIAL UPDATE COMPLETED FOR COURSE_ID: {COURSE_ID}")
    print("=" * 70)
    
    # Show collection stats
    try:
        collection_info = client.get_collection(collection_name)
        print(f"\nCollection Info:")
        print(f"  Total vectors: {collection_info.points_count}")
    except Exception as e:
        print(f"⚠️  Could not retrieve collection info: {e}")


if __name__ == "__main__":
    main()