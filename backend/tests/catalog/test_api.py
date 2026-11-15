"""Catalog API endpoints."""


def test_list_crops_in_telugu(client) -> None:
    r = client.get("/api/v1/catalog/crops", params={"language": "te"})
    assert r.status_code == 200
    paddy = next(c for c in r.json() if c["crop_canonical"] == "paddy")
    assert paddy["display_name"] == "వరి"


def test_resolve_ambiguous_returns_choices(client) -> None:
    r = client.post("/api/v1/catalog/resolve", json={"text": "gobhi", "language": "hi"})
    body = r.json()
    assert body["status"] == "ambiguous"
    names = {c["crop_canonical"]: c["display_name"] for c in body["candidates"]}
    assert names == {"cabbage": "पत्तागोभी", "cauliflower": "फूलगोभी"}


def test_district_endpoints(client) -> None:
    assert client.get("/api/v1/catalog/districts/575").json()["district_name"] == "Kanniyakumari"
    assert client.get("/api/v1/catalog/districts/999999").status_code == 404
    r = client.get("/api/v1/catalog/districts", params={"name": "Khammam"})
    assert [d["lgd_district_code"] for d in r.json()] == [509]
