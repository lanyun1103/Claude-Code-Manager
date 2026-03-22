from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models.tag import Tag
from backend.models.project import Project
from backend.schemas.tag import TagCreate, TagUpdate, TagResponse

router = APIRouter(prefix="/api/tags", tags=["tags"])


@router.get("", response_model=list[TagResponse])
async def list_tags(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Tag).order_by(Tag.name.asc()))
    return list(result.scalars().all())


@router.post("", response_model=TagResponse, status_code=201)
async def create_tag(body: TagCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(Tag).where(Tag.name == body.name))
    if existing.scalar_one_or_none():
        raise HTTPException(400, f"Tag '{body.name}' already exists")
    tag = Tag(name=body.name, color=body.color)
    db.add(tag)
    await db.commit()
    await db.refresh(tag)
    return tag


@router.put("/{tag_id}", response_model=TagResponse)
async def update_tag(tag_id: int, body: TagUpdate, db: AsyncSession = Depends(get_db)):
    tag = await db.get(Tag, tag_id)
    if not tag:
        raise HTTPException(404, "Tag not found")

    old_name = tag.name

    if body.name is not None and body.name != old_name:
        # Check for duplicate name
        dup = await db.execute(select(Tag).where(Tag.name == body.name))
        if dup.scalar_one_or_none():
            raise HTTPException(400, f"Tag '{body.name}' already exists")

        # Rename tag across all projects
        result = await db.execute(select(Project))
        for project in result.scalars().all():
            if old_name in (project.tags or []):
                new_tags = [body.name if t == old_name else t for t in project.tags]
                project.tags = new_tags

        tag.name = body.name

    if body.color is not None:
        tag.color = body.color

    await db.commit()
    await db.refresh(tag)
    return tag


@router.delete("/{tag_id}")
async def delete_tag(tag_id: int, db: AsyncSession = Depends(get_db)):
    tag = await db.get(Tag, tag_id)
    if not tag:
        raise HTTPException(404, "Tag not found")

    # Remove tag from all projects
    result = await db.execute(select(Project))
    for project in result.scalars().all():
        if tag.name in (project.tags or []):
            project.tags = [t for t in project.tags if t != tag.name]

    await db.delete(tag)
    await db.commit()
    return {"ok": True}
