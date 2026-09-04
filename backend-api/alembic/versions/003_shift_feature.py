"""3 shift management + overtime: shifts table, employee.shift_id, attendance OT fields

Revision ID: 003
Revises: 002
Create Date: 2026-09-04

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = '003'
down_revision: Union[str, None] = '002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

uuid_pk = postgresql.UUID(as_uuid=True)
uuid_fk = postgresql.UUID(as_uuid=True)
uuid_default = sa.text('gen_random_uuid()')


def upgrade() -> None:
    op.create_table(
        'shifts',
        sa.Column('id', uuid_pk, primary_key=True, server_default=uuid_default),
        sa.Column('shift_name', sa.String(100), unique=True, nullable=False),
        sa.Column('start_time', sa.Time, nullable=False),
        sa.Column('end_time', sa.Time, nullable=False),
        sa.Column('standard_hours', sa.Numeric(6, 2), server_default='8.0'),
        sa.Column('grace_period', sa.Integer, server_default='0'),
        sa.Column('is_active', sa.Boolean, server_default='true'),
        sa.Column('created_at', sa.TIMESTAMP, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.TIMESTAMP, server_default=sa.text('CURRENT_TIMESTAMP')),
    )

    op.add_column(
        'employees',
        sa.Column('shift_id', uuid_fk, sa.ForeignKey('shifts.id')),
    )

    op.add_column('attendance', sa.Column('shift_id', uuid_fk, sa.ForeignKey('shifts.id')))
    op.add_column('attendance', sa.Column('scheduled_start', sa.Time))
    op.add_column('attendance', sa.Column('scheduled_end', sa.Time))
    op.add_column('attendance', sa.Column('normal_work_minutes', sa.Integer, server_default='0'))
    op.add_column('attendance', sa.Column('overtime_minutes', sa.Integer, server_default='0'))


def downgrade() -> None:
    op.drop_column('attendance', 'overtime_minutes')
    op.drop_column('attendance', 'normal_work_minutes')
    op.drop_column('attendance', 'scheduled_end')
    op.drop_column('attendance', 'scheduled_start')
    op.drop_column('attendance', 'shift_id')
    op.drop_column('employees', 'shift_id')
    op.drop_table('shifts')
