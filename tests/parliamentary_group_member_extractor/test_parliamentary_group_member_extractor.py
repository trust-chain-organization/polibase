"""議員団メンバー抽出器のテスト"""

from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from src.parliamentary_group_member_extractor import (
    ExtractedMember,
    MatchingResult,
    MemberExtractionResult,
    ParliamentaryGroupMemberExtractor,
    ParliamentaryGroupMembershipService,
)


class TestParliamentaryGroupMemberExtractor:
    """ParliamentaryGroupMemberExtractorのテスト"""

    @pytest.fixture
    def extractor(self):
        """抽出器のフィクスチャ"""
        # LLMServiceをモックして注入
        mock_llm_service = MagicMock()
        return ParliamentaryGroupMemberExtractor(llm_service=mock_llm_service)

    @pytest.fixture
    def sample_html(self):
        """サンプルHTMLコンテンツ"""
        return """
        <html>
        <body>
            <h1>京都市会自民党議員団</h1>
            <div class="members">
                <div class="member">
                    <h3>山田太郎（団長）</h3>
                    <p>自由民主党</p>
                    <p>左京区選出</p>
                </div>
                <div class="member">
                    <h3>鈴木花子（幹事長）</h3>
                    <p>自由民主党</p>
                    <p>中京区選出</p>
                </div>
                <div class="member">
                    <h3>佐藤次郎</h3>
                    <p>自由民主党</p>
                    <p>右京区選出</p>
                </div>
            </div>
        </body>
        </html>
        """

    @pytest.mark.asyncio
    async def test_extract_members_success(self, extractor, sample_html):
        """メンバー抽出の成功テスト"""
        # HTMLフェッチャーをモック
        with patch.object(extractor, "_fetch_html", return_value=sample_html):
            # LLMの応答をモック
            mock_members = [
                ExtractedMember(
                    name="山田太郎",
                    role="団長",
                    party_name="自由民主党",
                    district="左京区",
                ),
                ExtractedMember(
                    name="鈴木花子",
                    role="幹事長",
                    party_name="自由民主党",
                    district="中京区",
                ),
                ExtractedMember(
                    name="佐藤次郎",
                    role=None,
                    party_name="自由民主党",
                    district="右京区",
                ),
            ]

            with patch.object(
                extractor, "_extract_members_with_llm", return_value=mock_members
            ):
                result = await extractor.extract_members(1, "https://example.com")

                assert result.parliamentary_group_id == 1
                assert result.url == "https://example.com"
                assert len(result.extracted_members) == 3
                assert result.error is None

                # 最初のメンバーの詳細を確認
                first_member = result.extracted_members[0]
                assert first_member.name == "山田太郎"
                assert first_member.role == "団長"
                assert first_member.party_name == "自由民主党"
                assert first_member.district == "左京区"

    @pytest.mark.asyncio
    async def test_extract_members_fetch_error(self, extractor):
        """HTML取得エラー時のテスト"""
        # HTMLフェッチャーがNoneを返す
        with patch.object(extractor, "_fetch_html", return_value=None):
            result = await extractor.extract_members(1, "https://example.com")

            assert result.parliamentary_group_id == 1
            assert result.url == "https://example.com"
            assert len(result.extracted_members) == 0
            expected_error = (
                "URLからコンテンツを取得できませんでした。"
                "URLが正しいか、またはPlaywrightが正しくインストールされているか確認してください。"
            )
            assert result.error == expected_error

    @pytest.mark.asyncio
    async def test_extract_members_llm_error(self, extractor, sample_html):
        """LLMエラー時のテスト"""
        with patch.object(extractor, "_fetch_html", return_value=sample_html):
            # LLMがエラーを発生させる
            with patch.object(
                extractor,
                "_extract_members_with_llm",
                side_effect=Exception("LLM error"),
            ):
                result = await extractor.extract_members(1, "https://example.com")

                assert result.parliamentary_group_id == 1
                assert len(result.extracted_members) == 0
                assert "LLM error" in result.error

    def test_extract_members_sync(self, extractor):
        """同期版メソッドのテスト"""
        mock_result = MemberExtractionResult(
            parliamentary_group_id=1,
            url="https://example.com",
            extracted_members=[ExtractedMember(name="テスト議員", role="団長")],
        )

        with patch.object(extractor, "extract_members", return_value=mock_result):
            result = extractor.extract_members_sync(1, "https://example.com")

            assert result.parliamentary_group_id == 1
            assert len(result.extracted_members) == 1


class TestParliamentaryGroupMembershipService:
    """ParliamentaryGroupMembershipServiceのテスト"""

    @pytest.fixture
    def service(self):
        """サービスのフィクスチャ"""
        # 依存関係をすべてモック
        mock_llm_service = MagicMock()
        mock_politician_repo = MagicMock()
        mock_group_repo = MagicMock()
        mock_membership_repo = MagicMock()

        return ParliamentaryGroupMembershipService(
            llm_service=mock_llm_service,
            politician_repo=mock_politician_repo,
            group_repo=mock_group_repo,
            membership_repo=mock_membership_repo,
        )

    @pytest.fixture
    def extracted_members(self):
        """抽出されたメンバーのサンプル"""
        return [
            ExtractedMember(
                name="山田太郎",
                role="団長",
                party_name="自由民主党",
                district="左京区",
            ),
            ExtractedMember(
                name="鈴木花子",
                role="幹事長",
                party_name="自由民主党",
                district="中京区",
            ),
        ]

    @pytest.fixture
    def politician_candidates(self):
        """政治家候補のサンプル"""
        return [
            {
                "id": 1,
                "name": "山田太郎",
                "political_party_id": 1,
                "party_name": "自由民主党",
                "district": "左京区",
                "profile": None,
            },
            {
                "id": 2,
                "name": "山田太朗",  # 類似名
                "political_party_id": 1,
                "party_name": "自由民主党",
                "district": "北区",
                "profile": None,
            },
        ]

    @pytest.mark.asyncio
    async def test_match_politicians_success(
        self, service, extracted_members, politician_candidates
    ):
        """政治家マッチングの成功テスト"""
        # 政治家検索をモック
        with patch.object(
            service,
            "_search_politician_candidates",
            side_effect=[politician_candidates, []],  # 1人目はマッチ、2人目はマッチなし
        ):
            # LLMマッチングをモック
            mock_match_result = MatchingResult(
                extracted_member=extracted_members[0],
                politician_id=1,
                politician_name="山田太郎",
                confidence_score=0.95,
                matching_reason="名前と政党、選挙区が完全一致",
            )

            with patch.object(
                service, "_find_best_match_with_llm", return_value=mock_match_result
            ):
                results = await service.match_politicians(extracted_members)

                assert len(results) == 2

                # 1人目：マッチ成功
                assert results[0].politician_id == 1
                assert results[0].politician_name == "山田太郎"
                assert results[0].confidence_score == 0.95

                # 2人目：マッチなし
                assert results[1].politician_id is None
                assert results[1].confidence_score == 0.0

    def test_create_memberships_success(self, service):
        """メンバーシップ作成の成功テスト"""
        matching_results = [
            MatchingResult(
                extracted_member=ExtractedMember(name="山田太郎", role="団長"),
                politician_id=1,
                politician_name="山田太郎",
                confidence_score=0.95,
                matching_reason="マッチ成功",
            ),
            MatchingResult(
                extracted_member=ExtractedMember(name="鈴木花子", role="幹事長"),
                politician_id=2,
                politician_name="鈴木花子",
                confidence_score=0.85,
                matching_reason="マッチ成功",
            ),
            MatchingResult(
                extracted_member=ExtractedMember(name="佐藤次郎"),
                politician_id=None,
                politician_name=None,
                confidence_score=0.0,
                matching_reason="マッチなし",
            ),
        ]

        # 現在のメンバーをモック（空）
        with patch.object(
            service.membership_repo, "get_current_members", return_value=[]
        ):
            # メンバーシップ追加をモック
            with patch.object(
                service.membership_repo,
                "add_membership",
                return_value={"id": 1},
            ):
                result = service.create_memberships(
                    parliamentary_group_id=1,
                    matching_results=matching_results,
                    start_date=date.today(),
                    confidence_threshold=0.7,
                    dry_run=False,
                )

                assert result.total_extracted == 3
                assert result.matched_count == 2
                assert result.created_count == 2
                assert result.skipped_count == 0
                assert len(result.errors) == 0

    def test_create_memberships_dry_run(self, service):
        """ドライランモードのテスト"""
        matching_results = [
            MatchingResult(
                extracted_member=ExtractedMember(name="山田太郎", role="団長"),
                politician_id=1,
                politician_name="山田太郎",
                confidence_score=0.95,
                matching_reason="マッチ成功",
            ),
        ]

        # 現在のメンバーをモック（空）
        with patch.object(
            service.membership_repo, "get_current_members", return_value=[]
        ):
            # add_membershipが呼ばれないことを確認
            with patch.object(service.membership_repo, "add_membership") as mock_add:
                result = service.create_memberships(
                    parliamentary_group_id=1,
                    matching_results=matching_results,
                    dry_run=True,
                )

                assert result.created_count == 1
                mock_add.assert_not_called()  # ドライランなので呼ばれない

    def test_create_memberships_skip_existing(self, service):
        """既存メンバーのスキップテスト"""
        matching_results = [
            MatchingResult(
                extracted_member=ExtractedMember(name="山田太郎", role="団長"),
                politician_id=1,
                politician_name="山田太郎",
                confidence_score=0.95,
                matching_reason="マッチ成功",
            ),
        ]

        # 現在のメンバーに既に存在
        current_members = [{"politician_id": 1, "politician_name": "山田太郎"}]

        with patch.object(
            service.membership_repo, "get_current_members", return_value=current_members
        ):
            result = service.create_memberships(
                parliamentary_group_id=1,
                matching_results=matching_results,
                dry_run=False,
            )

            assert result.matched_count == 1
            assert result.created_count == 0
            assert result.skipped_count == 1

    def test_create_memberships_low_confidence(self, service):
        """低信頼度のスキップテスト"""
        matching_results = [
            MatchingResult(
                extracted_member=ExtractedMember(name="山田太郎", role="団長"),
                politician_id=1,
                politician_name="山田太郎",
                confidence_score=0.5,  # 閾値以下
                matching_reason="部分的なマッチ",
            ),
        ]

        with patch.object(
            service.membership_repo, "get_current_members", return_value=[]
        ):
            result = service.create_memberships(
                parliamentary_group_id=1,
                matching_results=matching_results,
                confidence_threshold=0.7,
                dry_run=False,
            )

            assert result.matched_count == 1
            assert result.created_count == 0
            assert len(result.errors) == 1
            assert "信頼度が低い" in result.errors[0]
