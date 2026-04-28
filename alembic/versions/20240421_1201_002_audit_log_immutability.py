"""audit_log_immutability

Revision ID: 002
Revises: 001
Create Date: 2024-04-21 12:01:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Add database rules to enforce immutability on audit_logs table.
    
    These rules prevent UPDATE and DELETE operations at the database level,
    ensuring audit logs cannot be modified or deleted after creation.
    This is a critical security requirement for compliance and forensic integrity.
    """
    
    # Prevent UPDATE operations on audit_logs
    op.execute(
        """
        CREATE RULE audit_logs_no_update AS 
        ON UPDATE TO audit_logs 
        DO INSTEAD NOTHING
        """
    )
    
    # Prevent DELETE operations on audit_logs
    op.execute(
        """
        CREATE RULE audit_logs_no_delete AS 
        ON DELETE TO audit_logs 
        DO INSTEAD NOTHING
        """
    )
    
    # Add comment explaining the immutability enforcement
    op.execute(
        """
        COMMENT ON TABLE audit_logs IS 
        'Immutable audit log table. UPDATE and DELETE operations are blocked by database rules for compliance.'
        """
    )


def downgrade() -> None:
    """Remove immutability rules from audit_logs table"""
    
    # Drop the rules
    op.execute("DROP RULE IF EXISTS audit_logs_no_update ON audit_logs")
    op.execute("DROP RULE IF EXISTS audit_logs_no_delete ON audit_logs")
    
    # Remove comment
    op.execute("COMMENT ON TABLE audit_logs IS NULL")
