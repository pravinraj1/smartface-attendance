import requests
import json
import sys

BASE_URL = "http://127.0.0.1:8080"

def test_api():
    print("=" * 60)
    print("SMARTFACE API TESTS - FastAPI + Supabase PostgreSQL")
    print("=" * 60)
    
    # Test 1: Health check
    r = requests.get(f"{BASE_URL}/health")
    print(f"\n1. Health: {r.status_code} - {r.json()}")
    
    # Test 2: Login
    r = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
        "email": "admin@smartface.com",
        "password": "Admin123!"
    })
    print(f"2. Login: {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        token = data.get("access_token")
        print(f"   Token received: {token[:30]}...")
    else:
        print(f"   Error: {r.text}")
        return
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test 3: Get current user
    r = requests.get(f"{BASE_URL}/api/v1/auth/me", headers=headers)
    print(f"3. Get user: {r.status_code} - {r.json().get('full_name', 'N/A')}")
    
    # Test 4: Create department
    r = requests.post(f"{BASE_URL}/api/v1/departments", headers=headers, json={
        "name": "Test Department",
        "description": "API test department"
    })
    print(f"4. Create dept: {r.status_code}")
    if r.status_code in [200, 201]:
        dept = r.json()
        dept_id = dept.get("id")
        print(f"   Created: {dept.get('name')} (id={dept_id})")
    else:
        print(f"   Error: {r.text[:100]}")
        dept_id = None
    
    # Test 5: List departments
    r = requests.get(f"{BASE_URL}/api/v1/departments", headers=headers)
    print(f"5. List depts: {r.status_code} - {len(r.json())} found")
    
    # Test 6: Create employee
    r = requests.post(f"{BASE_URL}/api/v1/employees", headers=headers, json={
        "employee_code": "API001",
        "full_name": "API Test Employee",
        "department_id": dept_id,
        "monthly_salary": 50000,
        "employment_status": "ACTIVE"
    })
    print(f"6. Create emp: {r.status_code}")
    if r.status_code in [200, 201]:
        emp = r.json()
        emp_id = emp.get("id")
        print(f"   Created: {emp.get('full_name')} ({emp.get('employee_code')})")
    else:
        print(f"   Error: {r.text[:100]}")
        emp_id = None
    
    # Test 7: List employees
    r = requests.get(f"{BASE_URL}/api/v1/employees", headers=headers)
    print(f"7. List emps: {r.status_code} - {len(r.json())} found")
    
    # Test 8: Attendance stats
    r = requests.get(f"{BASE_URL}/api/v1/attendance/stats", headers=headers)
    print(f"8. Attendance stats: {r.status_code}")
    if r.status_code == 200:
        stats = r.json()
        print(f"   Stats: {json.dumps(stats, indent=2)[:200]}")
    
    # Test 9: Today attendance
    r = requests.get(f"{BASE_URL}/api/v1/attendance/today", headers=headers)
    print(f"9. Today attendance: {r.status_code}")
    
    # Test 10: List attendance
    r = requests.get(f"{BASE_URL}/api/v1/attendance", headers=headers)
    print(f"10. List attendance: {r.status_code}")
    
    # Test 11: Get ERP config
    r = requests.get(f"{BASE_URL}/api/v1/erp/config", headers=headers)
    print(f"11. ERP config: {r.status_code}")
    
    # Test 12: Create ERP config
    r = requests.post(f"{BASE_URL}/api/v1/erp/config", headers=headers, json={
        "erp_name": "Test ERP",
        "erp_url": "https://test.erp.com/api",
        "api_key": "test-key-123",
        "data_format": "xml"
    })
    print(f"12. Create ERP config: {r.status_code}")
    
    # Test 13: Get ERP config again
    r = requests.get(f"{BASE_URL}/api/v1/erp/config", headers=headers)
    print(f"13. Get ERP config: {r.status_code}")
    if r.status_code == 200:
        config = r.json()
        print(f"   ERP: {config.get('erp_name')} ({config.get('erp_url', 'N/A')[:40]})")
    
    # Test 14: ERP sync logs
    r = requests.get(f"{BASE_URL}/api/v1/erp/sync-logs", headers=headers)
    print(f"14. ERP sync logs: {r.status_code}")
    
    # Test 15: Face enrollment (JSON base64)
    r = requests.post(f"{BASE_URL}/api/v1/faces/enroll", headers=headers, json={
        "employee_id": emp_id,
        "image_data": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    })
    print(f"15. Face enroll: {r.status_code}")
    
    # Cleanup: Delete test data
    if emp_id:
        requests.delete(f"{BASE_URL}/api/v1/employees/{emp_id}", headers=headers)
    if dept_id:
        requests.delete(f"{BASE_URL}/api/v1/departments/{dept_id}", headers=headers)
    print(f"\n16. Cleanup: Done")
    
    print("\n" + "=" * 60)
    print("API TESTS COMPLETE!")
    print("=" * 60)

if __name__ == "__main__":
    try:
        test_api()
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)
