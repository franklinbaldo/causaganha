import pytest
import ibis
from causaganha.storage.repositories.lawyer import LawyerRatingRepository
from causaganha.storage.connection import get_connection
from causaganha.storage.schema import create_schema

@pytest.fixture
def memory_con():
    con = get_connection(":memory:")
    create_schema(con)
    return con

@pytest.fixture
def rating_repo(memory_con):
    return LawyerRatingRepository(memory_con)

def test_save_and_get_lawyer_ratings(rating_repo):
    ratings = [
        {
            "oab_number": "123",
            "oab_state": "RO",
            "lawyer_name": "Test Lawyer",
            "mu": 25.0,
            "sigma": 8.333,
            "total_cases": 1,
            "wins": 1,
            "losses": 0
        }
    ]

    # Save
    rating_repo._sync_save_lawyer_ratings(ratings)

    # Get
    fetched = rating_repo._sync_get_lawyer_ratings([("123", "RO")])
    assert len(fetched) == 1
    assert fetched[0]["lawyer_name"] == "Test Lawyer"
    assert fetched[0]["mu"] == 25.0

    # Update
    ratings[0]["mu"] = 28.0
    ratings[0]["wins"] = 2
    rating_repo._sync_save_lawyer_ratings(ratings)

    # Get updated
    fetched = rating_repo._sync_get_lawyer_ratings([("123", "RO")])
    assert len(fetched) == 1
    assert fetched[0]["mu"] == 28.0
    assert fetched[0]["wins"] == 2

def test_get_lawyer_ratings_empty(rating_repo):
    fetched = rating_repo._sync_get_lawyer_ratings([("999", "RO")])
    assert len(fetched) == 0
