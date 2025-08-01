# Polibase Project Overview

Polibase (政治活動追跡アプリケーション) is a Political Activity Tracking Application for managing and analyzing Japanese political activities including politician statements, meeting minutes, political promises, and voting records.

## Main Purpose
- Extract and structure political discussions from meeting minutes (PDFs and web pages)
- Track politicians, their affiliations, and statements
- Link speakers in meetings to politicians using LLM-based matching
- Monitor data coverage across Japanese governmental bodies
- Manage parliamentary groups (議員団/会派) and their voting patterns

## Key Features
1. **Minutes Processing**: Extract speeches from meeting PDFs/text
2. **Politician Management**: Scrape and maintain politician data from party websites
3. **Speaker Matching**: LLM-powered linking of speakers to politicians
4. **Conference Member Extraction**: Staged extraction and matching of conference members
5. **Parliamentary Groups**: Track voting blocs within conferences
6. **Data Coverage Monitoring**: Visualize data completeness across Japan
7. **Web UI**: Streamlit-based interface for data management

## System Design Principles
1. Politicians data comes from party websites
2. Speakers and speeches extracted from meeting minutes
3. LLM links speakers to politicians with high accuracy
4. Conference members extracted in stages with manual review
5. Parliamentary groups track voting patterns
6. All data input through Streamlit UI
7. Coverage monitored via dashboards
8. LLM processing history tracked for reproducibility

## Database
- PostgreSQL 15 with SQLAlchemy ORM
- Master data: governing_bodies (1,966 municipalities), conferences, political_parties
- Core tables: meetings, minutes, speakers, politicians, conversations, proposals
- Staging tables for review: extracted_conference_members
- Comprehensive migration system in database/migrations/
