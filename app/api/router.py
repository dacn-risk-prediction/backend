from fastapi import APIRouter

from app.api.routes import (
    auth,
    classes,
    courses,
    curriculums,
    enrollments,
    lecturers,
    semesters,
    students,
    users,
)

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(students.router, prefix="/students", tags=["Students"])
api_router.include_router(lecturers.router, prefix="/lecturers", tags=["Lecturers"])
api_router.include_router(courses.router, prefix="/courses", tags=["Courses"])
api_router.include_router(curriculums.router, prefix="/curriculums", tags=["Curriculums"])
api_router.include_router(semesters.router, prefix="/semesters", tags=["Semesters"])
api_router.include_router(classes.router, prefix="/classes", tags=["Classes"])
api_router.include_router(enrollments.router, prefix="/enrollments", tags=["Enrollments"])
