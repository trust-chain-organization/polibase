"""Value object for politician member data."""

from typing import TypedDict


class PoliticianMemberData(TypedDict, total=False):
    """Structured data for a politician member.

    This TypedDict defines the structure of politician data extracted
    from party member pages. Using TypedDict provides type safety and
    IDE autocomplete while maintaining dict compatibility.

    All fields are optional (total=False) since different sources
    may provide different fields.

    Attributes:
        name: Full name of the politician (required in practice)
        position: Political position (e.g., 衆議院議員, 市議会議員)
        electoral_district: Electoral district (e.g., 東京1区, 渋谷区)
        prefecture: Prefecture (e.g., 東京都, 北海道)
        profile_url: URL to politician's profile page
        party_position: Position within the party (e.g., 代表, 幹事長)
    """

    name: str
    position: str | None
    electoral_district: str | None
    prefecture: str | None
    profile_url: str | None
    party_position: str | None
