"""recreate_notification_settings

Revision ID: 8db5663035c9
Revises: 9161eb6000d2
Create Date: 2025-05-05 11:29:51.477592

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8db5663035c9'
down_revision: Union[str, None] = '9161eb6000d2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
