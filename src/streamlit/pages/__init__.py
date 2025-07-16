"""Streamlit page modules"""

from .conferences import manage_conferences
from .governing_bodies import manage_governing_bodies
from .meetings import manage_meetings
from .parliamentary_groups import manage_parliamentary_groups
from .political_parties import manage_political_parties
from .politicians import manage_politicians
from .processes import execute_processes

__all__ = [
    "manage_conferences",
    "manage_governing_bodies",
    "manage_meetings",
    "manage_parliamentary_groups",
    "manage_politicians",
    "manage_political_parties",
    "execute_processes",
]
