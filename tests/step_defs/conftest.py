
import os
import pytest
from pytest_bdd import given
from causaganha.config import DB_PATH

@given("the system is in a clean state")
def clean_state():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
