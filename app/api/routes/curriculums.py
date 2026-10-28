from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import SessionDep
from app.repositories import curriculum_repo, knowledge_block_repo, program_structure_repo
from app.schemas.curriculum import (
    CurriculumResponse,
    KnowledgeBlockResponse,
    ProgramStructureResponse,
)

router = APIRouter()


@router.get(
    "/",
    response_model=list[CurriculumResponse],
    status_code=status.HTTP_200_OK,
    summary="List all academic curriculums",
)
def list_curriculums(
    db: SessionDep,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    cohort: str | None = Query(default=None, description="Filter by student cohort (e.g. K20)"),
    major_code: str | None = Query(default=None, description="Filter by major code"),
):
    """Retrieve list of academic curriculum programs."""
    return curriculum_repo.get_multi(db, skip=skip, limit=limit, cohort=cohort, major_code=major_code)


@router.get(
    "/knowledge-blocks",
    response_model=list[KnowledgeBlockResponse],
    status_code=status.HTTP_200_OK,
    summary="List all knowledge blocks in curriculums",
)
def list_knowledge_blocks(
    db: SessionDep,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
):
    """Retrieve list of defined academic knowledge blocks."""
    return knowledge_block_repo.get_multi(db, skip=skip, limit=limit)


@router.get(
    "/{curriculum_id}",
    response_model=CurriculumResponse,
    status_code=status.HTTP_200_OK,
    summary="Get curriculum program details by ID",
)
def get_curriculum(curriculum_id: str, db: SessionDep):
    """Retrieve specific curriculum program by its identifier."""
    curriculum = curriculum_repo.get_by_id(db, curriculum_id)
    if not curriculum:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Curriculum '{curriculum_id}' not found",
        )
    return curriculum


@router.get(
    "/{curriculum_id}/structures",
    response_model=list[ProgramStructureResponse],
    status_code=status.HTTP_200_OK,
    summary="Get course allocations and structure for a curriculum",
)
def get_curriculum_structures(
    curriculum_id: str,
    db: SessionDep,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=200, ge=1, le=500),
):
    """Retrieve course layout, required credits, and recommended semesters for a curriculum."""
    curriculum = curriculum_repo.get_by_id(db, curriculum_id)
    if not curriculum:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Curriculum '{curriculum_id}' not found",
        )
    return program_structure_repo.get_by_curriculum(db, curriculum_id=curriculum_id, skip=skip, limit=limit)

