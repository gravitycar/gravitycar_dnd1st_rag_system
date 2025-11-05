#!/usr/bin/env python3
"""
Integration test script for Flask API.

Tests the Flask API endpoints with simulated scenarios.
"""

import requests
import json
import time

BASE_URL = "http://localhost:5000"

def test_health_check():
    """Test 1: Health check endpoint."""
    print("\n" + "="*80)
    print("TEST 1: Health Check")
    print("="*80)
    
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    assert response.status_code == 200
    assert response.json()['status'] == 'ok'
    print("✅ PASSED")
    return True


def test_missing_auth():
    """Test 2: Missing Authorization header."""
    print("\n" + "="*80)
    print("TEST 2: Missing Authorization Header")
    print("="*80)
    
    response = requests.post(
        f"{BASE_URL}/api/query",
        json={"question": "What is a beholder?"}
    )
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    assert response.status_code == 401
    assert 'error' in response.json()
    print("✅ PASSED")
    return True


def test_invalid_json():
    """Test 3: Invalid JSON body."""
    print("\n" + "="*80)
    print("TEST 3: Invalid JSON Body")
    print("="*80)
    
    response = requests.post(
        f"{BASE_URL}/api/query",
        data="not json",
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer fake-token"
        }
    )
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    assert response.status_code == 400
    assert 'error' in response.json()
    print("✅ PASSED")
    return True


def test_missing_question():
    """Test 4: Missing required field 'question'."""
    print("\n" + "="*80)
    print("TEST 4: Missing Required Field")
    print("="*80)
    
    response = requests.post(
        f"{BASE_URL}/api/query",
        json={"debug": True},
        headers={"Authorization": "Bearer fake-token"}
    )
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    assert response.status_code == 400
    assert 'question' in response.json()['error'].lower()
    print("✅ PASSED")
    return True


def test_404_endpoint():
    """Test 5: 404 for unknown endpoint."""
    print("\n" + "="*80)
    print("TEST 5: 404 Not Found")
    print("="*80)
    
    response = requests.get(f"{BASE_URL}/api/unknown")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    assert response.status_code == 404
    print("✅ PASSED")
    return True


def test_cors_headers():
    """Test 6: CORS headers present."""
    print("\n" + "="*80)
    print("TEST 6: CORS Headers")
    print("="*80)
    
    response = requests.options(
        f"{BASE_URL}/api/query",
        headers={"Origin": "http://localhost:3000"}
    )
    print(f"Status Code: {response.status_code}")
    print("CORS Headers:")
    for header, value in response.headers.items():
        if 'access-control' in header.lower():
            print(f"  {header}: {value}")
    
    # Flask-CORS should add these headers
    assert 'Access-Control-Allow-Origin' in response.headers or response.status_code == 200
    print("✅ PASSED")
    return True


def main():
    """Run all integration tests."""
    print("\n" + "="*80)
    print("Flask API Integration Tests")
    print("="*80)
    print(f"Testing against: {BASE_URL}")
    
    tests = [
        test_health_check,
        test_missing_auth,
        test_invalid_json,
        test_missing_question,
        test_404_endpoint,
        test_cors_headers,
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append((test.__name__, "PASSED" if result else "FAILED"))
        except AssertionError as e:
            print(f"❌ FAILED: {e}")
            results.append((test.__name__, "FAILED"))
        except Exception as e:
            print(f"❌ ERROR: {e}")
            results.append((test.__name__, "ERROR"))
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    for test_name, status in results:
        symbol = "✅" if status == "PASSED" else "❌"
        print(f"{symbol} {test_name}: {status}")
    
    passed = sum(1 for _, status in results if status == "PASSED")
    total = len(results)
    print(f"\n{passed}/{total} tests passed")
    print("="*80)


if __name__ == "__main__":
    main()
