import os
import fitz  # PyMuPDF
from typing import List, Dict, Any
from app.utils.logger import logger
try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
except ImportError:
    from langchain.text_splitter import RecursiveCharacterTextSplitter


class PDFIngestor:
    """Handles parsing and chunking of the AWS Customer Agreement PDF."""

    @staticmethod
    def extract_and_chunk(pdf_path: str, chunk_size: int = 500, chunk_overlap: int = 100) -> List[Dict[str, Any]]:
        """
        Extracts text from PDF and splits it into chunks, preserving page numbers and adding metadata.
        Returns a list of dicts: {'text': str, 'metadata': {'page': int, 'chunk_id': str}}
        """
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF file not found at: {pdf_path}")

        logger.info("Opening PDF for parsing", extra={"pdf_path": pdf_path})
        doc = fitz.open(pdf_path)
        chunks = []
        chunk_counter = 0

        # We split using tiktoken encoder if possible, or fallback to character splitter with typical character to token ratio
        try:
            splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                model_name="gpt-4"  # standard tokenizer model
            )
        except Exception as e:
            print(f"Warning: Tiktoken text splitter initialization failed: {e}. Falling back to character-based splitting.")
            # 1 token is roughly 4 characters
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size * 4,
                chunk_overlap=chunk_overlap * 4
            )

        for page_idx in range(len(doc)):
            page = doc[page_idx]
            page_text = page.get_text()
            
            # Basic cleaning: strip leading/trailing spaces
            page_text = page_text.strip()
            
            # Simple header/footer stripping: skip very short strings or header patterns
            cleaned_lines = []
            for line in page_text.split("\n"):
                stripped_line = line.strip()
                # Skip page numbers, website URLs, or common headers
                if not stripped_line:
                    continue
                if stripped_line.isdigit():
                    continue
                if "aws.amazon.com" in stripped_line.lower():
                    continue
                cleaned_lines.append(stripped_line)
            
            cleaned_page_text = "\n".join(cleaned_lines)
            if not cleaned_page_text:
                continue

            # Split text of this page
            page_chunks = splitter.split_text(cleaned_page_text)
            
            for chunk_text in page_chunks:
                chunk_id = f"chunk_{chunk_counter:04d}"
                chunks.append({
                    "text": chunk_text,
                    "metadata": {
                        "chunk_id": chunk_id,
                        "page": page_idx + 1,  # 1-indexed pages
                        "source": os.path.basename(pdf_path)
                    }
                })
                chunk_counter += 1

        logger.info("Extraction and chunking complete", extra={"chunk_count": len(chunks)})
        return chunks
