from .conftest import create_ann_unit, create_mix


def test_create(client):
    aunit1 = create_ann_unit(client, "First ann unit #1")
    aunit2 = create_ann_unit(client, "Second ann unit #2")

    data = dict(
        name="Mix #1",
        description="Mix description #1",
        labels=["L1", "label2"],
        annotated_units=[
            dict(
                id_annotated_unit=aunit1,
                ip_mapping=[],
                mac_mapping=[],
                timestamp=134
            ),
            dict(
                id_annotated_unit=aunit2,
                ip_mapping=[],
                mac_mapping=[],
                timestamp=123
            ),
        ]
    )
    r = client.post("/mix/create", json=data, content_type="application/json")
    assert r.json["id_mix"]


def test_generate_and_download(client):
    aunit1 = create_ann_unit(client, "First ann unit #1")
    aunit2 = create_ann_unit(client, "Second ann unit #2")

    data = dict(
        name="Mix #1",
        description="Mix description #1",
        labels=["L1", "label2"],
        annotated_units=[
            dict(
                id_annotated_unit=aunit1,
                ip_mapping=[{
                  "original": "1.2.3.4",
                  "replacement": "172.16.0.0"
                }],
                mac_mapping=[{
                  "original": "00:A0:C9:14:C8:29",
                  "replacement": "00:A0:C9:14:C8:29"
                }],
                timestamp=134
            ),
            dict(
                id_annotated_unit=aunit2,
                ip_mapping=[],
                mac_mapping=[],
                timestamp=123
            ),
        ]
    )
    r1 = client.post("/mix/create", json=data, content_type="application/json")
    assert r1.status_code == 200
    id_mix = r1.json["id_mix"]

    r2 = client.post("/mix/%s/generate" % id_mix, json={}, content_type="application/json")
    assert r2.status_code == 200

    r3 = client.get("/mix/%s/generate/status" % id_mix, content_type="application/json")
    assert r3.status_code == 200
    assert r3.json["progress"] >= 0

    r4 = client.get("/mix/%s/download" % id_mix, content_type="application/json")
    assert r4.status_code == 200


def test_create_invalid_input(client):
    r = client.post("/mix/create")
    assert r.status_code == 400


def test_create_invalid_ann_unit(client):
    data = dict(
        name="Mix #1",
        description="Mix description #1",
        labels=["L1", "label2"],
        annotated_units=[
            dict(
                id_annotated_unit=345678,
                ip_mapping=[],
                mac_mapping=[],
                timestamp=134
            ),
            dict(
                id_annotated_unit=45678,
                ip_mapping=[],
                mac_mapping=[],
                timestamp=123
            ),
        ]
    )
    r = client.post("/mix/create", json=data, content_type="application/json")
    assert r.status_code == 404


def test_detail_invalid_id(client):
    r = client.get("/mix/%s/detail" % 4567, content_type="application/json")
    assert r.status_code == 404


def test_download_invalid_id(client):
    r = client.get("/mix/%s/download" % 4567, content_type="application/json")
    assert r.status_code == 404


def test_generate_invalid_id(client):
    r = client.post("/mix/%s/generate" % 4567, content_type="application/json")
    assert r.status_code == 404


def test_generate_status_invalid_id(client):
    r = client.get("/mix/%s/generate/status" % 4567, content_type="application/json")
    assert r.status_code == 404


def test_find(client):
    create_mix(client, "First mix #1")
    create_mix(client, "Second mix #2")
    create_mix(client, "Third mix #3")

    r = client.post("/mix/find", json=dict(name="mix #", operator="AND"), content_type="application/json")
    assert len(r.json["data"]) == 3
    r = client.post("/mix/find", json=dict(name="d mix #", operator="AND"), content_type="application/json")
    assert len(r.json["data"]) == 2
    r = client.post("/mix/find", json=dict(name="Second mix #2", operator="AND"), content_type="application/json")
    assert len(r.json["data"]) == 1

    r = client.post("/mix/find", json=dict(name="Non existing mix", operator="AND"), content_type="application/json")
    assert len(r.json["data"]) == 0


def test_remove_annotated_unit_in_mix(client):
        aunit1 = create_ann_unit(client, "First ann unit #1")
        aunit2 = create_ann_unit(client, "Second ann unit #2")

        data = dict(
            name="Mix #1",
            description="Mix description #1",
            labels=["L1", "label2"],
            annotated_units=[
                dict(
                    id_annotated_unit=aunit1,
                    ip_mapping=[],
                    mac_mapping=[],
                    timestamp=134
                )
            ]
        )
        r = client.post("/mix/create", json=data, content_type="application/json")
        assert r.json["id_mix"]

        r = client.delete("/annotated_unit/%s/delete" % aunit2)
        assert r.status_code == 200

        r = client.delete("/annotated_unit/%s/delete" % aunit1)
        assert r.status_code == 409
