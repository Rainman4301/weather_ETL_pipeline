from api_request import mock_fetch_data  # still works, conftest fixed the path

def test_mock_returns_location():
    data = mock_fetch_data()
    assert 'location' in data

def test_mock_has_temperature():
    data = mock_fetch_data()
    assert data['current']['temperature'] == 6