"""Add story models

Revision ID: f3f986ec672c
Revises: ac8309a015f1
Create Date: 2025-06-18 20:23:44.294537

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f3f986ec672c'
down_revision = 'ac8309a015f1'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('story_like', schema=None) as batch_op:
        batch_op.add_column(sa.Column('timestamp', sa.DateTime(), nullable=True))
        batch_op.alter_column('story_id',
               existing_type=sa.INTEGER(),
               nullable=False)
        batch_op.alter_column('user_id',
               existing_type=sa.INTEGER(),
               nullable=False)

    with op.batch_alter_table('story_view', schema=None) as batch_op:
        batch_op.add_column(sa.Column('timestamp', sa.DateTime(), nullable=True))
        batch_op.alter_column('story_id',
               existing_type=sa.INTEGER(),
               nullable=False)
        batch_op.alter_column('user_id',
               existing_type=sa.INTEGER(),
               nullable=False)

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('story_view', schema=None) as batch_op:
        batch_op.alter_column('user_id',
               existing_type=sa.INTEGER(),
               nullable=True)
        batch_op.alter_column('story_id',
               existing_type=sa.INTEGER(),
               nullable=True)
        batch_op.drop_column('timestamp')

    with op.batch_alter_table('story_like', schema=None) as batch_op:
        batch_op.alter_column('user_id',
               existing_type=sa.INTEGER(),
               nullable=True)
        batch_op.alter_column('story_id',
               existing_type=sa.INTEGER(),
               nullable=True)
        batch_op.drop_column('timestamp')

    # ### end Alembic commands ###
