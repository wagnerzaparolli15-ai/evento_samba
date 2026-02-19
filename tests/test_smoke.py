import os
import pytest

from app import app, db, Cliente


@pytest.fixture
def client(tmp_path, monkeypatch):
    # For CI, use a temporary SQLite DB
    db_path = tmp_path / 'test.db'
    uri = f'sqlite:///{db_path}'
    monkeypatch.setenv('DATABASE_URL', uri)
    # Reimport app context
    from importlib import reload
    reload(app)
    with app.test_client() as c:
        with app.app_context():
            db.create_all()
        yield c


def test_buy_and_admin(client):
    # Simula compra
    resp = client.post('/comprar', data={'nome': 'Smoke Test', 'telefone': '21999990000'})
    assert resp.status_code == 200
    # Verifica admin
    adm = client.get('/admin')
    assert adm.status_code == 200
    assert 'SMOKE TEST' in adm.get_data(as_text=True).upper() or 'SMOKE TEST' in resp.get_data(as_text=True).upper()
