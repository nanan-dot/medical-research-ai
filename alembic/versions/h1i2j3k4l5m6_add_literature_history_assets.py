"""add literature strategy assets

Revision ID: h1i2j3k4l5m6
Revises: g0b1c2d3e4f5
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision:str="h1i2j3k4l5m6";down_revision:str|None="g0b1c2d3e4f5";branch_labels:str|Sequence[str]|None=None;depends_on:str|Sequence[str]|None=None
def upgrade()->None:
    op.create_table("literature_search_strategies",sa.Column("id",sa.Integer(),primary_key=True),sa.Column("name",sa.String(300),nullable=False),sa.Column("research_context_id",sa.Integer(),sa.ForeignKey("research_contexts.id",ondelete="SET NULL")),sa.Column("framework",sa.String(32),nullable=False,server_default="topic"),sa.Column("database",sa.String(32),nullable=False,server_default="pubmed"),sa.Column("is_pinned",sa.Boolean(),nullable=False,server_default=sa.false()),sa.Column("is_archived",sa.Boolean(),nullable=False,server_default=sa.false()),sa.Column("copied_from_strategy_id",sa.Integer(),sa.ForeignKey("literature_search_strategies.id",ondelete="SET NULL")),sa.Column("created_at",sa.DateTime(timezone=True),nullable=False,server_default=sa.text("CURRENT_TIMESTAMP")),sa.Column("updated_at",sa.DateTime(timezone=True),nullable=False,server_default=sa.text("CURRENT_TIMESTAMP")),sa.Column("archived_at",sa.DateTime(timezone=True)))
    op.create_index("ix_literature_search_strategies_research_context_id","literature_search_strategies",["research_context_id"])
    op.create_table("literature_search_strategy_versions",sa.Column("id",sa.Integer(),primary_key=True),sa.Column("strategy_id",sa.Integer(),sa.ForeignKey("literature_search_strategies.id",ondelete="CASCADE"),nullable=False),sa.Column("version",sa.Integer(),nullable=False),sa.Column("original_query",sa.Text(),nullable=False),sa.Column("structured_query",sa.Text(),nullable=False),sa.Column("search_string",sa.Text(),nullable=False),sa.Column("filters",sa.Text(),nullable=False),sa.Column("model_version",sa.String(200),nullable=False),sa.Column("user_edits",sa.Text(),nullable=False),sa.Column("term_groups_json",sa.Text(),nullable=False),sa.Column("mesh_terms_json",sa.Text(),nullable=False),sa.Column("start_year",sa.Integer()),sa.Column("end_year",sa.Integer()),sa.Column("change_summary_json",sa.Text(),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),nullable=False,server_default=sa.text("CURRENT_TIMESTAMP")),sa.UniqueConstraint("strategy_id","version",name="uq_literature_strategy_version"))
    op.create_index("ix_literature_search_strategy_versions_strategy_id","literature_search_strategy_versions",["strategy_id"])
    op.create_table("literature_search_executions",sa.Column("id",sa.Integer(),primary_key=True),sa.Column("strategy_version_id",sa.Integer(),sa.ForeignKey("literature_search_strategy_versions.id",ondelete="CASCADE"),nullable=False),sa.Column("result_id",sa.Integer(),sa.ForeignKey("literature_search_results.id",ondelete="SET NULL")),sa.Column("status",sa.String(32),nullable=False),sa.Column("requested_retmax",sa.Integer(),nullable=False),sa.Column("result_count",sa.Integer(),nullable=False),sa.Column("error_message",sa.Text()),sa.Column("created_at",sa.DateTime(timezone=True),nullable=False,server_default=sa.text("CURRENT_TIMESTAMP")),sa.Column("completed_at",sa.DateTime(timezone=True)))
    op.create_index("ix_literature_search_executions_strategy_version_id","literature_search_executions",["strategy_version_id"])
    # 历史任务只能可靠恢复成一个初始修订；无法证明的术语分类和年份保持未知。
    op.execute("INSERT INTO literature_search_strategies (id,name,research_context_id,framework,database,is_pinned,is_archived,created_at,updated_at) SELECT id,original_query,research_context_id,'topic',database,0,0,created_at,COALESCE(searched_at,created_at) FROM literature_search_tasks")
    op.execute("INSERT INTO literature_search_strategy_versions (strategy_id,version,original_query,structured_query,search_string,filters,model_version,user_edits,term_groups_json,mesh_terms_json,change_summary_json,created_at) SELECT id,1,original_query,structured_query,search_string,filters,model_version,user_edits,'[]','[]','{}',created_at FROM literature_search_tasks")
    op.execute("INSERT INTO literature_search_executions (strategy_version_id,result_id,status,requested_retmax,result_count,created_at,completed_at) SELECT v.id,tr.result_id,'succeeded',t.retmax,r.total_count,tr.created_at,tr.created_at FROM literature_search_task_results tr JOIN literature_search_tasks t ON t.id=tr.task_id JOIN literature_search_strategy_versions v ON v.strategy_id=t.id AND v.version=1 JOIN literature_search_results r ON r.id=tr.result_id")
def downgrade()->None:
    op.drop_table("literature_search_executions");op.drop_table("literature_search_strategy_versions");op.drop_table("literature_search_strategies")

