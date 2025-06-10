"""Tests for conference member matching service"""

from unittest.mock import Mock, patch

import pytest

from src.conference_member_extractor.matching_service import (
    ConferenceMemberMatchingService,
)


class TestConferenceMemberMatchingService:
    """Test cases for ConferenceMemberMatchingService"""

    @pytest.fixture
    def mock_llm_service(self):
        """Create a mock LLM service"""
        llm_service = Mock()
        llm_service.llm = Mock()
        return llm_service

    @pytest.fixture
    def mock_extracted_repo(self):
        """Create a mock extracted member repository"""
        repo = Mock()
        repo.get_pending_members = Mock()
        repo.update_matching_result = Mock()
        return repo

    @pytest.fixture
    def mock_politician_repo(self):
        """Create a mock politician repository"""
        repo = Mock()
        repo.search_by_name = Mock()
        return repo

    @pytest.fixture
    def mock_affiliation_repo(self):
        """Create a mock affiliation repository"""
        repo = Mock()
        return repo

    @pytest.fixture
    def service(
        self,
        mock_llm_service,
        mock_extracted_repo,
        mock_politician_repo,
        mock_affiliation_repo,
    ):
        """Create a ConferenceMemberMatchingService instance"""
        with patch(
            "src.conference_member_extractor.matching_service.ExtractedConferenceMemberRepository",
            return_value=mock_extracted_repo,
        ):
            with patch(
                "src.conference_member_extractor.matching_service.PoliticianRepository",
                return_value=mock_politician_repo,
            ):
                with patch(
                    "src.conference_member_extractor.matching_service.LLMService",
                    return_value=mock_llm_service,
                ):
                    with patch(
                        "src.conference_member_extractor.matching_service.PoliticianAffiliationRepository",
                        return_value=mock_affiliation_repo,
                    ):
                        return ConferenceMemberMatchingService()

    def test_find_politician_candidates_exact_match_with_party(
        self, service, mock_politician_repo
    ):
        """Test finding candidates with exact name and party match"""
        # Setup
        mock_politician_repo.search_by_name.return_value = [
            {"id": 100, "name": "山田太郎", "party_name": "自民党"},
            {"id": 101, "name": "山田太郎", "party_name": "立憲民主党"},
        ]

        # Execute
        result = service.find_politician_candidates("山田太郎", "自民党")

        # Assert - should return only party matching candidate
        assert len(result) == 1
        assert result[0]["id"] == 100
        assert result[0]["party_name"] == "自民党"

    def test_find_politician_candidates_exact_match_no_party(
        self, service, mock_politician_repo
    ):
        """Test finding candidates with exact name match but no party info"""
        # Setup
        mock_politician_repo.search_by_name.return_value = [
            {"id": 100, "name": "山田太郎", "party_name": "自民党"},
            {
                "id": 101,
                "name": "山田太郎次",  # Partial match
                "party_name": "立憲民主党",
            },
        ]

        # Execute
        result = service.find_politician_candidates("山田太郎", None)

        # Assert - should return exact match only
        assert len(result) == 1
        assert result[0]["id"] == 100

    def test_find_politician_candidates_partial_matches(
        self, service, mock_politician_repo
    ):
        """Test finding candidates with partial matches only"""
        # Setup
        mock_politician_repo.search_by_name.return_value = [
            {"id": 100, "name": "山田太郎次", "party_name": "自民党"},
            {"id": 101, "name": "山田太郎三", "party_name": "立憲民主党"},
        ]

        # Execute
        result = service.find_politician_candidates("山田太郎", None)

        # Assert - should return up to 5 candidates
        assert len(result) == 2
        assert result[0]["id"] == 100

    def test_match_with_llm_single_candidate_with_party_match(self, service):
        """Test LLM matching with single candidate and matching party"""
        # Setup
        member = {
            "id": 1,
            "extracted_name": "山田太郎",
            "extracted_party_name": "自民党",
        }
        candidates = [{"id": 100, "name": "山田太郎", "party_name": "自民党"}]

        # Execute
        politician_id, confidence = service.match_with_llm(member, candidates)

        # Assert
        assert politician_id == 100
        assert confidence == 0.95

    def test_match_with_llm_multiple_candidates(self, service, mock_llm_service):
        """Test LLM matching with multiple candidates"""
        # Setup
        member = {
            "id": 1,
            "extracted_name": "山田議員",
            "extracted_party_name": "自民党",
            "extracted_role": "委員長",
        }
        candidates = [
            {"id": 100, "name": "山田太郎", "party_name": "自民党"},
            {"id": 101, "name": "山田花子", "party_name": "立憲民主党"},
        ]

        # Mock LLM response
        mock_response = Mock()
        mock_response.content = """番号: 1
信頼度: 0.85
理由: 名前の一部と政党が一致"""
        mock_llm_service.llm.invoke.return_value = mock_response

        # Execute
        politician_id, confidence = service.match_with_llm(member, candidates)

        # Assert
        assert politician_id == 100
        assert confidence == 0.85

    def test_match_with_llm_no_match(self, service, mock_llm_service):
        """Test LLM matching with no match"""
        # Setup
        member = {"id": 1, "extracted_name": "不明な議員", "extracted_party_name": None}
        candidates = [{"id": 100, "name": "山田太郎", "party_name": "自民党"}]

        # Mock LLM response with no match
        mock_response = Mock()
        mock_response.content = """番号: 0
信頼度: 0.0
理由: 該当なし"""
        mock_llm_service.llm.invoke.return_value = mock_response

        # Execute
        politician_id, confidence = service.match_with_llm(member, candidates)

        # Assert
        assert politician_id is None
        assert confidence == 0.0

    def test_process_extracted_member_matched(
        self, service, mock_politician_repo, mock_extracted_repo, mock_llm_service
    ):
        """Test processing member with successful match"""
        # Setup
        member = {
            "id": 1,
            "extracted_name": "山田太郎",
            "extracted_party_name": "自民党",
        }

        mock_politician_repo.search_by_name.return_value = [
            {"id": 100, "name": "山田太郎", "party_name": "自民党"}
        ]

        # Execute
        result = service.process_extracted_member(member)

        # Assert
        assert result["status"] == "matched"
        assert result["politician_id"] == 100
        assert result["confidence"] == 0.95
        mock_extracted_repo.update_matching_result.assert_called_once_with(
            member_id=1,
            matched_politician_id=100,
            matching_confidence=0.95,
            matching_status="matched",
        )

    def test_process_extracted_member_needs_review(
        self, service, mock_politician_repo, mock_extracted_repo, mock_llm_service
    ):
        """Test processing member that needs review"""
        # Setup
        member = {
            "id": 1,
            "extracted_name": "山田太郎",
            "extracted_party_name": "自民党",
        }

        mock_politician_repo.search_by_name.return_value = [
            {
                "id": 100,
                "name": "山田太郎",
                "party_name": "立憲民主党",
            },  # Different party
            {"id": 101, "name": "山田太郎", "party_name": "公明党"},
        ]

        # Mock LLM response with medium confidence
        mock_response = Mock()
        mock_response.content = """番号: 1
信頼度: 0.6
理由: 名前は一致するが政党が異なる"""
        mock_llm_service.llm.invoke.return_value = mock_response

        # Execute
        result = service.process_extracted_member(member)

        # Assert
        assert result["status"] == "needs_review"
        assert result["politician_id"] == 100
        assert result["confidence"] == 0.6
        mock_extracted_repo.update_matching_result.assert_called_once_with(
            member_id=1,
            matched_politician_id=100,
            matching_confidence=0.6,
            matching_status="needs_review",
        )

    def test_process_extracted_member_no_match(
        self, service, mock_politician_repo, mock_extracted_repo
    ):
        """Test processing member with no match"""
        # Setup
        member = {
            "id": 1,
            "extracted_name": "山田太郎",
            "extracted_party_name": "自民党",
        }

        mock_politician_repo.search_by_name.return_value = []  # No candidates

        # Execute
        result = service.process_extracted_member(member)

        # Assert
        assert result["status"] == "no_match"
        assert result["politician_id"] is None
        assert result["confidence"] == 0.0
        mock_extracted_repo.update_matching_result.assert_called_once_with(
            member_id=1,
            matched_politician_id=None,
            matching_confidence=0.0,
            matching_status="no_match",
        )

    def test_process_pending_members(
        self, service, mock_extracted_repo, mock_politician_repo
    ):
        """Test processing multiple pending members"""
        # Setup
        mock_extracted_repo.get_pending_members.return_value = [
            {"id": 1, "extracted_name": "山田太郎", "extracted_party_name": "自民党"},
            {
                "id": 2,
                "extracted_name": "田中花子",
                "extracted_party_name": "立憲民主党",
            },
            {"id": 3, "extracted_name": "佐藤次郎", "extracted_party_name": None},
        ]

        # Mock different search results
        def search_by_name_side_effect(name):
            if name == "山田太郎":
                return [{"id": 100, "name": "山田太郎", "party_name": "自民党"}]
            elif name == "田中花子":
                return []  # No match
            else:
                return [{"id": 102, "name": "佐藤次郎", "party_name": "公明党"}]

        mock_politician_repo.search_by_name.side_effect = search_by_name_side_effect

        # Execute
        result = service.process_pending_members(1)

        # Assert
        assert result["total"] == 3
        assert result["matched"] == 2  # 山田太郎 and 佐藤次郎
        assert result["no_match"] == 1  # 田中花子
        assert result["needs_review"] == 0
        assert mock_extracted_repo.update_matching_result.call_count == 3

    def test_match_with_llm_error_handling(self, service, mock_llm_service):
        """Test handling of LLM errors"""
        # Setup
        member = {"id": 1, "extracted_name": "山田議員", "extracted_party_name": None}
        candidates = [{"id": 100, "name": "山田太郎", "party_name": "自民党"}]

        # Mock LLM error
        mock_llm_service.llm.invoke.side_effect = Exception("LLM Error")

        # Execute
        politician_id, confidence = service.match_with_llm(member, candidates)

        # Assert - should return no match on error
        assert politician_id is None
        assert confidence == 0.0
