import pytest

from app import create_engine, setup_database

from traces_api.database.tools import recreate_database


@pytest.fixture()
def database_url():
    # return "sqlite://"
    return "postgresql://root:example@localhost/traces"


@pytest.fixture(scope="function")
def sqlalchemy_session(database_url):
    engine = create_engine(database_url)
    session = setup_database(engine)

    recreate_database(engine)

    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def file_hydra_1_binary():
    with open("tests/fixtures/hydra-1_tasks.pcap", "rb") as f:
        return f.read()