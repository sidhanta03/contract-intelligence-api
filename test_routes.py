"""
Test script for Contract Intelligence API routes
"""
import requests
import json
import sys
from pathlib import Path

BASE_URL = "http://localhost:8000"

def test_health():
    """Test health endpoint"""
    print("🔍 Testing health endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/healthz", timeout=5)
        if response.status_code == 200:
            print("✅ Health check passed")
            print(f"   Response: {response.json()}")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False


def test_ingest(pdf_path):
    """Test ingest endpoint"""
    print("\n🔍 Testing ingest endpoint...")
    
    if not Path(pdf_path).exists():
        print(f"❌ PDF file not found: {pdf_path}")
        return None
    
    try:
        with open(pdf_path, 'rb') as f:
            files = {'files': f}
            response = requests.post(
                f"{BASE_URL}/api/ingest/",
                files=files,
                timeout=60
            )
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Ingest successful")
            print(f"   Document IDs: {data['document_ids']}")
            print(f"   Details: {json.dumps(data['details'], indent=2)}")
            return data['document_ids'][0] if data['document_ids'] else None
        else:
            print(f"❌ Ingest failed: {response.status_code}")
            print(f"   Error: {response.json()}")
            return None
    except Exception as e:
        print(f"❌ Ingest error: {e}")
        return None


def test_extract(document_id):
    """Test extract endpoint"""
    print("\n🔍 Testing extract endpoint...")
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/extract",
            json={"document_id": document_id},
            timeout=60
        )
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Extract successful")
            print(f"   Parties: {data.get('parties')}")
            print(f"   Effective Date: {data.get('effective_date')}")
            print(f"   Term: {data.get('term')}")
            print(f"   Governing Law: {data.get('governing_law')}")
            print(f"   Auto Renewal: {data.get('auto_renewal')}")
            print(f"   Full response: {json.dumps(data, indent=2)}")
            return True
        else:
            print(f"❌ Extract failed: {response.status_code}")
            print(f"   Error: {response.json()}")
            return False
    except Exception as e:
        print(f"❌ Extract error: {e}")
        return False


def test_ask(document_id, query="What are the main terms of this contract?"):
    """Test ask endpoint"""
    print("\n🔍 Testing ask endpoint...")
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/ask",
            json={
                "document_id": document_id,
                "query": query,
                "top_k": 5
            },
            timeout=60
        )
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Ask successful")
            print(f"   Query: {data['query']}")
            print(f"   Answer: {data['answer']}")
            print(f"   Citations: {len(data['citations'])} chunks")
            for i, citation in enumerate(data['citations'][:3], 1):
                print(f"   Citation {i}:")
                print(f"      - Chunk index: {citation['chunk_index']}")
                print(f"      - Char range: {citation['char_range']}")
                print(f"      - Relevance: {citation['relevance_score']:.4f}")
            return True
        else:
            print(f"❌ Ask failed: {response.status_code}")
            print(f"   Error: {response.json()}")
            return False
    except Exception as e:
        print(f"❌ Ask error: {e}")
        return False


def run_all_tests(pdf_path="test_contract.pdf"):
    """Run all tests in sequence"""
    print("=" * 60)
    print("Contract Intelligence API - Route Tests")
    print("=" * 60)
    
    # Test 1: Health Check
    if not test_health():
        print("\n❌ Server is not responding. Make sure it's running on", BASE_URL)
        return False
    
    # Test 2: Ingest
    document_id = test_ingest(pdf_path)
    if not document_id:
        print("\n⚠️  Ingest failed. Remaining tests skipped.")
        return False
    
    # Test 3: Extract
    extract_success = test_extract(document_id)
    
    # Test 4: Ask
    ask_success = test_ask(document_id)
    ask_success2 = test_ask(
        document_id, 
        "What are the termination clauses?"
    )
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    print(f"Health Check: ✅ Passed")
    print(f"Ingest:       {'✅ Passed' if document_id else '❌ Failed'}")
    print(f"Extract:      {'✅ Passed' if extract_success else '❌ Failed'}")
    print(f"Ask (Q1):     {'✅ Passed' if ask_success else '❌ Failed'}")
    print(f"Ask (Q2):     {'✅ Passed' if ask_success2 else '❌ Failed'}")
    print("=" * 60)
    
    all_passed = all([document_id, extract_success, ask_success, ask_success2])
    
    if all_passed:
        print("\n🎉 All tests passed!")
    else:
        print("\n⚠️  Some tests failed. Check the output above.")
    
    return all_passed


if __name__ == "__main__":
    if len(sys.argv) > 1:
        pdf_file = sys.argv[1]
    else:
        print("Usage: python test_routes.py <path_to_pdf>")
        print("\nExample: python test_routes.py sample_contract.pdf")
        print("\nRunning with default (will fail if file doesn't exist)...")
        pdf_file = "test_contract.pdf"
    
    success = run_all_tests(pdf_file)
    sys.exit(0 if success else 1)
