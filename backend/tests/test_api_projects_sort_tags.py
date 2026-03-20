"""Tests for project sort_order and tags features."""
import pytest
from unittest.mock import patch, AsyncMock


@pytest.fixture
def mock_bg_tasks():
    with patch("backend.api.projects._clone_repo", new_callable=AsyncMock) as mock_clone, \
         patch("backend.api.projects._init_local_repo", new_callable=AsyncMock) as mock_init:
        yield mock_clone, mock_init


# ── sort_order: create & default ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_project_default_sort_order(client, mock_bg_tasks):
    resp = await client.post("/api/projects", json={"name": "proj-sort-default"})
    assert resp.status_code == 201
    assert resp.json()["sort_order"] == 0


@pytest.mark.asyncio
async def test_create_project_custom_sort_order(client, mock_bg_tasks):
    resp = await client.post("/api/projects", json={"name": "proj-sort-5", "sort_order": 5})
    assert resp.status_code == 201
    assert resp.json()["sort_order"] == 5


@pytest.mark.asyncio
async def test_update_project_sort_order(client, mock_bg_tasks):
    create_resp = await client.post("/api/projects", json={"name": "proj-sort-update"})
    project_id = create_resp.json()["id"]

    resp = await client.put(f"/api/projects/{project_id}", json={"sort_order": 10})
    assert resp.status_code == 200
    assert resp.json()["sort_order"] == 10


# ── sort_order: list ordering ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_projects_sorted_by_sort_order(client, mock_bg_tasks):
    """Projects should be returned in ascending sort_order, then name."""
    await client.post("/api/projects", json={"name": "alpha", "sort_order": 2})
    await client.post("/api/projects", json={"name": "beta", "sort_order": 0})
    await client.post("/api/projects", json={"name": "gamma", "sort_order": 1})

    resp = await client.get("/api/projects")
    assert resp.status_code == 200
    names = [p["name"] for p in resp.json()]
    assert names.index("beta") < names.index("gamma") < names.index("alpha")


@pytest.mark.asyncio
async def test_list_projects_same_sort_order_sorted_by_name(client, mock_bg_tasks):
    """When sort_order is equal, projects should be sorted alphabetically by name."""
    await client.post("/api/projects", json={"name": "zebra", "sort_order": 0})
    await client.post("/api/projects", json={"name": "apple", "sort_order": 0})
    await client.post("/api/projects", json={"name": "mango", "sort_order": 0})

    resp = await client.get("/api/projects")
    assert resp.status_code == 200
    names = [p["name"] for p in resp.json()]
    assert names.index("apple") < names.index("mango") < names.index("zebra")


# ── sort_order: reorder endpoint ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_reorder_projects(client, mock_bg_tasks):
    r1 = await client.post("/api/projects", json={"name": "reorder-a"})
    r2 = await client.post("/api/projects", json={"name": "reorder-b"})
    r3 = await client.post("/api/projects", json={"name": "reorder-c"})
    id1, id2, id3 = r1.json()["id"], r2.json()["id"], r3.json()["id"]

    # Reverse the order
    resp = await client.put("/api/projects/reorder", json=[
        {"id": id1, "sort_order": 2},
        {"id": id2, "sort_order": 1},
        {"id": id3, "sort_order": 0},
    ])
    assert resp.status_code == 200
    names = [p["name"] for p in resp.json()]
    assert names.index("reorder-c") < names.index("reorder-b") < names.index("reorder-a")


@pytest.mark.asyncio
async def test_reorder_persists(client, mock_bg_tasks):
    """After reorder, a subsequent GET should reflect the new order."""
    r1 = await client.post("/api/projects", json={"name": "persist-a"})
    r2 = await client.post("/api/projects", json={"name": "persist-b"})
    id1, id2 = r1.json()["id"], r2.json()["id"]

    await client.put("/api/projects/reorder", json=[
        {"id": id1, "sort_order": 99},
        {"id": id2, "sort_order": 0},
    ])

    get_resp = await client.get("/api/projects")
    names = [p["name"] for p in get_resp.json()]
    assert names.index("persist-b") < names.index("persist-a")


@pytest.mark.asyncio
async def test_reorder_returns_full_project_list(client, mock_bg_tasks):
    """Reorder endpoint returns all projects, not just the ones in the request."""
    r1 = await client.post("/api/projects", json={"name": "full-a"})
    await client.post("/api/projects", json={"name": "full-b"})
    id1 = r1.json()["id"]

    resp = await client.put("/api/projects/reorder", json=[{"id": id1, "sort_order": 5}])
    assert resp.status_code == 200
    # Both projects returned
    names = [p["name"] for p in resp.json()]
    assert "full-a" in names
    assert "full-b" in names


# ── tags: create & default ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_project_default_tags(client, mock_bg_tasks):
    resp = await client.post("/api/projects", json={"name": "proj-tags-default"})
    assert resp.status_code == 201
    assert resp.json()["tags"] == []


@pytest.mark.asyncio
async def test_create_project_with_tags(client, mock_bg_tasks):
    resp = await client.post("/api/projects", json={"name": "proj-with-tags", "tags": ["work", "ai"]})
    assert resp.status_code == 201
    assert sorted(resp.json()["tags"]) == ["ai", "work"]


@pytest.mark.asyncio
async def test_update_project_tags(client, mock_bg_tasks):
    create_resp = await client.post("/api/projects", json={"name": "proj-update-tags"})
    project_id = create_resp.json()["id"]

    resp = await client.put(f"/api/projects/{project_id}", json={"tags": ["mobile", "backend"]})
    assert resp.status_code == 200
    assert sorted(resp.json()["tags"]) == ["backend", "mobile"]


@pytest.mark.asyncio
async def test_update_project_tags_replaces(client, mock_bg_tasks):
    """Updating tags replaces the whole list, not appends."""
    create_resp = await client.post("/api/projects", json={"name": "proj-tags-replace", "tags": ["old"]})
    project_id = create_resp.json()["id"]

    resp = await client.put(f"/api/projects/{project_id}", json={"tags": ["new"]})
    assert resp.status_code == 200
    assert resp.json()["tags"] == ["new"]


@pytest.mark.asyncio
async def test_update_project_tags_clear(client, mock_bg_tasks):
    """Updating tags to empty list clears tags."""
    create_resp = await client.post("/api/projects", json={"name": "proj-tags-clear", "tags": ["remove-me"]})
    project_id = create_resp.json()["id"]

    resp = await client.put(f"/api/projects/{project_id}", json={"tags": []})
    assert resp.status_code == 200
    assert resp.json()["tags"] == []


# ── tags: /tags endpoint ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_tags_empty(client):
    resp = await client.get("/api/projects/tags")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_list_tags_deduped_and_sorted(client, mock_bg_tasks):
    """Tags endpoint returns unique tags sorted alphabetically."""
    await client.post("/api/projects", json={"name": "tags-proj-1", "tags": ["work", "ai"]})
    await client.post("/api/projects", json={"name": "tags-proj-2", "tags": ["ai", "mobile"]})

    resp = await client.get("/api/projects/tags")
    assert resp.status_code == 200
    assert resp.json() == ["ai", "mobile", "work"]


@pytest.mark.asyncio
async def test_list_tags_no_duplicates(client, mock_bg_tasks):
    """Same tag on multiple projects appears only once."""
    await client.post("/api/projects", json={"name": "dup-tags-1", "tags": ["shared"]})
    await client.post("/api/projects", json={"name": "dup-tags-2", "tags": ["shared"]})

    resp = await client.get("/api/projects/tags")
    assert resp.status_code == 200
    tags = resp.json()
    assert tags.count("shared") == 1


@pytest.mark.asyncio
async def test_list_tags_updates_after_project_update(client, mock_bg_tasks):
    """Tags list updates when a project's tags are changed."""
    create_resp = await client.post("/api/projects", json={"name": "dyn-tags", "tags": ["before"]})
    project_id = create_resp.json()["id"]

    resp1 = await client.get("/api/projects/tags")
    assert "before" in resp1.json()

    await client.put(f"/api/projects/{project_id}", json={"tags": ["after"]})

    resp2 = await client.get("/api/projects/tags")
    assert "after" in resp2.json()
    assert "before" not in resp2.json()


# ── combined: sort + tags preserved on update ─────────────────────────────────


@pytest.mark.asyncio
async def test_sort_order_not_cleared_when_updating_tags(client, mock_bg_tasks):
    """Updating only tags should not reset sort_order."""
    create_resp = await client.post("/api/projects", json={"name": "combo-1", "sort_order": 7})
    project_id = create_resp.json()["id"]

    resp = await client.put(f"/api/projects/{project_id}", json={"tags": ["x"]})
    assert resp.status_code == 200
    assert resp.json()["sort_order"] == 7


@pytest.mark.asyncio
async def test_tags_not_cleared_when_updating_sort_order(client, mock_bg_tasks):
    """Updating only sort_order should not reset tags."""
    create_resp = await client.post("/api/projects", json={"name": "combo-2", "tags": ["y"]})
    project_id = create_resp.json()["id"]

    resp = await client.put(f"/api/projects/{project_id}", json={"sort_order": 3})
    assert resp.status_code == 200
    assert resp.json()["tags"] == ["y"]
