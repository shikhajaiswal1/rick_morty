from app.services import get_filtered_characters


def test_filter_logic(monkeypatch):
    fake_api_response = {
        "info": {"next": None},
        "results": [
            {
                "id": 1,
                "name": "Rick",
                "status": "Alive",
                "species": "Human",
                "origin": {"name": "Earth (C-137)"},
            },
            {
                "id": 2,
                "name": "Morty",
                "status": "Dead",
                "species": "Human",
                "origin": {"name": "Earth (C-137)"},
            },
        ],
    }

    def mock_get(url, *args, **kwargs):
        class MockResponse:
            status_code = 200

            def json(self):
                return fake_api_response

        return MockResponse()

    monkeypatch.setattr("requests.get", mock_get)

    results = get_filtered_characters()
    assert len(results) == 1
    assert results[0]["name"] == "Rick"
