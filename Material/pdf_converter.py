import fitz  # PyMuPDF
import os


def extract_text_from_pdf(pdf_path):
    """
    Extract text from PDF file page by page.
    Returns a list of dictionaries with page number and text content.
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")
    
    print(f"\n📄 Processing PDF: {pdf_path}")
    
    doc = fitz.open(pdf_path)
    pages_data = []
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text()
        
        if text.strip():  # Only add pages with content
            pages_data.append({
                "page": page_num + 1,  # 1-indexed page numbers
                "text": text.strip()
            })
    
    doc.close()
    
    print(f"✅ Extracted text from {len(pages_data)} pages")
    return pages_data


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


def process_pdf_to_chunks(pdf_path, course_id, book_name):
    """
    Process PDF and create chunks with metadata.
    
    Args:
        pdf_path: Path to the PDF file
        course_id: Course ID to associate with chunks
        book_name: Name of the book/material
        
    Returns:
        List of chunk dictionaries with metadata
    """
    print(f"\n🔄 Converting PDF to chunks...")
    print(f"   Course ID: {course_id}")
    print(f"   Book Name: {book_name}")
    
    # Extract pages from PDF
    pages_data = extract_text_from_pdf(pdf_path)
    
    all_chunks = []
    chunk_counter = 0
    
    for page_data in pages_data:
        page_num = page_data["page"]
        page_text = page_data["text"]
        
        # Split page text into 250-word chunks
        text_chunks = chunk_text_by_words(page_text, max_words=250)
        
        for chunk_text in text_chunks:
            chunk_id = f"{course_id}_{book_name}_{page_num}_{chunk_counter}"
            
            all_chunks.append({
                "course_id": course_id,
                "book_name": book_name,
                "page": page_num,
                "chunk_id": chunk_id,
                "text": chunk_text
            })
            
            chunk_counter += 1
    
    print(f"✅ Created {len(all_chunks)} chunks from {len(pages_data)} pages")
    return all_chunks