"""add sms table

Revision ID: xxx
Revises: xxx
Create Date: 2024-xx-xx

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'xxx'
down_revision = 'xxx'  # Update with your latest revision
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'sms',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('phone_number', sa.String(), nullable=False),
        sa.Column('raw_message', sa.Text(), nullable=True),
        sa.Column('received_at', sa.DateTime(), nullable=False),
        sa.Column('parsed_at', sa.DateTime(), nullable=True),
        sa.Column('parsing_status', sa.Enum('pending', 'parsed', 'failed', 'remote_parsing', name='parsingstatus'), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('remote_parse_requested', sa.Boolean(), default=False),
        sa.Column('amount', sa.Float(), nullable=True),
        sa.Column('transaction_type', sa.Enum('debit', 'credit', 'unknown', name='transactiontype'), nullable=True),
        sa.Column('merchant', sa.String(), nullable=True),
        sa.Column('account_last4', sa.String(), nullable=True),
        sa.Column('transaction_date', sa.DateTime(), nullable=True),
        sa.Column('balance', sa.Float(), nullable=True),
        sa.Column('category', sa.String(), nullable=True),
        sa.Column('confidence', sa.Float(), default=0.0),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_sms_id'), 'sms', ['id'])
    op.create_index(op.f('ix_sms_user_id'), 'sms', ['user_id'])


def upgrade():
    op.drop_index(op.f('ix_sms_user_id'), table_name='sms')
    op.drop_index(op.f('ix_sms_id'), table_name='sms')
    op.drop_table('sms')

