"""Use case for scraping politicians from party websites."""

from src.application.dtos.politician_dto import (
    ExtractedPoliticianDTO,
    PoliticianDTO,
    ScrapePoliticiansInputDTO,
)
from src.domain.entities.political_party import PoliticalParty
from src.domain.entities.politician import Politician
from src.domain.entities.speaker import Speaker
from src.domain.repositories.political_party_repository import PoliticalPartyRepository
from src.domain.repositories.politician_repository import PoliticianRepository
from src.domain.repositories.speaker_repository import SpeakerRepository
from src.domain.services.politician_domain_service import PoliticianDomainService
from src.infrastructure.interfaces.web_scraper_service import IWebScraperService


class ScrapePoliticiansUseCase:
    """政治家情報スクレイピングユースケース

    政党のウェブサイトから政治家情報を収集し、データベースに保存します。
    重複チェックとデータのマージ機能を含みます。

    Attributes:
        party_repo: 政党リポジトリ
        politician_repo: 政治家リポジトリ
        speaker_repo: 発言者リポジトリ
        politician_service: 政治家ドメインサービス
        scraper: Webスクレイピングサービス

    Example:
        >>> use_case = ScrapePoliticiansUseCase(
        ...     party_repo, politician_repo, speaker_repo,
        ...     politician_service, scraper_service
        ... )
        >>> # 全政党から収集
        >>> result = await use_case.execute(
        ...     ScrapePoliticiansInputDTO(all_parties=True)
        ... )
        >>> print(f"収集した政治家数: {len(result)}")

        >>> # 特定政党から収集（ドライラン）
        >>> result = await use_case.execute(
        ...     ScrapePoliticiansInputDTO(party_id=5, dry_run=True)
        ... )
    """

    def __init__(
        self,
        political_party_repository: PoliticalPartyRepository,
        politician_repository: PoliticianRepository,
        speaker_repository: SpeakerRepository,
        politician_domain_service: PoliticianDomainService,
        web_scraper_service: IWebScraperService,
    ):
        """政治家スクレイピングユースケースを初期化する

        Args:
            political_party_repository: 政党リポジトリの実装
            politician_repository: 政治家リポジトリの実装
            speaker_repository: 発言者リポジトリの実装
            politician_domain_service: 政治家ドメインサービス
            web_scraper_service: Webスクレイピングサービス
        """
        self.party_repo = political_party_repository
        self.politician_repo = politician_repository
        self.speaker_repo = speaker_repository
        self.politician_service = politician_domain_service
        self.scraper = web_scraper_service

    async def execute(
        self,
        request: ScrapePoliticiansInputDTO,
    ) -> list[PoliticianDTO]:
        """政治家情報のスクレイピングを実行する

        処理の流れ：
        1. 対象政党の特定（単一または全政党）
        2. 各政党のメンバーリストURLからスクレイピング
        3. 重複チェックとデータマージ
        4. 新規登録または既存データ更新

        Args:
            request: スクレイピングリクエストDTO
                - party_id: 特定政党のID（オプション）
                - all_parties: 全政党を対象とするか
                - dry_run: 実行せずに結果を確認するか

        Returns:
            PoliticianDTOのリスト。各DTOには以下が含まれる：
            - id: 政治家ID（dry_runの場合は0）
            - name: 政治家名
            - speaker_id: 発言者ID
            - political_party_id: 所属政党ID
            - political_party_name: 所属政党名
            - furigana: ふりがな
            - position: 役職
            - district: 選挙区
            - profile_image_url: プロフィール画像URL
            - profile_page_url: プロフィールページURL

        Raises:
            ValueError: party_idが無効、または必須パラメータが未指定の場合
        """
        import logging

        logger = logging.getLogger(__name__)

        # Get parties to scrape
        if request.party_id:
            party = await self.party_repo.get_by_id(request.party_id)
            if not party:
                raise ValueError(f"Party {request.party_id} not found")
            parties = [party] if party.members_list_url else []
        elif request.all_parties:
            parties = await self.party_repo.get_with_members_url()
        else:
            raise ValueError("Either party_id or all_parties must be specified")

        all_results: list[PoliticianDTO] = []

        for party in parties:
            # Scrape party website
            extracted = await self._scrape_party_website(party)

            if request.dry_run:
                # Convert to DTOs without saving
                for data in extracted:
                    all_results.append(
                        PoliticianDTO(
                            id=0,  # Not saved
                            name=data.name,
                            speaker_id=0,  # Not created
                            political_party_id=data.party_id,
                            political_party_name=party.name,
                            furigana=data.furigana,
                            position=data.position,
                            district=data.district,
                            profile_image_url=data.profile_image_url,
                            profile_page_url=data.profile_page_url,
                        )
                    )
            else:
                # Save politicians
                logger.info(f"Saving {len(extracted)} politicians to database")
                for idx, data in enumerate(extracted, 1):
                    logger.info(
                        f"Processing politician {idx}/{len(extracted)}: {data.name}"
                    )
                    politician_dto = await self._create_or_update_politician(data)
                    if politician_dto:
                        all_results.append(politician_dto)
                        logger.info(
                            f"Saved: {politician_dto.name} (ID: {politician_dto.id})"
                        )

        return all_results

    async def _scrape_party_website(
        self, party: PoliticalParty
    ) -> list[ExtractedPoliticianDTO]:
        """政党ウェブサイトから政治家情報をスクレイピングする

        Args:
            party: 対象政党エンティティ

        Returns:
            抽出された政治家情報のDTOリスト

        Raises:
            ValueError: 政党にIDがない場合
        """
        if not party.members_list_url:
            return []

        # Use web scraper service
        if party.id is None:
            raise ValueError("Party must have an ID")
        raw_data = await self.scraper.scrape_party_members(
            party.members_list_url, party.id, party.name
        )

        # Log raw data count
        import logging

        logger = logging.getLogger(__name__)
        logger.info(f"Raw data received: {len(raw_data)} items")

        # Convert to DTOs
        extracted: list[ExtractedPoliticianDTO] = []
        for item in raw_data:
            dto = ExtractedPoliticianDTO(
                name=item["name"],
                party_id=party.id,  # Safe because we checked above
                furigana=item.get("furigana"),
                position=item.get("position"),
                district=item.get("district"),
                profile_image_url=item.get("profile_image_url"),
                profile_page_url=item.get("profile_page_url"),
                source_url=party.members_list_url,
            )
            extracted.append(dto)

        return extracted

    async def _create_or_update_politician(
        self, data: ExtractedPoliticianDTO
    ) -> PoliticianDTO | None:
        """抽出データから政治家を作成または更新する

        重複チェックを行い、既存データがある場合は新しい情報で
        更新します。新規の場合は発言者レコードも作成します。

        Args:
            data: 抽出された政治家データ

        Returns:
            作成または更新された政治家DTO（重複スキップの場合None）

        Raises:
            ValueError: 作成された発言者にIDがない場合
        """
        # Check for existing politician
        existing = await self.politician_repo.get_by_name_and_party(
            data.name, data.party_id
        )

        if existing:
            # Check if duplicate
            all_politicians = await self.politician_repo.get_by_party(data.party_id)
            duplicate = self.politician_service.is_duplicate_politician(
                Politician(
                    name=data.name,
                    speaker_id=0,  # Temporary
                    political_party_id=data.party_id,
                ),
                all_politicians,
            )

            if duplicate:
                # Update existing if new data
                if any(
                    [
                        data.furigana and not duplicate.furigana,
                        data.position and not duplicate.position,
                        data.district and not duplicate.district,
                        data.profile_image_url and not duplicate.profile_image_url,
                        data.profile_page_url and not duplicate.profile_page_url,
                    ]
                ):
                    merged = self.politician_service.merge_politician_info(
                        duplicate,
                        Politician(
                            name=data.name,
                            speaker_id=duplicate.speaker_id,
                            political_party_id=data.party_id,
                            furigana=data.furigana,
                            position=data.position,
                            district=data.district,
                            profile_image_url=data.profile_image_url,
                            profile_page_url=data.profile_page_url,
                        ),
                    )
                    updated = await self.politician_repo.update(merged)
                    return self._to_dto(updated)
                return None  # Skip duplicate

        # Create new speaker first
        speaker = Speaker(
            name=data.name,
            type="政治家",
            is_politician=True,
        )
        created_speaker = await self.speaker_repo.upsert(speaker)

        # Create politician
        if created_speaker.id is None:
            raise ValueError("Created speaker must have an ID")
        politician = Politician(
            name=data.name,
            speaker_id=created_speaker.id,
            political_party_id=data.party_id,
            furigana=data.furigana,
            position=data.position,
            district=data.district,
            profile_image_url=data.profile_image_url,
            profile_page_url=data.profile_page_url,
        )

        created = await self.politician_repo.create(politician)
        return self._to_dto(created)

    def _to_dto(self, politician: Politician) -> PoliticianDTO:
        """政治家エンティティをDTOに変換する

        Args:
            politician: 政治家エンティティ

        Returns:
            政治家DTO
        """
        return PoliticianDTO(
            id=politician.id if politician.id is not None else 0,
            name=politician.name,
            speaker_id=politician.speaker_id,
            political_party_id=politician.political_party_id,
            political_party_name=None,  # Would need to fetch
            furigana=politician.furigana,
            position=politician.position,
            district=politician.district,
            profile_image_url=politician.profile_image_url,
            profile_page_url=politician.profile_page_url,
        )
