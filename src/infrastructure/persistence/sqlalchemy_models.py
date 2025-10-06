"""SQLAlchemy ORM models for database tables.

This module contains proper SQLAlchemy declarative models for tables that
previously used Pydantic models or dummy dynamic models. This allows the
repository pattern to use ORM features instead of raw SQL.
"""

from datetime import date, datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""

    pass


class ParliamentaryGroupMembershipModel(Base):
    """SQLAlchemy model for parliamentary_group_memberships table."""

    __tablename__ = "parliamentary_group_memberships"

    id: Mapped[int] = mapped_column(primary_key=True)
    politician_id: Mapped[int] = mapped_column(ForeignKey("politicians.id"))
    parliamentary_group_id: Mapped[int] = mapped_column(
        ForeignKey("parliamentary_groups.id")
    )
    start_date: Mapped[date] = mapped_column()
    end_date: Mapped[date | None] = mapped_column()
    role: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    __table_args__ = (
        CheckConstraint(
            "end_date IS NULL OR end_date >= start_date",
            name="chk_membership_end_date_after_start",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<ParliamentaryGroupMembershipModel("
            f"id={self.id}, "
            f"politician_id={self.politician_id}, "
            f"parliamentary_group_id={self.parliamentary_group_id}, "
            f"start_date={self.start_date}, "
            f"end_date={self.end_date}"
            f")>"
        )


class ExtractedParliamentaryGroupMemberModel(Base):
    """SQLAlchemy model for extracted_parliamentary_group_members table."""

    __tablename__ = "extracted_parliamentary_group_members"

    id: Mapped[int] = mapped_column(primary_key=True)
    parliamentary_group_id: Mapped[int] = mapped_column(
        ForeignKey("parliamentary_groups.id")
    )
    extracted_name: Mapped[str] = mapped_column(String(200))
    source_url: Mapped[str] = mapped_column(String(500))
    extracted_role: Mapped[str | None] = mapped_column(String(100))
    extracted_party_name: Mapped[str | None] = mapped_column(String(200))
    extracted_district: Mapped[str | None] = mapped_column(String(200))
    extracted_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    matched_politician_id: Mapped[int | None] = mapped_column(
        ForeignKey("politicians.id")
    )
    matching_confidence: Mapped[float | None] = mapped_column()  # 0.0-1.0
    matching_status: Mapped[str] = mapped_column(String(20), default="pending")
    matched_at: Mapped[datetime | None] = mapped_column(DateTime)
    additional_info: Mapped[str | None] = mapped_column(String(1000))

    def __repr__(self) -> str:
        return (
            f"<ExtractedParliamentaryGroupMemberModel("
            f"id={self.id}, "
            f"extracted_name={self.extracted_name}, "
            f"matching_status={self.matching_status}"
            f")>"
        )
