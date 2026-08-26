"""evaluation level to score

Revision ID: 002_evaluation_score
Revises: 001_initial_schema
Create Date: 2026-08-26

Pré-requisito: a tabela interview_turns deve estar vazia. Esta migration não faz
backfill de dados existentes — se houver turns, o upgrade aborta com erro.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "002_evaluation_score"
down_revision: str | None = "001_initial_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    conn = op.get_bind()
    result = conn.execute(sa.text("SELECT COUNT(*) FROM interview_turns"))
    count = result.scalar()
    if count and count > 0:
        raise RuntimeError(
            "Migration 002 abortada: interview_turns não está vazio "
            f"({count} registro(s)). Esta migration não faz backfill — "
            "esvazie a tabela ou migre os dados manualmente antes de continuar."
        )

    op.drop_column("interview_turns", "evaluation_level")
    op.add_column(
        "interview_turns",
        sa.Column("evaluation_score", sa.Integer(), nullable=False),
    )


def downgrade() -> None:
    op.drop_column("interview_turns", "evaluation_score")
    op.add_column(
        "interview_turns",
        sa.Column("evaluation_level", sa.String(length=16), nullable=False),
    )
