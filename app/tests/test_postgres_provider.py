from app.providers.postgres_provider import PostgresProvider


class DummyRepo:
    def __init__(self):
        self.last = None

    def run_query(self, sql, params=None, **kwargs):
        # record call and return a synthetic row appropriate for KPI
        self.last = (sql, params)
        # return a row matching salaire_net_total, masse, nb_employes_uniques, deductions
        return [(1000.0, 800.0, 10, -200.0)]


def make_provider_with_repo(repo):
    # Create instance without running __init__ to avoid real DB calls
    p = PostgresProvider.__new__(PostgresProvider)
    p.repo = repo
    p.dsn = "postgresql://user:***@localhost/db"
    return p


def test_get_kpis_year():
    repo = DummyRepo()
    p = make_provider_with_repo(repo)

    res = p.get_kpis("2025")

    assert isinstance(res, dict)
    assert res["salaire_net_total"] == 1000.0
    # verify params are a 2-tuple for year
    assert isinstance(repo.last[1], tuple) and len(repo.last[1]) == 2


def test_get_kpis_month():
    repo = DummyRepo()
    p = make_provider_with_repo(repo)

    res = p.get_kpis("2025-08")
    assert res["masse_salariale"] == 800.0
    # verify params single-element tuple
    assert isinstance(repo.last[1], tuple) and len(repo.last[1]) == 1


def test_get_kpis_date():
    repo = DummyRepo()
    p = make_provider_with_repo(repo)

    res = p.get_kpis("2025-08-15")
    assert res["nb_employes"] == 10
    assert isinstance(repo.last[1], tuple) and len(repo.last[1]) == 1
