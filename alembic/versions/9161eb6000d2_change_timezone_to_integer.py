"""change_timezone_to_integer

Revision ID: 9161eb6000d2
Revises: abecc739e7a6
Create Date: 2025-05-05 11:26:33.929681

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9161eb6000d2'
down_revision: Union[str, None] = 'abecc739e7a6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
