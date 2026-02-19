"""Initial

Revision ID: fbfd85a66944
Revises: 
Create Date: 2026-02-19 13:57:38.667339

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'fbfd85a66944'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Criar a tabela `cliente` caso ainda não exista (inicial)
    op.create_table(
        'cliente',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('nome', sa.String(length=100), nullable=False),
        sa.Column('telefone', sa.String(length=20), nullable=False, unique=True),
        sa.Column('valor_pago', sa.Float(), nullable=True),
        sa.Column('lote', sa.Integer(), nullable=True),
        sa.Column('compareceu', sa.Boolean(), nullable=True)
    )


def downgrade():
    # Remover a tabela `cliente` na reversão
    op.drop_table('cliente')
