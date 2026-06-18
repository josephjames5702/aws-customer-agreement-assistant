import time
import os
from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from app.config import settings
from app.db.session import get_db, engine, Base
from app.db.logger import DBLogger
from app.schemas.rag import AskRequest, AskResponse, IngestRequest, IngestResponse, AnalyticsResponse, Source
from app.rag.ingestor import PDFIngestor
from app.rag.vector_store import VectorStoreManager
from app.services.llm import LLMService
from app.utils.logger import logger

# Initialize Database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="AWS Agreement Assistant API")

@app.on_event("startup")
def startup_event():
    logger.info("Application startup completed", extra={"event": "startup"})

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global Exception Handlers

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    # 400: empty query
    # Check if query parameter is empty or spaces only, but present
    for error in exc.errors():
        loc = error.get("loc", [])
        if "query" in loc and error.get("type") != "missing":
            input_val = error.get("input")
            # If the query field is None, or empty string (after strip)
            if input_val is None or (isinstance(input_val, str) and not input_val.strip()):
                logger.error("API Error: empty query validation failed", extra={"status_code": 400})
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={"detail": "Query cannot be empty."}
                )

    # 422: other validation errors
    # Format and return errors without exposing internal stack traces
    logger.error("API Error: request validation failed", extra={"status_code": 422, "errors": exc.errors()})
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors()}
    )

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    # Ensure no internal traceback or sensitive detail is exposed for 500s
    logger.error("API Error: HTTP exception raised", extra={"status_code": exc.status_code, "detail": exc.detail})
    if exc.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "An unexpected error occurred."}
        )
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    # Log the full exception on the server side
    logger.error("API Error: unexpected internal exception", exc_info=exc, extra={"status_code": 500})
    
    # 500: unexpected exceptions (never expose stack traces)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An unexpected error occurred."}
    )

# Initialize vector store manager
vector_manager = VectorStoreManager()

@app.post("/ingest", response_model=IngestResponse, status_code=status.HTTP_200_OK)
def ingest_document(payload: IngestRequest = IngestRequest(), db: Session = Depends(get_db)):
    """
    Triggers PDF parsing, chunking, embedding, and vector store generation.
    Returns chunk count and status. Returns 409 if index exists and force=False.
    """
    logger.info("PDF ingestion initiated", extra={"force": payload.force})
    if vector_manager.exists() and not payload.force:
        logger.error("API Error: duplicate ingestion attempted without force=True", extra={"status_code": 409})
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Index already exists. Use force=True to re-ingest."
        )

    if not os.path.exists(settings.PDF_PATH):
        # Let's create the PDF if it's missing, using the compiler
        logger.info("PDF missing. Attempting to compile from cached content...", extra={"pdf_path": settings.PDF_PATH})
        try:
            from app.utils.pdf_generator import generate_pdf
            # Check standard steps paths for step 128
            steps_dir = r"C:\Users\josep\.gemini\antigravity\brain\492d8a3c-40c9-4f61-9149-5c941a88a313\.system_generated\steps"
            # Look for steps content.md
            md_path = None
            if os.path.exists(steps_dir):
                for folder in sorted(os.listdir(steps_dir), reverse=True):
                    candidate = os.path.join(steps_dir, folder, "content.md")
                    if os.path.exists(candidate):
                        md_path = candidate
                        break
            
            if md_path:
                generate_pdf(md_path, settings.PDF_PATH)
            else:
                raise FileNotFoundError("Could not locate agreement source content.md in steps cache.")
        except Exception as e:
            logger.error("API Error: PDF file not found and auto-generation failed", exc_info=e, extra={"status_code": 404})
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="PDF not found."
            )

    try:
        # Parse PDF and split into chunks
        chunks = PDFIngestor.extract_and_chunk(
            settings.PDF_PATH,
            chunk_size=500,
            chunk_overlap=100
        )
        
        # Build FAISS database
        chunks_created = vector_manager.build_and_save(chunks, force=True)
        
        logger.info("PDF ingestion completed successfully", extra={"chunks_created": chunks_created, "embedding_model": settings.EMBEDDING_MODEL})
        return IngestResponse(
            status="success",
            chunks_created=chunks_created,
            embedding_model=settings.EMBEDDING_MODEL,
            message="Index built and saved to disk."
        )
    except Exception as e:
        logger.error("PDF Ingestion failed", exc_info=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ingestion failed: {str(e)}"
        )

@app.post("/ask", response_model=AskResponse, status_code=status.HTTP_200_OK)
def ask_question(payload: AskRequest, db: Session = Depends(get_db)):
    """
    Accepts query, performs similarity search, passes top chunks to LLM, 
    logs the event to database, and returns answer and sources.
    """
    if not vector_manager.exists():
        logger.error("API Error: FAISS index missing when processing ask request", extra={"status_code": 409})
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="FAISS index missing. Please call POST /ingest first."
        )

    start_time = time.perf_counter()
    
    try:
        # Load vector database if not already done
        if not vector_manager._db:
            vector_manager.load()

        # Retrieve top k matching documents
        retrieval_start = time.perf_counter()
        results = vector_manager.similarity_search(payload.query, k=settings.TOP_K)
        retrieval_time_ms = (time.perf_counter() - retrieval_start) * 1000.0
        logger.info("Vector retrieval complete", extra={"retrieval_time_ms": retrieval_time_ms, "query": payload.query})
        
        # Format sources
        sources = []
        for doc, score in results:
            sources.append(Source(
                chunk_id=doc.metadata.get("chunk_id", "unknown"),
                page=doc.metadata.get("page", 0),
                text_snippet=doc.page_content[:200],  # Return first 200 chars as snippet
                similarity_score=float(score)
            ))

        # Generate answer using LLM service
        llm_start = time.perf_counter()
        answer, answer_found, model_used = LLMService.answer_query(payload.query, results)
        llm_response_time_ms = (time.perf_counter() - llm_start) * 1000.0
        logger.info("LLM response generated", extra={"llm_response_time_ms": llm_response_time_ms, "model_used": model_used})
        
        # Calculate overall latency in ms
        latency_ms = (time.perf_counter() - start_time) * 1000.0
        
        # Log to database
        sources_logged = [
            {"chunk_id": src.chunk_id, "page": src.page, "similarity_score": src.similarity_score}
            for src in sources
        ]
        DBLogger.log_query(
            db=db,
            query=payload.query,
            answer=answer,
            answer_found=answer_found,
            response_time_ms=latency_ms,
            sources=sources_logged,
            model_used=model_used
        )

        return AskResponse(
            query=payload.query,
            answer=answer,
            answer_found=answer_found,
            sources=sources,
            response_time_ms=latency_ms,
            model_used=model_used
        )
    except Exception as e:
        logger.error("Error processing ask request", exc_info=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while processing query: {str(e)}"
        )

@app.get("/analytics", response_model=AnalyticsResponse, status_code=status.HTTP_200_OK)
def get_analytics(db: Session = Depends(get_db)):
    """Fetches SQL logging statistics and returns aggregated results."""
    try:
        analytics_data = DBLogger.get_analytics(db)
        return AnalyticsResponse(**analytics_data)
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve analytics: {str(e)}"
        )
