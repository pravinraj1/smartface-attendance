"""fresh supabase migration - all tables with UUID PKs

Revision ID: 001
Revises: 
Create Date: 2026-08-27

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

uuid_pk = postgresql.UUID(as_uuid=True)
uuid_fk = postgresql.UUID(as_uuid=True)
uuid_default = sa.text('gen_random_uuid()')


def upgrade() -> None:
    op.create_table(
        'departments',
        sa.Column('id', uuid_pk, primary_key=True, server_default=uuid_default),
        sa.Column('name', sa.String(100), unique=True, nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('is_active', sa.Boolean, server_default='true'),
        sa.Column('created_at', sa.TIMESTAMP, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.TIMESTAMP, server_default=sa.text('CURRENT_TIMESTAMP')),
    )

    op.create_table(
        'employees',
        sa.Column('id', uuid_pk, primary_key=True, server_default=uuid_default),
        sa.Column('employee_code', sa.String(50), unique=True, nullable=False),
        sa.Column('full_name', sa.String(255), nullable=False),
        sa.Column('mobile_number', sa.String(20), unique=True),
        sa.Column('department_id', uuid_fk, sa.ForeignKey('departments.id')),
        sa.Column('monthly_salary', sa.Numeric(12, 2)),
        sa.Column('joining_date', sa.Date),
        sa.Column('employment_status', sa.String(20), server_default='ACTIVE'),
        sa.Column('face_enrolled', sa.Boolean, server_default='false'),
        sa.Column('notes', sa.Text),
        sa.Column('created_at', sa.TIMESTAMP, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.TIMESTAMP, server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    op.create_index('idx_employee_code', 'employees', ['employee_code'])
    op.create_index('idx_employee_mobile', 'employees', ['mobile_number'])

    op.create_table(
        'face_profiles',
        sa.Column('id', uuid_pk, primary_key=True, server_default=uuid_default),
        sa.Column('employee_id', uuid_fk, sa.ForeignKey('employees.id', ondelete='CASCADE'), nullable=False),
        sa.Column('face_image_url', sa.Text, nullable=False),
        sa.Column('face_image_data', sa.Text),
        sa.Column('qdrant_vector_id', sa.String(255)),
        sa.Column('embedding_data', sa.Text),
        sa.Column('embedding_version', sa.String(50)),
        sa.Column('enrollment_quality_score', sa.Numeric(5, 2)),
        sa.Column('is_primary', sa.Boolean, server_default='true'),
        sa.Column('created_at', sa.TIMESTAMP, server_default=sa.text('CURRENT_TIMESTAMP')),
    )

    op.create_table(
        'attendance',
        sa.Column('id', uuid_pk, primary_key=True, server_default=uuid_default),
        sa.Column('employee_id', uuid_fk, sa.ForeignKey('employees.id', ondelete='CASCADE'), nullable=False),
        sa.Column('attendance_date', sa.Date, nullable=False),
        sa.Column('check_in', sa.TIMESTAMP),
        sa.Column('check_out', sa.TIMESTAMP),
        sa.Column('total_work_minutes', sa.Integer, server_default='0'),
        sa.Column('attendance_status', sa.String(20)),
        sa.Column('late_minutes', sa.Integer, server_default='0'),
        sa.Column('early_exit_minutes', sa.Integer, server_default='0'),
        sa.Column('remarks', sa.Text),
        sa.Column('created_at', sa.TIMESTAMP, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.TIMESTAMP, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.UniqueConstraint('employee_id', 'attendance_date', name='uq_employee_attendance_date'),
    )
    op.create_index('idx_attendance_employee', 'attendance', ['employee_id'])
    op.create_index('idx_attendance_date', 'attendance', ['attendance_date'])

    op.create_table(
        'attendance_logs',
        sa.Column('id', uuid_pk, primary_key=True, server_default=uuid_default),
        sa.Column('employee_id', uuid_fk, sa.ForeignKey('employees.id', ondelete='SET NULL')),
        sa.Column('event_type', sa.String(20)),
        sa.Column('event_time', sa.TIMESTAMP, nullable=False),
        sa.Column('confidence_score', sa.Numeric(5, 2)),
        sa.Column('snapshot_url', sa.Text),
        sa.Column('recognition_status', sa.String(20)),
        sa.Column('created_at', sa.TIMESTAMP, server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    op.create_index('idx_attendance_logs_employee', 'attendance_logs', ['employee_id'])
    op.create_index('idx_attendance_logs_time', 'attendance_logs', ['event_time'])

    op.create_table(
        'unknown_face_events',
        sa.Column('id', uuid_pk, primary_key=True, server_default=uuid_default),
        sa.Column('snapshot_url', sa.Text),
        sa.Column('confidence_score', sa.Numeric(5, 2)),
        sa.Column('detected_at', sa.TIMESTAMP),
        sa.Column('reviewed', sa.Boolean, server_default='false'),
        sa.Column('notes', sa.Text),
    )

    op.create_table(
        'roles',
        sa.Column('id', uuid_pk, primary_key=True, server_default=uuid_default),
        sa.Column('role_name', sa.String(50), unique=True, nullable=False),
        sa.Column('description', sa.Text),
    )

    op.execute("""
        INSERT INTO roles (id, role_name, description) VALUES
        ('a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11'::uuid, 'SUPER_ADMIN', 'Full system access'),
        ('a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a12'::uuid, 'HR_ADMIN', 'Employee and attendance management'),
        ('a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a13'::uuid, 'VIEWER', 'Read-only access')
    """)

    op.create_table(
        'users',
        sa.Column('id', uuid_pk, primary_key=True, server_default=uuid_default),
        sa.Column('role_id', uuid_fk, sa.ForeignKey('roles.id')),
        sa.Column('full_name', sa.String(255)),
        sa.Column('email', sa.String(255), unique=True, nullable=False),
        sa.Column('password_hash', sa.Text, nullable=False),
        sa.Column('is_active', sa.Boolean, server_default='true'),
        sa.Column('last_login', sa.TIMESTAMP),
        sa.Column('created_at', sa.TIMESTAMP, server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    op.create_index('idx_users_email', 'users', ['email'])

    op.create_table(
        'audit_logs',
        sa.Column('id', uuid_pk, primary_key=True, server_default=uuid_default),
        sa.Column('user_id', uuid_fk, sa.ForeignKey('users.id', ondelete='SET NULL')),
        sa.Column('action', sa.String(255)),
        sa.Column('entity_name', sa.String(100)),
        sa.Column('entity_id', uuid_fk),
        sa.Column('old_value', postgresql.JSONB),
        sa.Column('new_value', postgresql.JSONB),
        sa.Column('created_at', sa.TIMESTAMP, server_default=sa.text('CURRENT_TIMESTAMP')),
    )

    op.create_table(
        'system_settings',
        sa.Column('id', uuid_pk, primary_key=True, server_default=uuid_default),
        sa.Column('setting_key', sa.String(255), unique=True),
        sa.Column('setting_value', sa.Text),
        sa.Column('description', sa.Text),
        sa.Column('updated_at', sa.TIMESTAMP, server_default=sa.text('CURRENT_TIMESTAMP')),
    )

    op.execute("""
        INSERT INTO system_settings (id, setting_key, setting_value, description) VALUES
        ('a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a21'::uuid, 'FACE_MATCH_THRESHOLD', '0.75', 'Face matching confidence threshold'),
        ('a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22'::uuid, 'ATTENDANCE_COOLDOWN_MINUTES', '5', 'Minimum minutes between attendance records'),
        ('a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a23'::uuid, 'CHECKIN_START_TIME', '08:00', 'Check-in window start time'),
        ('a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a24'::uuid, 'LATE_AFTER_TIME', '09:15', 'Time after which check-in is marked as late'),
        ('a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a25'::uuid, 'AUTO_CHECKOUT_TIME', '22:00', 'Automatic checkout time')
    """)

    op.create_table(
        'holidays',
        sa.Column('id', uuid_pk, primary_key=True, server_default=uuid_default),
        sa.Column('holiday_name', sa.String(255)),
        sa.Column('holiday_date', sa.Date),
        sa.Column('description', sa.Text),
        sa.Column('created_at', sa.TIMESTAMP, server_default=sa.text('CURRENT_TIMESTAMP')),
    )

    op.create_table(
        'leave_types',
        sa.Column('id', uuid_pk, primary_key=True, server_default=uuid_default),
        sa.Column('leave_name', sa.String(100)),
        sa.Column('is_paid', sa.Boolean, server_default='true'),
    )

    op.create_table(
        'report_exports',
        sa.Column('id', uuid_pk, primary_key=True, server_default=uuid_default),
        sa.Column('generated_by', uuid_fk, sa.ForeignKey('users.id', ondelete='SET NULL')),
        sa.Column('report_type', sa.String(50)),
        sa.Column('file_url', sa.Text),
        sa.Column('generated_at', sa.TIMESTAMP, server_default=sa.text('CURRENT_TIMESTAMP')),
    )

    op.create_table(
        'erp_configs',
        sa.Column('id', uuid_pk, primary_key=True, server_default=uuid_default),
        sa.Column('erp_name', sa.String(100), nullable=False, server_default='Custom ERP'),
        sa.Column('erp_url', sa.String(500), nullable=False),
        sa.Column('api_key', sa.String(200)),
        sa.Column('auth_type', sa.String(50), nullable=False, server_default='api_key'),
        sa.Column('data_format', sa.String(20), nullable=False, server_default='xml'),
        sa.Column('sync_enabled', sa.Boolean, server_default='true'),
        sa.Column('sync_interval_minutes', sa.Integer, server_default='15'),
        sa.Column('last_sync_at', sa.DateTime),
        sa.Column('last_sync_status', sa.String(50)),
        sa.Column('last_sync_message', sa.Text),
        sa.Column('endpoint_attendance', sa.String(500)),
        sa.Column('endpoint_employees', sa.String(500)),
        sa.Column('webhook_url', sa.String(500)),
        sa.Column('webhook_secret', sa.String(200)),
        sa.Column('webhook_enabled', sa.Boolean, server_default='false'),
        sa.Column('created_at', sa.DateTime, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime, server_default=sa.text('CURRENT_TIMESTAMP')),
    )

    op.create_table(
        'erp_sync_logs',
        sa.Column('id', uuid_pk, primary_key=True, server_default=uuid_default),
        sa.Column('erp_config_id', uuid_fk, sa.ForeignKey('erp_configs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('sync_type', sa.String(50), nullable=False),
        sa.Column('direction', sa.String(20), nullable=False, server_default='push'),
        sa.Column('status', sa.String(50), nullable=False, server_default='pending'),
        sa.Column('records_count', sa.Integer, server_default='0'),
        sa.Column('error_message', sa.Text),
        sa.Column('request_payload', sa.Text),
        sa.Column('response_payload', sa.Text),
        sa.Column('started_at', sa.DateTime, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('completed_at', sa.DateTime),
    )


def downgrade() -> None:
    op.drop_table('erp_sync_logs')
    op.drop_table('erp_configs')
    op.drop_table('report_exports')
    op.drop_table('leave_types')
    op.drop_table('holidays')
    op.drop_table('system_settings')
    op.drop_table('audit_logs')
    op.drop_table('users')
    op.drop_table('roles')
    op.drop_table('unknown_face_events')
    op.drop_index('idx_attendance_logs_time', table_name='attendance_logs')
    op.drop_index('idx_attendance_logs_employee', table_name='attendance_logs')
    op.drop_table('attendance_logs')
    op.drop_index('idx_attendance_date', table_name='attendance')
    op.drop_index('idx_attendance_employee', table_name='attendance')
    op.drop_table('attendance')
    op.drop_table('face_profiles')
    op.drop_index('idx_employee_mobile', table_name='employees')
    op.drop_index('idx_employee_code', table_name='employees')
    op.drop_table('employees')
    op.drop_table('departments')
