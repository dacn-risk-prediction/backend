from typing import Any
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.curriculum import Curriculum, KnowledgeBlock, ProgramStructure
from app.schemas.curriculum import (
    CurriculumCreate,
    CurriculumUpdate,
    KnowledgeBlockCreate,
    KnowledgeBlockUpdate,
    ProgramStructureCreate,
    ProgramStructureUpdate,
)


class CurriculumRepository:
    """Repository handling database operations for Curriculum entity."""

    def get_by_id(self, db: Session, curriculum_id: str) -> Curriculum | None:
        """Fetch curriculum by primary key identifier."""
        statement = (
            select(Curriculum)
            .options(
                selectinload(Curriculum.program_structures).selectinload(ProgramStructure.course),
                selectinload(Curriculum.program_structures).selectinload(ProgramStructure.knowledge_block),
            )
            .where(Curriculum.curriculum_id == curriculum_id)
        )
        return db.scalar(statement)

    def get_multi(
        self,
        db: Session,
        *,
        skip: int = 0,
        limit: int = 100,
        cohort: str | None = None,
        major_code: str | None = None,
    ) -> list[Curriculum]:
        """Fetch list of curriculums with optional cohort and major filtering."""
        statement = select(Curriculum)
        if cohort:
            statement = statement.where(Curriculum.cohort == cohort)
        if major_code:
            statement = statement.where(Curriculum.major_code == major_code)
        statement = statement.order_by(Curriculum.cohort.desc(), Curriculum.curriculum_id).offset(skip).limit(limit)
        return list(db.scalars(statement).all())

    def create(self, db: Session, *, obj_in: CurriculumCreate) -> Curriculum:
        """Create new curriculum definition."""
        db_obj = Curriculum(
            curriculum_id=obj_in.curriculum_id,
            curriculum_name=obj_in.curriculum_name,
            major_code=obj_in.major_code,
            major_name=obj_in.major_name,
            cohort=obj_in.cohort,
            academic_year_start=obj_in.academic_year_start,
            total_credits=obj_in.total_credits,
            base_curriculum_id=obj_in.base_curriculum_id,
            faculty=obj_in.faculty,
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(self, db: Session, *, db_obj: Curriculum, obj_in: CurriculumUpdate | dict[str, Any]) -> Curriculum:
        """Update existing curriculum."""
        update_data = obj_in if isinstance(obj_in, dict) else obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def remove(self, db: Session, *, curriculum_id: str) -> Curriculum | None:
        """Delete curriculum record."""
        obj = self.get_by_id(db, curriculum_id)
        if obj:
            db.delete(obj)
            db.commit()
        return obj


class KnowledgeBlockRepository:
    """Repository handling database operations for KnowledgeBlock entity."""

    def get_by_id(self, db: Session, block_id: str) -> KnowledgeBlock | None:
        """Fetch knowledge block by ID."""
        statement = select(KnowledgeBlock).where(KnowledgeBlock.block_id == block_id)
        return db.scalar(statement)

    def get_multi(self, db: Session, *, skip: int = 0, limit: int = 100) -> list[KnowledgeBlock]:
        """Fetch list of knowledge blocks."""
        statement = select(KnowledgeBlock).order_by(KnowledgeBlock.block_id).offset(skip).limit(limit)
        return list(db.scalars(statement).all())

    def create(self, db: Session, *, obj_in: KnowledgeBlockCreate) -> KnowledgeBlock:
        """Create a new knowledge block."""
        db_obj = KnowledgeBlock(
            block_id=obj_in.block_id,
            block_code=obj_in.block_code,
            block_name_vi=obj_in.block_name_vi,
            block_name_en=obj_in.block_name_en,
            category=obj_in.category,
            required_credits=obj_in.required_credits,
            description=obj_in.description,
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj


class ProgramStructureRepository:
    """Repository handling database operations for ProgramStructure entity."""

    def get_by_id(self, db: Session, structure_id: int) -> ProgramStructure | None:
        """Fetch structure entry by primary key ID."""
        statement = (
            select(ProgramStructure)
            .options(
                selectinload(ProgramStructure.curriculum),
                selectinload(ProgramStructure.knowledge_block),
                selectinload(ProgramStructure.course),
            )
            .where(ProgramStructure.structure_id == structure_id)
        )
        return db.scalar(statement)

    def get_by_curriculum(
        self,
        db: Session,
        *,
        curriculum_id: str,
        skip: int = 0,
        limit: int = 200,
    ) -> list[ProgramStructure]:
        """Fetch program structure allocations for a specific curriculum."""
        statement = (
            select(ProgramStructure)
            .options(
                selectinload(ProgramStructure.knowledge_block),
                selectinload(ProgramStructure.course),
            )
            .where(ProgramStructure.curriculum_id == curriculum_id)
            .order_by(ProgramStructure.structure_id)
            .offset(skip)
            .limit(limit)
        )
        return list(db.scalars(statement).all())


curriculum_repo = CurriculumRepository()
knowledge_block_repo = KnowledgeBlockRepository()
program_structure_repo = ProgramStructureRepository()

