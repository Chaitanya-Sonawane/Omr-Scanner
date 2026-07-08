#!/usr/bin/env python3
"""
Test the complete OMR API workflow
"""
import requests
import json
import time

BASE_URL = "http://localhost:8000/api"

def test_workflow():
    print("🧪 Testing OMR API Workflow\n")
    
    # 1. Create session
    print("1️⃣  Creating session...")
    resp = requests.post(f"{BASE_URL}/session")
    assert resp.status_code == 200
    session_id = resp.json()["session_id"]
    print(f"   ✅ Session created: {session_id}\n")
    
    # 2. Set answer key manually
    print("2️⃣  Setting answer key...")
    answer_key = {str(i): str((i % 4) + 1) for i in range(1, 41)}  # Sample answers
    resp = requests.post(
        f"{BASE_URL}/session/{session_id}/answer-key/manual",
        json={"answers": answer_key}
    )
    assert resp.status_code == 200
    print(f"   ✅ Answer key set (40 questions)\n")
    
    # 3. Upload sheets
    print("3️⃣  Uploading test sheets...")
    with open("inputs/sample1/MobileCamera/sheet1.jpg", "rb") as f:
        files = {"files": ("sheet1.jpg", f, "image/jpeg")}
        data = {"names": "John Doe"}
        resp = requests.post(
            f"{BASE_URL}/session/{session_id}/sheets",
            files=files,
            data=data
        )
    assert resp.status_code == 200
    result = resp.json()
    print(f"   ✅ Uploaded {result['total_sheets']} sheet(s)\n")
    
    # 4. Check status
    print("4️⃣  Checking status...")
    resp = requests.get(f"{BASE_URL}/session/{session_id}/status")
    assert resp.status_code == 200
    status = resp.json()
    print(f"   📊 Status: {status['status']}")
    print(f"   📄 Queued: {status['queued']}\n")
    
    # 5. Start processing (SSE stream)
    print("5️⃣  Processing sheets...")
    resp = requests.get(f"{BASE_URL}/session/{session_id}/progress", stream=True)
    
    for line in resp.iter_lines():
        if line:
            line_str = line.decode('utf-8')
            if line_str.startswith('data: '):
                data = json.loads(line_str[6:])
                event_type = data.get('type')
                
                if event_type == 'SHEET_START':
                    print(f"   🔄 Processing: {data['studentName']}")
                elif event_type == 'SHEET_DONE':
                    print(f"   ✅ Done: {data['studentName']} - Score: {data['score']}/{data['total']}")
                elif event_type == 'SHEET_ERROR':
                    print(f"   ❌ Error: {data.get('error')}")
                elif event_type == 'BATCH_COMPLETE':
                    print(f"\n   🎉 Batch complete! Total processed: {data['totalProcessed']}\n")
                    break
    
    # 6. Get results
    print("6️⃣  Fetching results...")
    resp = requests.get(f"{BASE_URL}/session/{session_id}/results")
    assert resp.status_code == 200
    results = resp.json()
    
    print(f"   📈 Statistics:")
    if results['results']:
        stats = results['statistics']
        print(f"      - Total Students: {stats['total_students']}")
        print(f"      - Average Score: {stats['average_score']:.1f}/{results['total_questions']}")
        print(f"      - Pass Rate: {stats['pass_rate']:.1f}%")
        print(f"      - Highest: {stats['highest_score']}")
        print(f"      - Lowest: {stats['lowest_score']}\n")
    
    # 7. Show individual results
    print("7️⃣  Individual Results:")
    for result in results['results']:
        print(f"   👤 {result['name']}: {result['score']}/{result['total']} ({result['percentage']:.1f}%)")
        if result.get('flags'):
            print(f"      ⚠️  Flags: {result['flags']}")
    
    print("\n✅ All tests passed! API is working correctly.")
    return True

if __name__ == "__main__":
    try:
        test_workflow()
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
