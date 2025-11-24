import sys
from Video.extracter import export_to_json
from Video.embedder import process_and_upload_data


def main():
    """
    Main orchestrator that runs the entire pipeline:
    1. Extract data from PostgreSQL (test.py)
    2. Generate embeddings and upload to Qdrant (embedder.py)
    """
    
    print("=" * 60)
    print("COURSE DATA EMBEDDING PIPELINE")
    print("=" * 60)
    
    # Step 1: Extract from PostgreSQL
    print("\n[STEP 1/2] Extracting data from PostgreSQL...")
    print("-" * 60)
    
    data = export_to_json()
    
    if data is None or len(data) == 0:
        print("\n❌ Error: No data extracted from database. Exiting.")
        sys.exit(1)
    
    print(f"\n✓ Successfully extracted {len(data)} resources")
    
    # Step 2: Generate embeddings and upload to Qdrant
    print("\n[STEP 2/2] Generating embeddings and uploading to Qdrant...")
    print("-" * 60)
    
    try:
        process_and_upload_data("course_data.json")
        print("\n" + "=" * 60)
        print("✓ PIPELINE COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Error in embedding process: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()