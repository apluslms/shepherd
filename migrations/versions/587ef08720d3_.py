"""empty message

Revision ID: 587ef08720d3
Revises: 48710c7a1511
Create Date: 2019-06-15 17:52:30.760011

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '587ef08720d3'
down_revision = '48710c7a1511'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('create_group_perm', schema=None) as batch_op:
        batch_op.drop_column('id')

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('create_group_perm', schema=None) as batch_op:
        batch_op.add_column(sa.Column('id', sa.INTEGER(), nullable=False))

    # ### end Alembic commands ###