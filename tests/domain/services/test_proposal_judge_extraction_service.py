"""Tests for ProposalJudgeExtractionService"""

from src.domain.services.proposal_judge_extraction_service import (
    ProposalJudgeExtractionService,
)


class TestProposalJudgeExtractionService:
    """Test ProposalJudgeExtractionService"""

    def test_normalize_judgment_type_japanese(self):
        """Test normalizing Japanese judgment types"""
        service = ProposalJudgeExtractionService()

        assert service.normalize_judgment_type("賛成") == ("賛成", True)
        assert service.normalize_judgment_type("反対") == ("反対", True)
        # 棄権と欠席はデフォルトで賛成になる
        assert service.normalize_judgment_type("棄権") == ("賛成", False)
        assert service.normalize_judgment_type("欠席") == ("賛成", False)

    def test_normalize_judgment_type_english(self):
        """Test normalizing English judgment types"""
        service = ProposalJudgeExtractionService()

        assert service.normalize_judgment_type("APPROVE") == ("賛成", True)
        assert service.normalize_judgment_type("OPPOSE") == ("反対", True)
        # ABSTAINとABSENTはデフォルトで賛成になる
        assert service.normalize_judgment_type("ABSTAIN") == ("賛成", False)
        assert service.normalize_judgment_type("ABSENT") == ("賛成", False)

    def test_normalize_judgment_type_symbols(self):
        """Test normalizing symbol judgment types"""
        service = ProposalJudgeExtractionService()

        assert service.normalize_judgment_type("○") == ("賛成", True)
        assert service.normalize_judgment_type("×") == ("反対", True)
        # ハイフンはデフォルトで賛成になる
        assert service.normalize_judgment_type("－") == ("賛成", False)

    def test_normalize_judgment_type_variations(self):
        """Test normalizing various judgment type variations"""
        service = ProposalJudgeExtractionService()

        assert service.normalize_judgment_type("YES") == ("賛成", True)
        assert service.normalize_judgment_type("NO") == ("反対", True)
        assert service.normalize_judgment_type("FOR") == ("賛成", True)
        assert service.normalize_judgment_type("AGAINST") == ("反対", True)

    def test_normalize_judgment_type_unknown(self):
        """Test normalizing unknown judgment type defaults to 賛成"""
        service = ProposalJudgeExtractionService()

        assert service.normalize_judgment_type("不明") == ("賛成", False)
        assert service.normalize_judgment_type("その他") == ("賛成", False)
        assert service.normalize_judgment_type("") == ("賛成", False)

    def test_normalize_politician_name(self):
        """Test normalizing politician names"""
        service = ProposalJudgeExtractionService()

        # Remove honorifics
        assert service.normalize_politician_name("山田太郎議員") == "山田太郎"
        assert service.normalize_politician_name("田中花子氏") == "田中花子"
        assert service.normalize_politician_name("佐藤一郎さん") == "佐藤一郎"
        assert service.normalize_politician_name("鈴木次郎君") == "鈴木次郎"
        assert service.normalize_politician_name("高橋三郎様") == "高橋三郎"

    def test_normalize_politician_name_with_titles(self):
        """Test normalizing politician names with titles"""
        service = ProposalJudgeExtractionService()

        assert service.normalize_politician_name("山田太郎委員長") == "山田太郎"
        assert service.normalize_politician_name("田中花子副委員長") == "田中花子"
        assert service.normalize_politician_name("佐藤一郎議長") == "佐藤一郎"
        assert service.normalize_politician_name("鈴木次郎副議長") == "鈴木次郎"
        assert service.normalize_politician_name("高橋三郎市長") == "高橋三郎"

    def test_normalize_politician_name_spaces(self):
        """Test normalizing spaces in politician names"""
        service = ProposalJudgeExtractionService()

        assert service.normalize_politician_name("山田　太郎") == "山田 太郎"
        assert service.normalize_politician_name("田中  花子") == "田中 花子"
        assert service.normalize_politician_name(" 佐藤一郎 ") == "佐藤一郎"

    def test_extract_party_from_text(self):
        """Test extracting party name from text"""
        service = ProposalJudgeExtractionService()

        assert service.extract_party_from_text("山田太郎（○○党）") == "○○党"
        assert service.extract_party_from_text("田中花子(△△党)") == "△△党"
        assert service.extract_party_from_text("佐藤一郎【××党】") == "××党"
        assert service.extract_party_from_text("鈴木次郎[□□党]") == "□□党"

    def test_extract_party_from_text_no_party(self):
        """Test extracting party name when no party is present"""
        service = ProposalJudgeExtractionService()

        assert service.extract_party_from_text("山田太郎") is None
        assert service.extract_party_from_text("田中花子議員") is None

    def test_extract_party_from_text_too_long(self):
        """Test that very long text in parentheses is not considered a party"""
        service = ProposalJudgeExtractionService()

        long_text = "山田太郎（これは非常に長いテキストで政党名ではありません）"
        assert service.extract_party_from_text(long_text) is None

    def test_parse_voting_result_text(self):
        """Test parsing voting result text"""
        service = ProposalJudgeExtractionService()

        text = """
        賛成者
        山田太郎、田中花子、佐藤一郎

        反対者
        鈴木次郎、高橋三郎

        棄権
        渡辺四郎
        """

        results = service.parse_voting_result_text(text)

        # 棄権者は無視されるため、5人になる
        assert len(results) == 5

        # Check for expected names and judgments
        names_judgments = {(r["name"], r["judgment"]) for r in results}
        assert ("山田太郎", "賛成") in names_judgments
        assert ("田中花子", "賛成") in names_judgments
        assert ("佐藤一郎", "賛成") in names_judgments
        assert ("鈴木次郎", "反対") in names_judgments
        assert ("高橋三郎", "反対") in names_judgments
        # 渡辺四郎は棄権のため含まれない

    def test_parse_voting_result_text_with_party(self):
        """Test parsing voting result text with party information"""
        service = ProposalJudgeExtractionService()

        text = """
        賛成議員
        山田太郎（○○党）、田中花子（△△党）

        反対議員
        佐藤一郎（××党）
        """

        results = service.parse_voting_result_text(text)

        assert len(results) == 3

        # Find specific results
        yamada = next((r for r in results if r["name"] == "山田太郎"), None)
        assert yamada is not None
        assert yamada["party"] == "○○党"
        assert yamada["judgment"] == "賛成"

        tanaka = next((r for r in results if r["name"] == "田中花子"), None)
        assert tanaka is not None
        assert tanaka["party"] == "△△党"
        assert tanaka["judgment"] == "賛成"

        sato = next((r for r in results if r["name"] == "佐藤一郎"), None)
        assert sato is not None
        assert sato["party"] == "××党"
        assert sato["judgment"] == "反対"

    def test_calculate_matching_confidence_exact_match(self):
        """Test calculating matching confidence for exact match"""
        service = ProposalJudgeExtractionService()

        confidence = service.calculate_matching_confidence("山田太郎", "山田太郎")
        assert confidence == 1.0

    def test_calculate_matching_confidence_with_honorifics(self):
        """Test calculating matching confidence with honorifics"""
        service = ProposalJudgeExtractionService()

        confidence = service.calculate_matching_confidence("山田太郎議員", "山田太郎")
        assert confidence == 1.0  # Should be 1.0 after normalization

    def test_calculate_matching_confidence_partial_match(self):
        """Test calculating matching confidence for partial match"""
        service = ProposalJudgeExtractionService()

        confidence = service.calculate_matching_confidence("山田太郎", "山田太郎次郎")
        assert confidence == 0.8  # One contains the other

    def test_calculate_matching_confidence_with_party_match(self):
        """Test calculating matching confidence with party match"""
        service = ProposalJudgeExtractionService()

        confidence = service.calculate_matching_confidence(
            "山田太郎", "山田太郎", "○○党", "○○党"
        )
        assert confidence == 1.0  # Exact match with same party

    def test_calculate_matching_confidence_with_party_mismatch(self):
        """Test calculating matching confidence with party mismatch"""
        service = ProposalJudgeExtractionService()

        confidence = service.calculate_matching_confidence(
            "山田太郎", "山田太郎", "○○党", "△△党"
        )
        assert confidence == 0.9  # Exact name match but different party

    def test_calculate_matching_confidence_no_match(self):
        """Test calculating matching confidence for no match"""
        service = ProposalJudgeExtractionService()

        confidence = service.calculate_matching_confidence("山田太郎", "鈴木次郎")
        assert confidence < 0.5

    def test_is_parliamentary_group(self):
        """Test identifying parliamentary group names"""
        service = ProposalJudgeExtractionService()

        assert service.is_parliamentary_group("○○会派") is True
        assert service.is_parliamentary_group("△△議員団") is True
        assert service.is_parliamentary_group("××クラブ") is True
        assert service.is_parliamentary_group("□□の会") is True
        assert service.is_parliamentary_group("市民グループ") is True
        assert service.is_parliamentary_group("議員連合") is True

    def test_is_parliamentary_group_individual(self):
        """Test that individual names are not identified as groups"""
        service = ProposalJudgeExtractionService()

        assert service.is_parliamentary_group("山田太郎") is False
        assert service.is_parliamentary_group("田中花子議員") is False

    def test_extract_members_from_group_text(self):
        """Test extracting member names from group text"""
        service = ProposalJudgeExtractionService()

        text = "○○会派 所属議員：山田太郎、田中花子、佐藤一郎"
        members = service.extract_members_from_group_text(text)

        assert len(members) == 3
        assert "山田太郎" in members
        assert "田中花子" in members
        assert "佐藤一郎" in members

    def test_extract_members_from_group_text_different_format(self):
        """Test extracting members with different format"""
        service = ProposalJudgeExtractionService()

        text = "△△議員団 メンバー：鈴木次郎議員、高橋三郎氏"
        members = service.extract_members_from_group_text(text)

        assert len(members) == 2
        assert "鈴木次郎" in members  # Honorific should be removed
        assert "高橋三郎" in members  # Honorific should be removed

    def test_extract_members_from_group_text_no_members(self):
        """Test extracting members when no member list is present"""
        service = ProposalJudgeExtractionService()

        text = "○○会派"
        members = service.extract_members_from_group_text(text)

        assert len(members) == 0
