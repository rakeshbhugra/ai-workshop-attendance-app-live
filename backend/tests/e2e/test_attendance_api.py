from httpx import AsyncClient


async def create_sample(client: AsyncClient):
    for id, name in [("A", "Alice"), ("B", "Bob")]:
        response = await client.post(
            "/api/v1/students",
            json={
                "id": id,
                "name": name,
                "email": f"{id.lower()}@example.com",
                "college": "College",
            },
        )
        assert response.status_code == 201
    response = await client.post(
        "/api/v1/workshops", json={"id": "w", "title": "Workshop", "studentIds": ["A", "B"]}
    )
    assert response.status_code == 201
    for id, day in [("past", "2000-01-01"), ("future", "2099-01-01")]:
        response = await client.post(
            "/api/v1/sessions",
            json={
                "id": id,
                "workshopId": "w",
                "title": "Session",
                "date": day,
                "start": "10:00",
                "end": "12:00",
            },
        )
        assert response.status_code == 201


async def test_http_contract_and_persistence(client):
    await create_sample(client)
    assert (await client.get("/api/v1/workshops")).json()[0]["studentIds"] == ["A", "B"]
    assert len((await client.get("/api/v1/sessions?workshopId=w")).json()) == 2
    assert len((await client.get("/api/v1/students?workshopId=w")).json()) == 2
    records = (await client.get("/api/v1/sessions/past/attendance")).json()
    assert all(r["status"] == "unmarked" for r in records)
    response = await client.patch(
        "/api/v1/sessions/past/attendance",
        json={
            "records": [
                {"studentId": "A", "status": "present", "checkIn": "10:00", "checkOut": "11:45"}
            ]
        },
    )
    assert response.status_code == 200
    assert (await client.get("/api/v1/sessions/past/attendance")).json()[0]["checkOut"] == "11:45"
    assert (await client.patch("/api/v1/students/A", json={"active": False})).status_code == 200
    assert len((await client.get("/api/v1/sessions/past/attendance")).json()) == 2
    assert len((await client.get("/api/v1/sessions/future/attendance")).json()) == 1
    response = await client.post(
        "/api/v1/students",
        json={"id": "C", "name": "Cara", "email": "cara@example.com", "workshopId": "w"},
    )
    assert response.status_code == 201
    assert len((await client.get("/api/v1/sessions/future/attendance")).json()) == 2
    assert (
        await client.put("/api/v1/workshops/w/students", json={"studentIds": []})
    ).status_code == 200
    assert (await client.get("/api/v1/sessions/future/attendance")).json() == []


async def test_attendance_access_and_errors(anonymous, client):
    await client.post("/api/v1/auth/logout")
    assert (await anonymous.get("/api/v1/students")).status_code == 401
    login = await client.get("/api/v1/auth/dev/login")
    await client.get(login.headers["location"])
    await create_sample(client)
    duplicate = await client.post(
        "/api/v1/students", json={"id": "A", "name": "Duplicate", "email": "new@example.com"}
    )
    assert duplicate.status_code == 409
    assert (await client.get("/api/v1/sessions/missing/attendance")).status_code == 404
    response = await client.patch(
        "/api/v1/sessions/past/attendance",
        json={
            "records": [
                {"studentId": "A", "status": "present"},
                {"studentId": "unknown", "status": "absent"},
            ]
        },
    )
    assert response.status_code == 422
    assert (await client.get("/api/v1/sessions/past/attendance")).json()[0]["status"] == "unmarked"
    bad = await client.patch(
        "/api/v1/students/A",
        json={"name": "Hijack"},
        headers={"Origin": "https://untrusted.example"},
    )
    assert bad.status_code == 403


async def test_future_marked_roster_survives_unenrollment(client):
    await create_sample(client)
    marked = await client.patch(
        "/api/v1/sessions/future/attendance",
        json={
            "records": [
                {"studentId": "A", "status": "absent"},
                {"studentId": "B", "status": "unmarked"},
            ]
        },
    )
    assert marked.status_code == 200
    await client.put("/api/v1/workshops/w/students", json={"studentIds": []})
    rows = (await client.get("/api/v1/sessions/future/attendance")).json()
    assert rows == [{"studentId": "A", "status": "absent", "checkIn": "", "checkOut": ""}]
