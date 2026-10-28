from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.admin import Admin
from app.schemas.admin import AdminCreate, AdminUpdate


class AdminRepository:
    """Repository handling database operations for Admin entity."""

    def get_by_admin_id(self, db: Session, admin_id: str) -> Admin | None:
        """Fetch admin by admin_id identifier."""
        statement = select(Admin).options(selectinload(Admin.user)).where(Admin.admin_id == admin_id)
        return db.scalar(statement)

    def get_multi(self, db: Session, *, skip: int = 0, limit: int = 100) -> list[Admin]:
        """Fetch list of admins."""
        statement = select(Admin).options(selectinload(Admin.user)).order_by(Admin.admin_id).offset(skip).limit(limit)
        return list(db.scalars(statement).all())

    def create(self, db: Session, *, obj_in: AdminCreate) -> Admin:
        """Create new administrator record."""
        db_obj = Admin(
            admin_id=obj_in.admin_id,
            user_id=obj_in.user_id,
            department=obj_in.department,
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj


admin_repo = AdminRepository()

