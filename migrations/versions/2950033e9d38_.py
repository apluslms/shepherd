"""empty message

Revision ID: 2950033e9d38
Revises: dacff8c1eeed
Create Date: 2019-06-15 17:15:42.149958

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2950033e9d38'
down_revision = 'dacff8c1eeed'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('create_group_perm', schema=None) as batch_op:
        batch_op.drop_constraint('fk_create_group_perm_group_id_group', type_='foreignkey')

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('create_group_perm', schema=None) as batch_op:
        batch_op.create_foreign_key('fk_create_group_perm_group_id_group', 'group', ['group_id', 'target_group_id'], ['id', 'id'])

    # ### end Alembic commands ###
