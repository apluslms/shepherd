"""empty message

Revision ID: 48710c7a1511
Revises: 2950033e9d38
Create Date: 2019-06-15 17:16:49.279668

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '48710c7a1511'
down_revision = '2950033e9d38'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('create_group_perm', schema=None) as batch_op:
        batch_op.create_foreign_key(batch_op.f('fk_create_group_perm_group_id_group'), 'group', ['group_id'], ['id'])

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('create_group_perm', schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f('fk_create_group_perm_group_id_group'), type_='foreignkey')

    # ### end Alembic commands ###
