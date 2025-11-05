"""Data loader for BI Dashboard POC.

This module handles data retrieval from PostgreSQL database.
"""

import os
from typing import Any

import pandas as pd
from sqlalchemy import create_engine, text


def get_database_url() -> str:
    """Get database URL from environment variable.

    Returns:
        str: Database connection URL
    """
    return os.getenv(
        "DATABASE_URL", "postgresql://polibase:polibase@localhost:5432/polibase"
    )


def load_governing_bodies_coverage() -> pd.DataFrame:
    """Load governing bodies data with coverage information.

    Returns:
        pd.DataFrame: DataFrame with columns:
            - id: Governing body ID
            - name: Governing body name
            - organization_type: Type (国/都道府県/市町村)
            - prefecture: Prefecture name (extracted from name)
            - has_data: Whether we have data for this body
    """
    engine = create_engine(get_database_url())

    query = text("""
        SELECT
            gb.id,
            gb.name,
            gb.organization_type,
            CASE
                WHEN gb.name ~ '^(北海道|.*[都道府県])' THEN
                    SUBSTRING(gb.name FROM '^(北海道|.*?[都道府県])')
                ELSE
                    '不明'
            END as prefecture,
            CASE
                WHEN COUNT(m.id) > 0 THEN true
                ELSE false
            END as has_data
        FROM governing_bodies gb
        LEFT JOIN conferences c ON gb.id = c.governing_body_id
        LEFT JOIN meetings m ON c.id = m.conference_id
        GROUP BY gb.id, gb.name, gb.organization_type
        ORDER BY gb.organization_type, prefecture, gb.name
    """)

    with engine.connect() as conn:
        df = pd.read_sql_query(query, conn)

    return df


def get_coverage_stats() -> dict[str, Any]:
    """Get coverage statistics.

    Returns:
        dict: Statistics including:
            - total: Total number of governing bodies
            - covered: Number with data
            - coverage_rate: Percentage covered
            - by_type: Coverage by organization type
    """
    df = load_governing_bodies_coverage()

    total = len(df)
    covered = df["has_data"].sum()
    coverage_rate = (covered / total * 100) if total > 0 else 0

    by_type = (
        df.groupby("organization_type")
        .agg({"id": "count", "has_data": "sum"})
        .rename(columns={"id": "total", "has_data": "covered"})
    )
    by_type["coverage_rate"] = by_type["covered"] / by_type["total"] * 100

    return {
        "total": total,
        "covered": int(covered),
        "coverage_rate": round(coverage_rate, 2),
        "by_type": by_type.to_dict("index"),
    }


def get_prefecture_coverage() -> pd.DataFrame:
    """Get coverage by prefecture.

    Returns:
        pd.DataFrame: Coverage statistics by prefecture
    """
    df = load_governing_bodies_coverage()

    # Filter only municipalities (市町村)
    municipalities = df[df["organization_type"] == "市町村"]

    coverage = (
        municipalities.groupby("prefecture")
        .agg({"id": "count", "has_data": "sum"})
        .rename(columns={"id": "total", "has_data": "covered"})
    )

    coverage["coverage_rate"] = coverage["covered"] / coverage["total"] * 100
    coverage = coverage.sort_values("coverage_rate", ascending=False)

    return coverage.reset_index()
