"""
Dependency providers for dependency injection containers.

This module defines the providers for repositories, services, and use cases.
"""

from dependency_injector import containers, providers
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.application.usecases.analyze_party_page_links_usecase import (
    AnalyzePartyPageLinksUseCase,
)
from src.application.usecases.convert_extracted_politician_usecase import (
    ConvertExtractedPoliticianUseCase,
)
from src.application.usecases.execute_minutes_processing_usecase import (
    ExecuteMinutesProcessingUseCase,
)
from src.application.usecases.execute_speaker_extraction_usecase import (
    ExecuteSpeakerExtractionUseCase,
)
from src.application.usecases.extract_proposal_judges_usecase import (
    ExtractProposalJudgesUseCase,
)
from src.application.usecases.manage_conference_members_usecase import (
    ManageConferenceMembersUseCase,
)
from src.application.usecases.match_speakers_usecase import MatchSpeakersUseCase
from src.application.usecases.process_minutes_usecase import ProcessMinutesUseCase
from src.application.usecases.review_and_convert_politician_usecase import (
    ReviewAndConvertPoliticianUseCase,
)
from src.application.usecases.review_extracted_politician_usecase import (
    ReviewExtractedPoliticianUseCase,
)
from src.application.usecases.scrape_politicians_usecase import ScrapePoliticiansUseCase
from src.domain.services.interfaces.html_link_extractor_service import (
    IHtmlLinkExtractorService,
)
from src.domain.services.interfaces.link_analyzer_service import ILinkAnalyzerService
from src.domain.services.interfaces.llm_link_classifier_service import (
    ILLMLinkClassifierService,
)
from src.domain.services.interfaces.llm_service import ILLMService
from src.domain.services.interfaces.minutes_processing_service import (
    IMinutesProcessingService,
)
from src.domain.services.interfaces.page_classifier_service import (
    IPageClassifierService,
)
from src.domain.services.interfaces.party_scraping_agent import IPartyScrapingAgent
from src.domain.services.interfaces.storage_service import IStorageService
from src.domain.services.link_analysis_domain_service import LinkAnalysisDomainService
from src.domain.services.party_member_extraction_service import (
    IPartyMemberExtractionService,
)
from src.domain.services.politician_domain_service import PoliticianDomainService
from src.domain.services.speaker_domain_service import SpeakerDomainService
from src.infrastructure.external.gcs_storage_service import GCSStorageService
from src.infrastructure.external.html_link_extractor_service import (
    BeautifulSoupLinkExtractor,
)

# fmt: off - Long import line required for clarity
from src.infrastructure.external.langgraph_party_scraping_agent_with_classification import (  # noqa: E501
    LangGraphPartyScrapingAgentWithClassification,
)

# fmt: on
from src.infrastructure.external.link_analyzer_service_impl import (
    LinkAnalyzerServiceImpl,
)
from src.infrastructure.external.llm_link_classifier_service import (
    LLMLinkClassifierService,
)
from src.infrastructure.external.llm_page_classifier_service import (
    LLMPageClassifierService,
)
from src.infrastructure.external.llm_service import GeminiLLMService
from src.infrastructure.external.minutes_processing_service import (
    MinutesProcessAgentService,
)
from src.infrastructure.external.party_member_extraction_service_impl import (
    PartyMemberExtractionServiceImpl,
)
from src.infrastructure.external.web_scraper_service import (
    IWebScraperService,
    PlaywrightScraperService,
)
from src.infrastructure.persistence.async_session_adapter import AsyncSessionAdapter
from src.infrastructure.persistence.conference_repository_impl import (
    ConferenceRepositoryImpl,
)
from src.infrastructure.persistence.conversation_repository_impl import (
    ConversationRepositoryImpl,
)
from src.infrastructure.persistence.extracted_conference_member_repository_impl import (
    ExtractedConferenceMemberRepositoryImpl,
)
from src.infrastructure.persistence.extracted_politician_repository_impl import (
    ExtractedPoliticianRepositoryImpl,
)
from src.infrastructure.persistence.extracted_proposal_judge_repository_impl import (
    ExtractedProposalJudgeRepositoryImpl,
)
from src.infrastructure.persistence.governing_body_repository_impl import (
    GoverningBodyRepositoryImpl,
)
from src.infrastructure.persistence.llm_processing_history_repository_impl import (
    LLMProcessingHistoryRepositoryImpl,
)
from src.infrastructure.persistence.llm_service_adapter import LLMServiceAdapter
from src.infrastructure.persistence.meeting_repository_impl import MeetingRepositoryImpl
from src.infrastructure.persistence.minutes_repository_impl import MinutesRepositoryImpl
from src.infrastructure.persistence.monitoring_repository_impl import (
    MonitoringRepositoryImpl,
)
from src.infrastructure.persistence.parliamentary_group_repository_impl import (
    ParliamentaryGroupMembershipRepositoryImpl,
    ParliamentaryGroupRepositoryImpl,
)
from src.infrastructure.persistence.political_party_repository_impl import (
    PoliticalPartyRepositoryImpl,
)
from src.infrastructure.persistence.politician_affiliation_repository_impl import (
    PoliticianAffiliationRepositoryImpl,
)
from src.infrastructure.persistence.politician_repository_impl import (
    PoliticianRepositoryImpl,
)
from src.infrastructure.persistence.prompt_version_repository_impl import (
    PromptVersionRepositoryImpl,
)
from src.infrastructure.persistence.proposal_judge_repository_impl import (
    ProposalJudgeRepositoryImpl,
)
from src.infrastructure.persistence.proposal_repository_impl import (
    ProposalRepositoryImpl,
)
from src.infrastructure.persistence.speaker_repository_impl import SpeakerRepositoryImpl
from src.infrastructure.persistence.unit_of_work_impl import UnitOfWorkImpl


# Mock SQLAlchemy model classes for repositories that don't have them yet
class MockSpeakerModel:
    """Mock SQLAlchemy model for Speaker entity."""

    __tablename__ = "speakers"
    id = None
    name = None


class MockPoliticianModel:
    """Mock SQLAlchemy model for Politician entity."""

    __tablename__ = "politicians"
    id = None
    name = None


class MockMeetingModel:
    """Mock SQLAlchemy model for Meeting entity."""

    __tablename__ = "meetings"
    id = None


class MockConversationModel:
    """Mock SQLAlchemy model for Conversation entity."""

    __tablename__ = "conversations"
    id = None


class MockMinutesModel:
    """Mock SQLAlchemy model for Minutes entity."""

    __tablename__ = "minutes"
    id = None


class MockService:
    """Mock service for testing."""

    def __init__(self, service_type: str):
        self.service_type = service_type


class MockDomainService:
    """Mock domain service for testing."""

    def __init__(self, domain_type: str):
        self.domain_type = domain_type


class MockRepository:
    """Mock repository for testing."""

    def __init__(self, repository_type: str):
        self.repository_type = repository_type


def create_engine_with_config(database_url: str | None):
    """Create SQLAlchemy engine with appropriate configuration for database type."""
    # Handle None database_url with a default
    if database_url is None:
        import logging
        import os

        logger = logging.getLogger(__name__)
        # Use debug level as this is expected behavior during initial container setup
        logger.debug("database_url is None, using default value based on environment")

        # Check if running in Docker
        if os.path.exists("/.dockerenv") or os.getenv("DOCKER_CONTAINER"):
            database_url = (
                "postgresql://polibase_user:polibase_password@postgres:5432/polibase_db"
            )
        else:
            database_url = "postgresql://polibase_user:polibase_password@localhost:5432/polibase_db"

    engine_kwargs = {
        "url": database_url,
        "pool_pre_ping": True,
    }

    # Only add pool parameters for non-SQLite databases
    if not database_url.startswith("sqlite"):
        engine_kwargs.update(
            {
                "pool_size": 5,
                "max_overflow": 10,
            }
        )

    return create_engine(**engine_kwargs)


class DatabaseContainer(containers.DeclarativeContainer):
    """Container for database-related dependencies."""

    config = providers.Configuration()

    engine = providers.Singleton(
        create_engine_with_config,
        database_url=config.database_url,
    )

    session_factory = providers.Singleton(
        sessionmaker,
        bind=engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )

    session = providers.Factory(
        lambda factory: factory(),
        factory=session_factory,
    )

    async_session = providers.Factory(
        AsyncSessionAdapter,
        sync_session=session,
    )


class RepositoryContainer(containers.DeclarativeContainer):
    """Container for repository implementations."""

    database = providers.DependenciesContainer()

    speaker_repository = providers.Factory(
        SpeakerRepositoryImpl,
        session=database.async_session,
    )

    politician_repository = providers.Factory(
        PoliticianRepositoryImpl,
        session=database.async_session,
    )

    meeting_repository = providers.Factory(
        MeetingRepositoryImpl,
        session=database.async_session,
    )

    conversation_repository = providers.Factory(
        ConversationRepositoryImpl,
        session=database.async_session,
    )

    minutes_repository = providers.Factory(
        MinutesRepositoryImpl,
        session=database.async_session,
    )

    conference_repository = providers.Factory(
        ConferenceRepositoryImpl,
        session=database.async_session,
    )

    governing_body_repository = providers.Factory(
        GoverningBodyRepositoryImpl,
        session=database.async_session,
    )

    political_party_repository = providers.Factory(
        PoliticalPartyRepositoryImpl,
        session=database.async_session,
    )

    politician_affiliation_repository = providers.Factory(
        PoliticianAffiliationRepositoryImpl,
        session=database.async_session,
    )

    extracted_conference_member_repository = providers.Factory(
        ExtractedConferenceMemberRepositoryImpl,
        session=database.async_session,
    )

    extracted_politician_repository = providers.Factory(
        ExtractedPoliticianRepositoryImpl,
        session=database.async_session,
    )

    extracted_proposal_judge_repository = providers.Factory(
        ExtractedProposalJudgeRepositoryImpl,
        session=database.async_session,
    )

    parliamentary_group_repository = providers.Factory(
        ParliamentaryGroupRepositoryImpl,
        session=database.async_session,
    )

    parliamentary_group_membership_repository = providers.Factory(
        ParliamentaryGroupMembershipRepositoryImpl,
        session=database.async_session,
    )

    monitoring_repository = providers.Factory(
        MonitoringRepositoryImpl,
        session=database.async_session,
    )

    llm_processing_history_repository = providers.Factory(
        LLMProcessingHistoryRepositoryImpl,
        session=database.async_session,
    )

    prompt_version_repository = providers.Factory(
        PromptVersionRepositoryImpl,
        session=database.async_session,
    )

    proposal_repository = providers.Factory(
        ProposalRepositoryImpl,
        session=database.async_session,
    )

    proposal_judge_repository = providers.Factory(
        ProposalJudgeRepositoryImpl,
        session=database.async_session,
    )


class ServiceContainer(containers.DeclarativeContainer):
    """Container for external service implementations."""

    config = providers.Configuration()

    # Create async LLM service
    async_llm_service: providers.Provider[ILLMService] = providers.Factory(
        GeminiLLMService,
        api_key=config.google_api_key,
        model_name=config.llm_model,
        temperature=config.llm_temperature,
    )

    # Wrap with adapter for synchronous use cases
    llm_service = providers.Factory(
        LLMServiceAdapter,
        llm_service=async_llm_service,
    )

    storage_service: providers.Provider[IStorageService] = providers.Singleton(
        GCSStorageService,
        bucket_name=config.gcs_bucket_name,
    )

    web_scraper_service: providers.Provider[IWebScraperService] = providers.Factory(
        PlaywrightScraperService,
        headless=True,
    )

    minutes_processing_service: providers.Provider[IMinutesProcessingService] = (
        providers.Factory(
            MinutesProcessAgentService,
            llm_service=llm_service,
        )
    )

    # Domain services
    politician_domain_service = providers.Factory(PoliticianDomainService)
    speaker_domain_service = providers.Factory(SpeakerDomainService)
    link_analysis_domain_service = providers.Factory(LinkAnalysisDomainService)

    # Infrastructure services for link analysis
    html_link_extractor_service: providers.Provider[IHtmlLinkExtractorService] = (
        providers.Factory(BeautifulSoupLinkExtractor)
    )

    llm_link_classifier_service: providers.Provider[ILLMLinkClassifierService] = (
        providers.Factory(
            LLMLinkClassifierService,
            llm_service=llm_service,
        )
    )

    # Page classifier service for hierarchical scraping
    page_classifier_service: providers.Provider[IPageClassifierService] = (
        providers.Factory(
            LLMPageClassifierService,
            llm_service=llm_service,
        )
    )

    # Party member extraction service
    party_member_extraction_service: providers.Provider[
        IPartyMemberExtractionService
    ] = providers.Factory(
        PartyMemberExtractionServiceImpl,
        llm_service=llm_service,
        party_id=None,  # Will be set per-request
    )

    # Mock services for testing (these may not have real implementations yet)
    minutes_domain_service = providers.Factory(lambda: MockDomainService("minutes"))

    pdf_processor_service = providers.Factory(lambda: MockService("pdf_processor"))

    text_extractor_service = providers.Factory(lambda: MockService("text_extractor"))


class UseCaseContainer(containers.DeclarativeContainer):
    """Container for use case implementations."""

    repositories = providers.DependenciesContainer()
    services = providers.DependenciesContainer()
    database = providers.DependenciesContainer()

    process_minutes_usecase = providers.Factory(
        ProcessMinutesUseCase,
        meeting_repository=repositories.meeting_repository,
        minutes_repository=repositories.minutes_repository,
        conversation_repository=repositories.conversation_repository,
        speaker_repository=repositories.speaker_repository,
        minutes_domain_service=services.minutes_domain_service,
        speaker_domain_service=services.speaker_domain_service,
        pdf_processor=services.pdf_processor_service,
        text_extractor=services.text_extractor_service,
    )

    match_speakers_usecase = providers.Factory(
        MatchSpeakersUseCase,
        speaker_repository=repositories.speaker_repository,
        politician_repository=repositories.politician_repository,
        conversation_repository=repositories.conversation_repository,
        speaker_domain_service=services.speaker_domain_service,
        llm_service=services.llm_service,
    )

    # Define analyze_party_page_links_usecase, link_analyzer_service, and party_scraping_agent
    # before scrape_politicians_usecase to resolve dependencies
    analyze_party_page_links_usecase = providers.Factory(
        AnalyzePartyPageLinksUseCase,
        html_extractor=services.html_link_extractor_service,
        link_classifier=services.llm_link_classifier_service,
        link_analysis_service=services.link_analysis_domain_service,
    )

    link_analyzer_service: providers.Provider[ILinkAnalyzerService] = providers.Factory(
        LinkAnalyzerServiceImpl,
        link_analysis_usecase=analyze_party_page_links_usecase,
    )

    party_scraping_agent: providers.Provider[IPartyScrapingAgent] = providers.Factory(
        LangGraphPartyScrapingAgentWithClassification,
        page_classifier=services.page_classifier_service,
        scraper=services.web_scraper_service,
        member_extractor=services.party_member_extraction_service,
        link_analyzer=link_analyzer_service,
    )

    scrape_politicians_usecase = providers.Factory(
        ScrapePoliticiansUseCase,
        political_party_repository=repositories.political_party_repository,
        extracted_politician_repository=repositories.extracted_politician_repository,
        party_scraping_agent=party_scraping_agent,
    )

    manage_conference_members_usecase = providers.Factory(
        ManageConferenceMembersUseCase,
        conference_repository=repositories.conference_repository,
        extracted_member_repository=repositories.extracted_conference_member_repository,
        politician_repository=repositories.politician_repository,
        politician_affiliation_repository=repositories.politician_affiliation_repository,
        web_scraper_service=services.web_scraper_service,
        llm_service=services.llm_service,
    )

    review_extracted_politician_usecase = providers.Factory(
        ReviewExtractedPoliticianUseCase,
        extracted_politician_repository=repositories.extracted_politician_repository,
        party_repository=repositories.political_party_repository,
    )

    convert_extracted_politician_usecase = providers.Factory(
        ConvertExtractedPoliticianUseCase,
        extracted_politician_repository=repositories.extracted_politician_repository,
        politician_repository=repositories.politician_repository,
        speaker_repository=repositories.speaker_repository,
    )

    review_and_convert_politician_usecase = providers.Factory(
        ReviewAndConvertPoliticianUseCase,
        review_use_case=review_extracted_politician_usecase,
        convert_use_case=convert_extracted_politician_usecase,
        extracted_politician_repository=repositories.extracted_politician_repository,
    )

    speaker_extraction_usecase = providers.Factory(
        ExecuteSpeakerExtractionUseCase,
        minutes_repository=repositories.minutes_repository,
        conversation_repository=repositories.conversation_repository,
        speaker_repository=repositories.speaker_repository,
        speaker_domain_service=services.speaker_domain_service,
    )

    # Unit of Work for transaction management
    unit_of_work = providers.Factory(
        UnitOfWorkImpl,
        session=database.async_session,
    )

    minutes_processing_usecase = providers.Factory(
        ExecuteMinutesProcessingUseCase,
        speaker_domain_service=services.speaker_domain_service,
        minutes_processing_service=services.minutes_processing_service,
        storage_service=services.storage_service,
        unit_of_work=unit_of_work,
    )

    extract_proposal_judges_usecase = providers.Factory(
        ExtractProposalJudgesUseCase,
        proposal_repository=repositories.proposal_repository,
        politician_repository=repositories.politician_repository,
        extracted_proposal_judge_repository=repositories.extracted_proposal_judge_repository,
        proposal_judge_repository=repositories.proposal_judge_repository,
        web_scraper_service=services.web_scraper_service,
        llm_service=services.llm_service,
    )
