"""
Dependency providers for dependency injection containers.

This module defines the providers for repositories, services, and use cases.
"""

from dependency_injector import containers, providers
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.application.usecases.manage_conference_members_usecase import (
    ManageConferenceMembersUseCase,
)
from src.application.usecases.match_speakers_usecase import MatchSpeakersUseCase
from src.application.usecases.process_minutes_usecase import ProcessMinutesUseCase
from src.application.usecases.scrape_politicians_usecase import ScrapePoliticiansUseCase
from src.infrastructure.external.llm_service import GeminiLLMService
from src.infrastructure.external.storage_service import (
    GCSStorageService,
    IStorageService,
)
from src.infrastructure.external.web_scraper_service import (
    IWebScraperService,
    PlaywrightScraperService,
)
from src.infrastructure.interfaces.llm_service import ILLMService
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
from src.infrastructure.persistence.governing_body_repository_impl import (
    GoverningBodyRepositoryImpl,
)
from src.infrastructure.persistence.llm_processing_history_repository_impl import (
    LLMProcessingHistoryRepositoryImpl,
)
from src.infrastructure.persistence.meeting_repository_impl import MeetingRepositoryImpl
from src.infrastructure.persistence.monitoring_repository_impl import (
    MonitoringRepositoryImpl,
)
from src.infrastructure.persistence.parliamentary_group_repository_impl import (
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
from src.infrastructure.persistence.speaker_repository_impl import SpeakerRepositoryImpl


class DatabaseContainer(containers.DeclarativeContainer):
    """Container for database-related dependencies."""

    config = providers.Configuration()

    engine = providers.Singleton(
        create_engine,
        url=config.database_url,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
    )

    session_factory = providers.Singleton(
        sessionmaker,
        bind=engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )

    session = providers.Factory(
        session_factory,
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

    parliamentary_group_repository = providers.Factory(
        ParliamentaryGroupRepositoryImpl,
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


class ServiceContainer(containers.DeclarativeContainer):
    """Container for external service implementations."""

    config = providers.Configuration()

    llm_service: providers.Provider[ILLMService] = providers.Factory(
        GeminiLLMService,
        api_key=config.google_api_key,
        model_name=config.llm_model,
        temperature=config.llm_temperature,
    )

    storage_service: providers.Provider[IStorageService] = providers.Singleton(
        GCSStorageService,
        bucket_name=config.gcs_bucket_name,
        project_id=config.gcs_project_id,
    )

    web_scraper_service: providers.Provider[IWebScraperService] = providers.Factory(
        PlaywrightScraperService,
        timeout=config.web_scraper_timeout,
        page_load_timeout=config.page_load_timeout,
    )


class UseCaseContainer(containers.DeclarativeContainer):
    """Container for use case implementations."""

    repositories = providers.DependenciesContainer()
    services = providers.DependenciesContainer()

    process_minutes_usecase = providers.Factory(
        ProcessMinutesUseCase,
        meeting_repository=repositories.meeting_repository,
        conversation_repository=repositories.conversation_repository,
        speaker_repository=repositories.speaker_repository,
        llm_service=services.llm_service,
        storage_service=services.storage_service,
    )

    match_speakers_usecase = providers.Factory(
        MatchSpeakersUseCase,
        speaker_repository=repositories.speaker_repository,
        politician_repository=repositories.politician_repository,
        conversation_repository=repositories.conversation_repository,
        llm_service=services.llm_service,
    )

    scrape_politicians_usecase = providers.Factory(
        ScrapePoliticiansUseCase,
        political_party_repository=repositories.political_party_repository,
        politician_repository=repositories.politician_repository,
        web_scraper_service=services.web_scraper_service,
        llm_service=services.llm_service,
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
