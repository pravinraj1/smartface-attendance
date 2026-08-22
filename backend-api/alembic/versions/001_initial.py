"""initial migration

Revision ID: 001
Revises: 
Create Date: 2026-08-19

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'departments',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(100), unique=True, nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('created_at', sa.TIMESTAMP, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.TIMESTAMP, server_default=sa.text('CURRENT_TIMESTAMP')),
    )

    op.create_table(
        'employees',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('employee_code', sa.String(50), unique=True, nullable=False),
        sa.Column('full_name', sa.String(255), nullable=False),
        sa.Column('mobile_number', sa.String(20), unique=True),
        sa.Column('department_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('departments.id')),
        sa.Column('monthly_salary', sa.Numeric(12, 2)),
        sa.Column('joining_date', sa.Date),
        sa.Column('employment_status', sa.String(20), default='ACTIVE'),
        sa.Column('face_enrolled', sa.Boolean, default=False),
        sa.Column('notes', sa.Text),
        sa.Column('created_at', sa.TIMESTAMP, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.TIMESTAMP, server_default=sa.text('CURRENT_TIMESTAMP')),
    )

    op.create_index('idx_employee_code', 'employees', ['employee_code'])
    op.create_index('idx_employee_mobile', 'employees', ['mobile_number'])

    op.create_table(
        'face_profiles',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('employee_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('employees.id'), nullable=False),
        sa.Column('face_image_url', sa.Text, nullable=False),
        sa.Column('qdrant_vector_id', sa.String(255)),
        sa.Column('embedding_version', sa.String(50)),
        sa.Column('enrollment_quality_score', sa.Numeric(5, 2)),
        sa.Column('is_primary', sa.Boolean, default=True),
        sa.Column('created_at', sa.TIMESTAMP, server_default=sa.text('CURRENT_TIMESTAMP')),
    )

    op.create_table(
        'attendance',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('employee_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('employees.id'), nullable=False),
        sa.Column('attendance_date', sa.Date, nullable=False),
        sa.Column('check_in', sa.TIMESTAMP),
        sa.Column('check_out', sa.TIMESTAMP),
        sa.Column('total_work_minutes', sa.Integer, default=0),
        sa.Column('attendance_status', sa.String(20)),
        sa.Column('late_minutes', sa.Integer, default=0),
        sa.Column('early_exit_minutes', sa.Integer, default=0),
        sa.Column('remarks', sa.Text),
        sa.Column('created_at', sa.TIMESTAMP, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.TIMESTAMP, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.UniqueConstraint('employee_id', 'attendance_date', name='uq_employee_attendance_date'),
    )

    op.create_index('idx_attendance_employee', 'attendance', ['employee_id'])
    op.create_index('idx_attendance_date', 'attendance', ['attendance_date'])

    op.create_table(
        'attendance_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('employee_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('employees.id')),
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
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('snapshot_url', sa.Text),
        sa.Column('confidence_score', sa.Numeric(5, 2)),
        sa.Column('detected_at', sa.TIMESTAMP),
        sa.Column('reviewed', sa.Boolean, default=False),
        sa.Column('notes', sa.Text),
    )

    op.create_table(
        'roles',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('role_name', sa.String(50), unique=True, nullable=False),
        sa.Column('description', sa.Text),
    )

    op.execute("""
        INSERT INTO roles (id, role_name, description) VALUES
        ('a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', 'SUPER_ADMIN', 'Full system access'),
        ('a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a12', 'HR_ADMIN', 'Employee and attendance management'),
        ('a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a13', 'VIEWER', 'Read-only access')
    """)

    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('role_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('roles.id')),
        sa.Column('full_name', sa.String(255)),
        sa.Column('email', sa.String(255), unique=True, nullable=False),
        sa.Column('password_hash', sa.Text, nullable=False),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('last_login', sa.TIMESTAMP),
        sa.Column('created_at', sa.TIMESTAMP, server_default=sa.text('CURRENT_TIMESTAMP')),
    )

    op.create_index('idx_users_email', 'users', ['email'])

    op.create_table(
        'audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id')),
        sa.Column('action', sa.String(255)),
        sa.Column('entity_name', sa.String(100)),
        sa.Column('entity_id', postgresql.UUID(as_uuid=True)),
        sa.Column('old_value', postgresql.JSONB),
        sa.Column('new_value', postgresql.JSONB),
        sa.Column('created_at', sa.TIMESTAMP, server_default=sa.text('CURRENT_TIMESTAMP')),
    )

    op.create_table(
        'system_settings',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('setting_key', sa.String(255), unique=True),
        sa.Column('setting_value', sa.Text),
        sa.Column('description', sa.Text),
        sa.Column('updated_at', sa.TIMESTAMP, server_default=sa.text('CURRENT_TIMESTAMP')),
    )

    op.execute("""
        INSERT INTO system_settings (setting_key, setting_value, description) VALUES
        ('FACE_MATCH_THRESHOLD', '0.75', 'Face matching confidence threshold'),
        ('ATTENDANCE_COOLDOWN_MINUTES', '5', 'Minimum minutes between attendance records'),
        ('CHECKIN_START_TIME', '08:00', 'Check-in window start time'),
        ('LATE_AFTER_TIME', '09:15', 'Time after which check-in is marked as late'),
        ('AUTO_CHECKOUT_TIME', '22:00', 'Automatic checkout time')
    """)

    op.create_table(
        'holidays',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('holiday_name', sa.String(255)),
        sa.Column('holiday_date', sa.Date),
        sa.Column('description', sa.Text),
        sa.Column('created_at', sa.TIMESTAMP, server_default=sa.text('CURRENT_TIMESTAMP')),
    )

    op.create_table(
        'leave_types',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('leave_name', sa.String(100)),
        sa.Column('is_paid', sa.Boolean, default=True),
    )

    op.create_table(
        'report_exports',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('generated_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id')),
        sa.Column('report_type', sa.String(50)),
        sa.Column('file_url', sa.Text),
        sa.Column('generated_at', sa.TIMESTAMP, server_default=sa.text('CURRENT_TIMESTAMP')),
    )


def downgrade() -> None:
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
