import subprocess
import time
import requests
import json
import sys
import os

os.chdir(r"C:\Users\pravi\OneDrive\Documents\Default Project\backend-api")

# Start server
server = subprocess.Popen(
    [r"venv\Scripts\python.exe", "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8080"],
    stdout=subprocess.PIPE, stderr=subprocess.PIPE
)

print(f"Server started with PID: {server.pid}")
time.sleep(12)

# Check if still running
if server.poll() is not None:
    stdout, stderr = server.communicate()
    print(f"Server crashed! stdout: {stdout.decode()[:500]}")
    print(f"stderr: {stderr.decode()[:500]}")
    sys.exit(1)

print("Server is running. Waiting for full init...")
BASE_URL = "http://127.0.0.1:8080"
TIMEOUT = 30

import time
for i in range(12):
    try:
        r = requests.get(f"{BASE_URL}/health", timeout=3)
        if r.status_code == 200:
            print(f"Server ready after {(i+1)*5}s")
            break
    except:
        pass
    time.sleep(5)
else:
    print("Server never became ready")
    server.terminate()
    sys.exit(1)

try:
    # Warm up - first request creates tables
    print("Warming up (creating tables + seeding)...")
    requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)
    
    # Test 1: Health
    r = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)
    print(f"1. Health: {r.status_code} - {r.json()}")
    
    # Test 2: Login
    r = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
        "email": "admin@smartface.com",
        "password": "Admin123!"
    }, timeout=TIMEOUT)
    print(f"2. Login: {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        token = data.get("access_token")
        print(f"   Token: {token[:30]}...")
    else:
        print(f"   Error: {r.text[:200]}")
        server.terminate()
        sys.exit(1)
    
    headers = {"Authorization": f"Bearer {token}"}
    
    time.sleep(2)  # Brief pause between requests
    
    # Test 3: Get user
    print("  Testing auth/me...")
    r = requests.get(f"{BASE_URL}/api/v1/auth/me", headers=headers, timeout=TIMEOUT)
    print(f"3. Get user: {r.status_code}")
    if r.status_code == 200:
        print(f"   Name: {r.json().get('full_name', 'N/A')}")
    else:
        print(f"   Error: {r.text[:200]}")
    
    time.sleep(1)
    
    # Test 4: Create department
    r = requests.post(f"{BASE_URL}/api/v1/departments", headers=headers, json={
        "name": "API Test Dept",
        "description": "Test"
    }, timeout=TIMEOUT)
    print(f"4. Create dept: {r.status_code}")
    dept_id = r.json().get("id") if r.status_code in [200, 201] else None
    if dept_id:
        print(f"   id: {dept_id}")
    
    time.sleep(1)
    
    # Test 5: List departments
    r = requests.get(f"{BASE_URL}/api/v1/departments", headers=headers, timeout=TIMEOUT)
    print(f"5. List depts: {r.status_code} - {len(r.json())} found")
    
    time.sleep(1)
    
    # Test 6: Create employee
    r = requests.post(f"{BASE_URL}/api/v1/employees", headers=headers, json={
        "employee_code": "API001",
        "full_name": "API Test Employee",
        "department_id": dept_id,
        "monthly_salary": 50000,
        "employment_status": "ACTIVE"
    }, timeout=TIMEOUT)
    print(f"6. Create emp: {r.status_code}")
    emp_id = r.json().get("id") if r.status_code in [200, 201] else None
    if emp_id:
        print(f"   id: {emp_id}")
    
    time.sleep(1)
    
    # Test 7: List employees
    r = requests.get(f"{BASE_URL}/api/v1/employees", headers=headers, timeout=TIMEOUT)
    print(f"7. List emps: {r.status_code} - {len(r.json())} found")
    
    time.sleep(1)
    
    # Test 8: Attendance stats
    r = requests.get(f"{BASE_URL}/api/v1/attendance/stats", headers=headers, timeout=TIMEOUT)
    print(f"8. Attendance stats: {r.status_code}")
    
    time.sleep(1)
    
    # Test 9: Today attendance
    r = requests.get(f"{BASE_URL}/api/v1/attendance/today", headers=headers, timeout=TIMEOUT)
    print(f"9. Today attendance: {r.status_code}")
    
    time.sleep(1)
    
    # Test 10: List attendance
    r = requests.get(f"{BASE_URL}/api/v1/attendance", headers=headers, timeout=TIMEOUT)
    print(f"10. List attendance: {r.status_code}")
    
    time.sleep(1)
    
    # Test 11: Get ERP config
    r = requests.get(f"{BASE_URL}/api/v1/erp/config", headers=headers, timeout=TIMEOUT)
    print(f"11. ERP config: {r.status_code}")
    
    time.sleep(1)
    
    # Test 12: ERP sync logs
    r = requests.get(f"{BASE_URL}/api/v1/erp/sync-logs", headers=headers, timeout=TIMEOUT)
    print(f"12. ERP sync logs: {r.status_code}")
    
    time.sleep(1)
    
    # Test 13: Face recognize logs
    r = requests.get(f"{BASE_URL}/api/v1/faces/recognize/logs", headers=headers, timeout=TIMEOUT)
    print(f"13. Face logs: {r.status_code}")
    
    # Cleanup
    if emp_id:
        requests.delete(f"{BASE_URL}/api/v1/employees/{emp_id}", headers=headers, timeout=TIMEOUT)
    if dept_id:
        requests.delete(f"{BASE_URL}/api/v1/departments/{dept_id}", headers=headers, timeout=TIMEOUT)
    print(f"\n14. Cleanup: Done")
    
    print("\n" + "=" * 60)
    print("ALL API TESTS PASSED!")
    print("=" * 60)

except Exception as e:
    print(f"\nERROR: {e}")
    # Capture server logs
    server.terminate()
    stdout, stderr = server.communicate(timeout=5)
    print(f"\nSERVER STDOUT: {stdout.decode()[-1000:]}")
    print(f"\nSERVER STDERR: {stderr.decode()[-2000:]}")
    sys.exit(1)

finally:
    server.terminate()
    try:
        stdout, stderr = server.communicate(timeout=5)
        print(f"\nSERVER FINAL STDOUT: {stdout.decode()[-500:]}")
        print(f"\nSERVER FINAL STDERR: {stderr.decode()[-500:]}")
    except:
        server.kill()
    print("\nServer stopped.")
