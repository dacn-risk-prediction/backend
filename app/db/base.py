# Import Base and all models so Alembic autogenerate detects them
from app.db.base_class import Base  # noqa: F401
from app.models.academic_class import AcademicClass  # noqa: F401
from app.models.course import Course, CoursePrerequisite  # noqa: F401
from app.models.enrollment import Enrollment  # noqa: F401
from app.models.lecturer import Lecturer  # noqa: F401
from app.models.semester import Semester  # noqa: F401
from app.models.student import Student  # noqa: F401
from app.models.user import User  # noqa: F401
