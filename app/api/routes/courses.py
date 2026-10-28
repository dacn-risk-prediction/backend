from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import SessionDep
from app.repositories import course_assessment_repo, course_repo
from app.schemas.course import (
    CourseCreate,
    CourseDetailResponse,
    CoursePrerequisiteCreate,
    CoursePrerequisiteResponse,
    CourseResponse,
    CourseUpdate,
)
from app.schemas.course_assessment import CourseAssessmentResponse

router = APIRouter()


@router.get(
    "/",
    response_model=list[CourseResponse],
    status_code=status.HTTP_200_OK,
    summary="List courses with pagination and search",
)
def list_courses(
    db: SessionDep,
    skip: int = Query(default=0, ge=0, description="Offset records"),
    limit: int = Query(default=100, ge=1, le=500, description="Limit records"),
    search: str | None = Query(default=None, description="Search by course code or title"),
):
    """Retrieve multiple courses with optional search and pagination."""
    return course_repo.get_multi(db, skip=skip, limit=limit, search=search)


@router.post(
    "/",
    response_model=CourseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new course",
)
def create_course(course_in: CourseCreate, db: SessionDep):
    """Register a new course into the system."""
    existing = course_repo.get_by_code(db, course_in.course_code)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Course with code '{course_in.course_code}' already exists",
        )
    return course_repo.create(db, obj_in=course_in)


@router.get(
    "/{course_code}",
    response_model=CourseDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get course details with prerequisites",
)
def get_course(course_code: str, db: SessionDep):
    """Retrieve a course by its code, including prerequisite requirements."""
    course = course_repo.get_with_prerequisites(db, course_code)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Course '{course_code}' not found",
        )
    return course


@router.put(
    "/{course_code}",
    response_model=CourseResponse,
    status_code=status.HTTP_200_OK,
    summary="Update a course",
)
def update_course(course_code: str, course_in: CourseUpdate, db: SessionDep):
    """Update details of an existing course."""
    course = course_repo.get_by_code(db, course_code)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Course '{course_code}' not found",
        )
    return course_repo.update(db, db_obj=course, obj_in=course_in)


@router.delete(
    "/{course_code}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a course",
)
def delete_course(course_code: str, db: SessionDep):
    """Delete a course by its unique code."""
    course = course_repo.get_by_code(db, course_code)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Course '{course_code}' not found",
        )
    course_repo.remove(db, course_code=course_code)
    return None


@router.post(
    "/{course_code}/prerequisites",
    response_model=CoursePrerequisiteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a prerequisite requirement to a course",
)
def add_prerequisite(
    course_code: str,
    prereq_in: CoursePrerequisiteCreate,
    db: SessionDep,
):
    """Link a prerequisite relationship to a course."""
    if prereq_in.course_code != course_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="URL course_code does not match payload course_code",
        )
    target_course = course_repo.get_by_code(db, course_code)
    related_course = course_repo.get_by_code(db, prereq_in.related_course_code)
    if not target_course or not related_course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Either target course or prerequisite course does not exist",
        )
    return course_repo.add_prerequisite(db, obj_in=prereq_in)


@router.get(
    "/{course_code}/assessment",
    response_model=CourseAssessmentResponse,
    status_code=status.HTTP_200_OK,
    summary="Get assessment weights breakdown for a course",
)
def get_course_assessment(course_code: str, db: SessionDep):
    """Retrieve score component weights (quiz, lab, btl, midterm, final) for a course."""
    assessment = course_assessment_repo.get_by_course_code(db, course_code)
    if not assessment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Assessment breakdown for course '{course_code}' not found",
        )
    return assessment


@router.delete(
    "/prerequisites/{prerequisite_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a prerequisite relationship",
)
def delete_prerequisite(prerequisite_id: int, db: SessionDep):
    """Delete a prerequisite rule by its ID."""
    success = course_repo.remove_prerequisite(db, prerequisite_id=prerequisite_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prerequisite with ID {prerequisite_id} not found",
        )
    return None
