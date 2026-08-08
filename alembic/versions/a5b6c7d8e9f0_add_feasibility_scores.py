"""add feasibility score snapshots"""
from alembic import op
import sqlalchemy as sa
revision="a5b6c7d8e9f0"; down_revision="a3d4e5f6a7b8"; branch_labels=None; depends_on=None
def upgrade()->None:
 op.create_table("feasibility_scores",sa.Column("id",sa.Integer(),primary_key=True),sa.Column("direction_id",sa.Integer(),sa.ForeignKey("research_directions.id"),nullable=False),sa.Column("version",sa.Integer(),nullable=False),sa.Column("dimensions_json",sa.Text(),nullable=False),sa.Column("weights_json",sa.Text(),nullable=False),sa.Column("total_score",sa.Float(),nullable=False),sa.Column("confidence",sa.String(16),nullable=False),sa.Column("missing_inputs_json",sa.Text(),nullable=False),sa.Column("ranking_sensitive",sa.Boolean(),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),nullable=False,server_default=sa.text("CURRENT_TIMESTAMP")),sa.UniqueConstraint("direction_id","version",name="uq_feasibility_score_version")); op.create_index("ix_feasibility_scores_direction_id","feasibility_scores",["direction_id"])
def downgrade()->None:
 op.drop_index("ix_feasibility_scores_direction_id",table_name="feasibility_scores"); op.drop_table("feasibility_scores")
