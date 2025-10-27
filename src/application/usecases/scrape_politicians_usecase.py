"""Use case for scraping politicians from party websites."""

from src.application.dtos.politician_dto import (
    PoliticianPartyExtractedPoliticianDTO,
    PoliticianPartyExtractedPoliticianOutputDTO,
    ScrapePoliticiansInputDTO,
)
from src.domain.entities.party_scraping_state import PartyScrapingState
from src.domain.entities.political_party import PoliticalParty
from src.domain.entities.politician_party_extracted_politician import (
    PoliticianPartyExtractedPolitician,
)
from src.domain.repositories.extracted_politician_repository import (
    ExtractedPoliticianRepository,
)
from src.domain.repositories.political_party_repository import PoliticalPartyRepository
from src.domain.services.interfaces.party_scraping_agent import IPartyScrapingAgent


class ScrapePoliticiansUseCase:
    """政治家情報スクレイピングユースケース

    政党のウェブサイトから政治家情報を収集し、中間テーブル（extracted_politicians）に保存します。
    重複チェック機能を含みます。

    Attributes:
        party_repo: 政党リポジトリ
        extracted_politician_repo: 抽出済み政治家リポジトリ
        scraper: Webスクレイピングサービス

    Example:
        >>> use_case = ScrapePoliticiansUseCase(
        ...     party_repo, extracted_politician_repo, scraper_service
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
        extracted_politician_repository: ExtractedPoliticianRepository,
        party_scraping_agent: IPartyScrapingAgent,
    ):
        """政治家スクレイピングユースケースを初期化する

        Args:
            political_party_repository: 政党リポジトリの実装
            extracted_politician_repository: 抽出済み政治家リポジトリの実装
            party_scraping_agent: LangGraphベースの政党スクレイピングエージェント
        """
        self.party_repo = political_party_repository
        self.extracted_politician_repo = extracted_politician_repository
        self.scraping_agent = party_scraping_agent

    async def execute(
        self,
        request: ScrapePoliticiansInputDTO,
    ) -> list[PoliticianPartyExtractedPoliticianOutputDTO]:
        """政治家情報のスクレイピングを実行する

        処理の流れ：
        1. 対象政党の特定（単一または全政党）
        2. 各政党のメンバーリストURLからスクレイピング
        3. 重複チェック
        4. extracted_politiciansテーブルへの保存

        Args:
            request: スクレイピングリクエストDTO
                - party_id: 特定政党のID（オプション）
                - all_parties: 全政党を対象とするか
                - dry_run: 実行せずに結果を確認するか

        Returns:
            PoliticianPartyExtractedPoliticianOutputDTOのリスト。各DTOには以下が含まれる：
            - id: 抽出済み政治家ID（dry_runの場合は0）
            - name: 政治家名
            - party_id: 所属政党ID
            - party_name: 所属政党名
            - district: 選挙区
            - position: 役職
            - profile_url: プロフィールURL
            - image_url: プロフィール画像URL
            - status: ステータス（pending）

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

        all_results: list[PoliticianPartyExtractedPoliticianOutputDTO] = []
        total_extracted = 0
        total_skipped = 0
        total_saved = 0

        for party in parties:
            # Scrape party website
            extracted = await self._scrape_party_website(party)
            total_extracted += len(extracted)
            print(
                f"DEBUG UseCase: Extracted {len(extracted)} DTOs from _scrape_party_website"
            )
            print(f"DEBUG UseCase: request.dry_run = {request.dry_run}")

            if request.dry_run:
                # Convert to DTOs without saving
                print(
                    f"DEBUG UseCase: In dry_run branch, processing {len(extracted)} items"
                )
                for data in extracted:
                    print(f"DEBUG UseCase: Processing member: {data.name}")
                    all_results.append(
                        PoliticianPartyExtractedPoliticianOutputDTO(
                            id=0,  # Not saved
                            name=data.name,
                            party_id=data.party_id,
                            party_name=party.name,
                            district=data.district,
                            profile_url=data.profile_page_url,
                            status="pending",
                        )
                    )
                print(
                    f"DEBUG UseCase: After dry_run loop, all_results has {len(all_results)} items"
                )
            else:
                # Save extracted politicians
                print(
                    f"DEBUG UseCase: In save branch, extracted has {len(extracted)} items"
                )
                logger.info(
                    f"Saving {len(extracted)} politicians to "
                    "extracted_politicians table"
                )
                (
                    saved_politicians,
                    skipped_count,
                ) = await self._save_extracted_politicians(extracted, party.name)
                total_skipped += skipped_count
                total_saved += len(saved_politicians)
                print(
                    f"DEBUG UseCase: _save_extracted_politicians returned {len(saved_politicians)} saved, {skipped_count} skipped"
                )

                for politician in saved_politicians:
                    print(f"DEBUG UseCase: Adding saved politician: {politician.name}")
                    all_results.append(
                        PoliticianPartyExtractedPoliticianOutputDTO(
                            id=politician.id if politician.id else 0,
                            name=politician.name,
                            party_id=politician.party_id,
                            party_name=party.name,
                            district=politician.district,
                            profile_url=politician.profile_url,
                            status=politician.status,
                        )
                    )
                print(
                    f"DEBUG UseCase: After save loop, all_results has {len(all_results)} items"
                )

                if skipped_count > 0:
                    logger.info(
                        f"Skipped {skipped_count} duplicate politicians, "
                        f"saved {len(saved_politicians)} new ones"
                    )
                else:
                    logger.info(
                        f"Saved {len(saved_politicians)} politicians to "
                        "extracted_politicians"
                    )

        # Log summary
        if not request.dry_run and total_skipped > 0:
            logger.info(
                f"Extraction complete: {total_extracted} extracted, "
                f"{total_saved} saved, {total_skipped} already existed"
            )

        return all_results

    async def _scrape_party_website(
        self, party: PoliticalParty
    ) -> list[PoliticianPartyExtractedPoliticianDTO]:
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

        if party.id is None:
            raise ValueError("Party must have an ID")

        import logging

        logger = logging.getLogger(__name__)

        # Create initial state for LangGraph agent
        initial_state = PartyScrapingState(
            party_id=party.id,
            party_name=party.name,
            current_url=party.members_list_url,
            max_depth=3,  # Reasonable default for hierarchical navigation
        )

        # Execute LangGraph-based scraping
        logger.info(
            f"Starting LangGraph scraping for {party.name} "
            f"from {party.members_list_url}"
        )
        final_state = await self.scraping_agent.scrape(initial_state)

        # Debug: Log final state details
        debug_msg = (
            f"Final state - extracted_members count: {len(final_state.extracted_members)}, "
            f"visited_urls count: {len(final_state.visited_urls)}, "
            f"error: {final_state.error_message}"
        )
        logger.info(debug_msg)
        print(f"DEBUG UseCase: {debug_msg}")  # Force print to stdout

        if final_state.error_message:
            logger.error(
                f"LangGraph scraping failed for {party.name}: "
                f"{final_state.error_message}"
            )
            # Return empty list on error instead of raising
            return []

        if not final_state.extracted_members:
            logger.warning(
                f"No members extracted for {party.name}. "
                f"Visited {len(final_state.visited_urls)} URLs"
            )

        # Convert extracted members to DTOs
        extracted: list[PoliticianPartyExtractedPoliticianDTO] = []
        for member in final_state.extracted_members:
            # extracted_members returns PoliticianMemberData (TypedDict)
            # Name is required in practice but TypedDict has total=False
            name = member.get("name")
            if not name:
                logger.warning(f"Skipping member with missing name: {member}")
                continue

            dto = PoliticianPartyExtractedPoliticianDTO(
                name=name,
                party_id=party.id,
                furigana=None,  # Not available in PoliticianMemberData
                district=member.get("electoral_district"),
                profile_page_url=member.get("profile_url"),
                source_url=party.members_list_url,
            )
            extracted.append(dto)

        logger.info(
            f"LangGraph scraping completed: {len(extracted)} members "
            f"extracted from {party.name}"
        )

        return extracted

    async def _save_extracted_politicians(
        self,
        extracted_data: list[PoliticianPartyExtractedPoliticianDTO],
        party_name: str,
    ) -> tuple[list[PoliticianPartyExtractedPolitician], int]:
        """抽出データを extracted_politicians テーブルに保存する

        重複チェックを行い、既存のデータがある場合はスキップします。

        Args:
            extracted_data: 抽出された政治家データのリスト
            party_name: 政党名（ログ用）

        Returns:
            Tuple of:
            - 保存された PoliticianPartyExtractedPolitician エンティティのリスト
            - スキップされた重複の数
        """
        import logging

        logger = logging.getLogger(__name__)
        saved_politicians: list[PoliticianPartyExtractedPolitician] = []
        skipped_count = 0

        for data in extracted_data:
            print(f"DEBUG Save: Processing {data.name} (party_id={data.party_id})")

            # Check for duplicates in extracted_politicians table
            duplicates = await self.extracted_politician_repo.get_duplicates(
                data.name, data.party_id
            )
            print(f"DEBUG Save: Found {len(duplicates)} duplicates for {data.name}")

            if duplicates:
                logger.info(
                    f"Skipping duplicate: {data.name} already exists in "
                    "extracted_politicians"
                )
                print(f"DEBUG Save: Skipping {data.name} (duplicate)")
                skipped_count += 1
                continue

            # Create new extracted politician
            print(f"DEBUG Save: Creating new entity for {data.name}")
            extracted_politician = PoliticianPartyExtractedPolitician(
                name=data.name,
                party_id=data.party_id,
                district=data.district,
                profile_url=data.profile_page_url,
                status="pending",  # Initial status is pending for review
            )

            print(f"DEBUG Save: Calling repository.create() for {data.name}")
            created = await self.extracted_politician_repo.create(extracted_politician)
            print(f"DEBUG Save: create() returned: {created}")

            if created:
                saved_politicians.append(created)
                logger.info(
                    f"Saved to extracted_politicians: {created.name} (ID: {created.id})"
                )
                print(f"DEBUG Save: Successfully saved {created.name}")
            else:
                print(f"DEBUG Save: create() returned None for {data.name}")

        return saved_politicians, skipped_count
