import time
import requests
import json
import sys

BASE_URL = "http://localhost:8000"

ANSWERABLE_QUERIES = [
    "How often does AWS bill customers?",
    "What are my responsibilities for backing up content?",
    "When can AWS suspend my services?",
    "How does AWS calculate and invoice monthly fees?",
    "Under what section is content backup responsibility defined?",
    "What constitutes a material breach that allows AWS to suspend services?",
    "Can the customer terminate the agreement for convenience?",
    "What happens to customer content upon termination of the services?",
    "Does AWS provide any express warranties under the agreement?",
    "Is there a limitation of liability clause for indirect damages?",
    "Which country or state laws govern the AWS Customer Agreement?",
    "How does AWS notify customers of changes to the agreement?",
    "What are the customer obligations regarding account security and keys?",
    "Does the agreement include a force majeure clause?",
    "How are intellectual property rights allocated between AWS and customers?",
    "Are there any confidentiality obligations for trade secrets?",
    "Can I transfer my rights under the agreement to a third party?",
    "What is the definition of Your Content in the agreement?",
    "Does AWS exclude warranties of merchantability and fitness for a particular purpose?",
    "What notice is required for AWS to terminate the agreement?"
]

IRRELEVANT_QUERIES = [
    "Who founded AWS?",
    "What is the price of EC2?",
    "Does AWS provide free certification courses?",
    "What is the best way to bake a chocolate cake?",
    "What is the current weather forecast in Seattle?",
    "How do I write a fast HTTP server in Go?",
    "Who won the last football world cup tournament?",
    "What is the height of Mount Everest in meters?",
    "Can you explain Einstein's theory of general relativity?",
    "How do I set up a local Git repository on my machine?"
]

def run_seeding():
    print("=== AWS Customer Agreement Assistant - Seeding & Test Script ===")
    
    # 1. Check if server is running
    try:
        response = requests.get(f"{BASE_URL}/analytics", timeout=5)
    except requests.exceptions.ConnectionError:
        print(f"Error: Could not connect to API server at {BASE_URL}.")
        print("Please start the FastAPI server first, e.g. by running:")
        print("  python -m uvicorn app.api.main:app --host 127.0.0.1 --port 8000")
        sys.exit(1)
        
    # 2. Call /ingest automatically
    print("\nCalling POST /ingest to prepare FAISS index...")
    try:
        ingest_res = requests.post(f"{BASE_URL}/ingest", json={"force": True}, timeout=60)
        if ingest_res.status_code == 200:
            ingest_data = ingest_res.json()
            print(f"Ingestion successful! Created {ingest_data.get('chunks_created')} chunks.")
        else:
            print(f"Ingestion failed with status code {ingest_res.status_code}: {ingest_res.text}")
            sys.exit(1)
    except Exception as e:
        print(f"Failed to call /ingest: {e}")
        sys.exit(1)

    # 3. Execute queries
    all_queries = [
        {"query": q, "category": "Answerable"} for q in ANSWERABLE_QUERIES
    ] + [
        {"query": q, "category": "Irrelevant"} for q in IRRELEVANT_QUERIES
    ]
    
    results = []
    print(f"\nExecuting {len(all_queries)} test queries against POST /ask...")
    
    for i, item in enumerate(all_queries, 1):
        q = item["query"]
        cat = item["category"]
        print(f"[{i:02d}/30] [{cat}] Sending: '{q}'")
        
        start_time = time.perf_counter()
        try:
            res = requests.post(f"{BASE_URL}/ask", json={"query": q}, timeout=20)
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            
            if res.status_code == 200:
                data = res.json()
                results.append({
                    "query": q,
                    "category": cat,
                    "status_code": 200,
                    "answer_found": data.get("answer_found"),
                    "response_time_ms": data.get("response_time_ms", elapsed_ms),
                    "model_used": data.get("model_used")
                })
            else:
                print(f"    -> Warning: received status {res.status_code}: {res.text}")
                results.append({
                    "query": q,
                    "category": cat,
                    "status_code": res.status_code,
                    "answer_found": False,
                    "response_time_ms": elapsed_ms,
                    "model_used": "error"
                })
        except Exception as e:
            print(f"    -> Connection error: {e}")
            results.append({
                "query": q,
                "category": cat,
                "status_code": 500,
                "answer_found": False,
                "response_time_ms": (time.perf_counter() - start_time) * 1000.0,
                "model_used": "error"
            })
            
    # 4. Print summary statistics
    print("\n" + "="*50)
    print("                SUMMARY STATISTICS")
    print("="*50)
    
    total_queries = len(results)
    successful_requests = sum(1 for r in results if r["status_code"] == 200)
    answerable_count = sum(1 for r in results if r["category"] == "Answerable")
    irrelevant_count = sum(1 for r in results if r["category"] == "Irrelevant")
    
    answers_found_for_answerable = sum(1 for r in results if r["category"] == "Answerable" and r["answer_found"])
    answers_found_for_irrelevant = sum(1 for r in results if r["category"] == "Irrelevant" and r["answer_found"])
    
    avg_latency = sum(r["response_time_ms"] for r in results) / total_queries if total_queries else 0
    
    print(f"Total Queries Executed:           {total_queries}")
    print(f"Successful API Requests (200 OK): {successful_requests}/{total_queries}")
    print(f"Average API Latency:              {avg_latency:.2f} ms")
    print(f"Answerable Queries Sent:          {answerable_count}")
    print(f"  - Answers Found:                {answers_found_for_answerable}/{answerable_count} ({(answers_found_for_answerable/answerable_count*100) if answerable_count else 0:.1f}%)")
    print(f"Irrelevant Queries Sent:          {irrelevant_count}")
    print(f"  - Answers Found:                {answers_found_for_irrelevant}/{irrelevant_count} ({(answers_found_for_irrelevant/irrelevant_count*100) if irrelevant_count else 0:.1f}%)")
    print("="*50)

if __name__ == "__main__":
    run_seeding()
