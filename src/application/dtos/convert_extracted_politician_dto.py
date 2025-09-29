from dataclasses import dataclass


@dataclass
class ConvertExtractedPoliticianInputDTO:
    """変換対象の抽出済み政治家を指定する入力DTO"""

    party_id: int | None = None
    batch_size: int = 100
    dry_run: bool = False


@dataclass
class ConvertedPoliticianDTO:
    """変換された政治家情報を表すDTO"""

    politician_id: int
    name: str
    party_id: int | None
    district: str | None
    profile_url: str | None


@dataclass
class ConvertExtractedPoliticianOutputDTO:
    """変換結果を表す出力DTO"""

    total_processed: int
    converted_count: int
    skipped_count: int
    error_count: int
    converted_politicians: list[ConvertedPoliticianDTO]
    skipped_names: list[str]
    error_messages: list[str]
