import os
import pytest
import json
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.main import app, vector_manager
from app.config import settings
from app.db.session import Base, get_db
from app.db.logger import DBLogger
from app.models.query_log import QueryLog
from app.rag.ingestor import PDFIngestor
from app.rag.vector_store import VectorStoreManager
from app.services.llm import LLMService

# Setup test database
TEST_DATABASE_URL = "sqlite:///./test_rag_logs.db"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Override get_db dependency in FastAPI app
def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(scope="module", autouse=True)
def setup_db():
    """Create test database tables before running tests, and drop after."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    if os.path.exists("./test_rag_logs.db"):
        try:
            os.remove("./test_rag_logs.db")
        except PermissionError:
            pass


client = TestClient(app)

def test_config():
    """Verify settings loaded from config."""
    assert settings.EMBEDDING_MODEL == "all-MiniLM-L6-v2"
    assert settings.TOP_K == 4

def test_query_before_ingestion():
    """Verify that asking a question before ingestion returns a 409 Conflict."""
    # Mock exists to return False
    original_exists = vector_manager.exists
    vector_manager.exists = lambda: False
    
    try:
        response = client.post("/ask", json={"query": "Who founded AWS?"})
        assert response.status_code == 409
        assert "FAISS index missing" in response.json()["detail"]
    finally:
        vector_manager.exists = original_exists

def test_analytics_endpoint_empty_database():
    """Verify that analytics endpoint returns correct zero values on an empty database."""
    db = TestingSessionLocal()
    try:
        # Clear database logs
        db.query(QueryLog).delete()
        db.commit()
    finally:
        db.close()
        
    response = client.get("/analytics")
    assert response.status_code == 200
    data = response.json()
    assert data["total_queries"] == 0
    assert data["average_response_time_ms"] == 0.0
    assert data["answer_found_rate_pct"] == 0.0
    assert len(data["top_5_questions"]) == 0

def test_successful_pdf_ingestion():
    """Verify that successful PDF ingestion creates vector database and returns 200."""
    # Run ingestion
    response = client.post("/ingest", json={"force": True})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["chunks_created"] > 0
    assert data["embedding_model"] == settings.EMBEDDING_MODEL

def test_duplicate_pdf_ingestion():
    """Verify that duplicate ingestion returns HTTP 409 Conflict if force=False."""
    # Call ingest again with force=False (default behavior)
    response = client.post("/ingest", json={"force": False})
    assert response.status_code == 409
    assert "Index already exists" in response.json()["detail"]

def test_valid_ask_query():
    """Verify that a valid query returns HTTP 200 with the expected answer."""
    query_text = "How often does AWS bill customers?"
    response = client.post("/ask", json={"query": query_text})
    assert response.status_code == 200
    data = response.json()
    assert data["query"] == query_text
    assert "monthly" in data["answer"].lower()
    assert data["answer_found"] is True
    assert len(data["sources"]) > 0
    assert data["response_time_ms"] > 0
    assert "model_used" in data

def test_empty_query():
    """Verify empty query inputs return 400 Bad Request."""
    # Completely empty query
    response = client.post("/ask", json={"query": ""})
    assert response.status_code == 400
    assert "Query cannot be empty" in response.json()["detail"]

    # Spaces only query
    response = client.post("/ask", json={"query": "       "})
    assert response.status_code == 400
    assert "Query cannot be empty" in response.json()["detail"]

def test_analytics_endpoint_with_data():
    """Verify analytics endpoint aggregates queries successfully."""
    response = client.get("/analytics")
    assert response.status_code == 200
    data = response.json()
    assert data["total_queries"] >= 1
    assert data["average_response_time_ms"] > 0.0
    assert data["answer_found_rate_pct"] == 100.0
    assert len(data["top_5_questions"]) >= 1
    assert data["top_5_questions"][0]["query"] == "How often does AWS bill customers?"

def test_ask_validation():
    """Verify detailed validation requirements for /ask endpoint."""
    # Empty request body
    response = client.post("/ask", content="")
    assert response.status_code == 422

    # Empty JSON object (missing query field)
    response = client.post("/ask", json={})
    assert response.status_code == 422

    # Invalid JSON fails
    response = client.post("/ask", content="{invalid json", headers={"Content-Type": "application/json"})
    assert response.status_code == 422

    # Query with length < 3 characters fails
    response = client.post("/ask", json={"query": "ab"})
    assert response.status_code == 422

    # Query with length > 500 characters fails
    response = client.post("/ask", json={"query": "a" * 501})
    assert response.status_code == 422

    # Query with spaces padding, but valid length after trimming (should pass validation)
    response = client.post("/ask", json={"query": "   abc   "})
    assert response.status_code == 200

def test_exception_handlers_404_and_500():
    """Verify 404 PDF not found and 500 unexpected exception responses."""
    # 404: PDF not found
    original_pdf_path = settings.PDF_PATH
    settings.PDF_PATH = "non_existent_file_path_123.pdf"
    
    try:
        response = client.post("/ingest", json={"force": True})
        assert response.status_code == 404
        assert "PDF not found" in response.json()["detail"]
    finally:
        settings.PDF_PATH = original_pdf_path

    # 500: Unexpected exceptions
    original_exists = vector_manager.exists
    def mock_exists():
        raise RuntimeError("Unexpected DB failure.")
    vector_manager.exists = mock_exists

    try:
        client_no_raise = TestClient(app, raise_server_exceptions=False)
        response = client_no_raise.post("/ask", json={"query": "valid query"})
        assert response.status_code == 500
        assert response.json()["detail"] == "An unexpected error occurred."
    finally:
        vector_manager.exists = original_exists

def test_structured_logging():
    """Verify that logging produces structured JSON and redacts secrets."""
    from app.utils.logger import logger
    
    # Check that a log is written
    logger.info("Test log message", extra={"test_field": "test_value"})
    
    # Verify log file exists
    assert os.path.exists("logs/app.log")
    
    with open("logs/app.log", "r", encoding="utf-8") as f:
        lines = f.readlines()
        last_line = lines[-1].strip()
        
    log_data = json.loads(last_line)
    assert log_data["message"] == "Test log message"
    assert log_data["test_field"] == "test_value"
    assert "timestamp" in log_data
    assert log_data["level"] == "INFO"

    # Verify secret redaction
    logger.info("HF Token log test", extra={"secret_token": "hf_abcdefghijklmnopqrstuvwxyz01234567"})
    
    with open("logs/app.log", "r", encoding="utf-8") as f:
        lines = f.readlines()
        last_line = lines[-1].strip()
        
    log_data = json.loads(last_line)
    assert log_data["secret_token"] == "********"

def test_pdf_generation_script():
    """Verify that PDF generation script works."""
    source_md = r"C:\Users\josep\.gemini\antigravity\brain\492d8a3c-40c9-4f61-9149-5c941a88a313\.system_generated\steps\128\content.md"
    test_pdf_path = "./test_agreement.pdf"
    
    from app.utils.pdf_generator import generate_pdf
    generate_pdf(source_md, test_pdf_path)
    assert os.path.exists(test_pdf_path)
    
    if os.path.exists(test_pdf_path):
        os.remove(test_pdf_path)
