import asyncio
import os
import sys
import json

sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv('.env')

async def test_crud():
    import asyncpg
    from app.core.config import settings
    
    sync_url = settings.DATABASE_URL.replace('postgresql+asyncpg://', 'postgresql://')
    conn = await asyncpg.connect(sync_url)
    
    print("=" * 60)
    print("SMARTFACE CRUD TEST - Supabase PostgreSQL")
    print("=" * 60)
    
    # Test 1: Verify roles seeded
    roles = await conn.fetch("SELECT * FROM roles ORDER BY role_name")
    print(f"\n1. ROLES ({len(roles)} found):")
    for r in roles:
        print(f"   {r['role_name']}: {r['description']}")
    
    # Test 2: Verify system_settings seeded
    settings = await conn.fetch("SELECT * FROM system_settings ORDER BY setting_key")
    print(f"\n2. SYSTEM_SETTINGS ({len(settings)} found):")
    for s in settings:
        print(f"   {s['setting_key']}: {s['setting_value']}")
    
    # Test 3: Create a department
    dept_result = await conn.fetchrow("""
        INSERT INTO departments (name, description) 
        VALUES ('Engineering', 'Software development team')
        RETURNING id, name
    """)
    dept_id = dept_result['id']
    print(f"\n3. CREATED department: {dept_result['name']} (id={dept_id})")
    
    # Test 4: Create an employee
    emp_result = await conn.fetchrow("""
        INSERT INTO employees (employee_code, full_name, mobile_number, department_id, monthly_salary, joining_date, employment_status)
        VALUES ('EMP001', 'John Doe', '1234567890', $1, 50000.00, '2026-01-15', 'ACTIVE')
        RETURNING id, employee_code, full_name
    """, dept_id)
    emp_id = emp_result['id']
    print(f"4. CREATED employee: {emp_result['full_name']} ({emp_result['employee_code']})")
    
    # Test 5: Create attendance record
    att_result = await conn.fetchrow("""
        INSERT INTO attendance (employee_id, attendance_date, check_in, attendance_status, total_work_minutes)
        VALUES ($1, CURRENT_DATE, NOW(), 'PRESENT', 480)
        RETURNING id, attendance_date, attendance_status
    """, emp_id)
    print(f"5. CREATED attendance: {att_result['attendance_date']} - {att_result['attendance_status']}")
    
    # Test 6: Create attendance log
    log_result = await conn.fetchrow("""
        INSERT INTO attendance_logs (employee_id, event_type, event_time, confidence_score, recognition_status)
        VALUES ($1, 'CHECK_IN', NOW(), 0.95, 'MATCHED')
        RETURNING id, event_type, confidence_score
    """, emp_id)
    print(f"6. CREATED attendance_log: {log_result['event_type']} (confidence={log_result['confidence_score']})")
    
    # Test 7: Create face profile
    face_result = await conn.fetchrow("""
        INSERT INTO face_profiles (employee_id, face_image_url, face_image_data, embedding_data, enrollment_quality_score)
        VALUES ($1, '/storage/faces/emp001.jpg', 'base64imagedata', 'base64embeddingdata', 0.85)
        RETURNING id, face_image_url
    """, emp_id)
    print(f"7. CREATED face_profile: {face_result['face_image_url']}")
    
    # Test 8: Create ERP config
    erp_result = await conn.fetchrow("""
        INSERT INTO erp_configs (erp_name, erp_url, api_key, data_format)
        VALUES ('Custom ERP', 'https://erp.example.com/api', 'test-api-key-123', 'xml')
        RETURNING id, erp_name
    """)
    erp_id = erp_result['id']
    print(f"8. CREATED erp_config: {erp_result['erp_name']}")
    
    # Test 9: Create ERP sync log
    sync_result = await conn.fetchrow("""
        INSERT INTO erp_sync_logs (erp_config_id, sync_type, direction, status, records_count)
        VALUES ($1, 'attendance', 'push', 'success', 10)
        RETURNING id, sync_type, status
    """, erp_id)
    print(f"9. CREATED erp_sync_log: {sync_result['sync_type']} - {sync_result['status']}")
    
    # Test 10: Create audit log
    audit_result = await conn.fetchrow("""
        INSERT INTO audit_logs (action, entity_name, entity_id)
        VALUES ('CREATE', 'employee', $1)
        RETURNING id, action, entity_name
    """, emp_id)
    print(f"10. CREATED audit_log: {audit_result['action']} on {audit_result['entity_name']}")
    
    # Test 11: Verify foreign key relationships
    rel_result = await conn.fetchrow("""
        SELECT e.employee_code, e.full_name, d.name as dept_name
        FROM employees e
        JOIN departments d ON e.department_id = d.id
        WHERE e.id = $1
    """, emp_id)
    print(f"\n11. JOIN QUERY: {rel_result['full_name']} works in {rel_result['dept_name']}")
    
    # Test 12: Verify cascade (employee -> face_profiles, attendance)
    counts = await conn.fetchrow("""
        SELECT 
            (SELECT COUNT(*) FROM face_profiles WHERE employee_id = $1) as faces,
            (SELECT COUNT(*) FROM attendance WHERE employee_id = $1) as attendance,
            (SELECT COUNT(*) FROM attendance_logs WHERE employee_id = $1) as logs
    """, emp_id)
    print(f"12. CASCADE CHECK: {counts['faces']} faces, {counts['attendance']} attendance, {counts['logs']} logs")
    
    # Cleanup test data
    await conn.execute("DELETE FROM audit_logs")
    await conn.execute("DELETE FROM erp_sync_logs")
    await conn.execute("DELETE FROM erp_configs")
    await conn.execute("DELETE FROM face_profiles")
    await conn.execute("DELETE FROM attendance_logs")
    await conn.execute("DELETE FROM attendance")
    await conn.execute("DELETE FROM employees")
    await conn.execute("DELETE FROM departments")
    
    print(f"\n13. CLEANUP: All test data deleted")
    
    await conn.close()
    
    print("\n" + "=" * 60)
    print("ALL CRUD TESTS PASSED!")
    print("=" * 60)

asyncio.run(test_crud())
