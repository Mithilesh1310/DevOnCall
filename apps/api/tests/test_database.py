import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.project import Project
from app.models.incident import Incident

@pytest.mark.asyncio
async def test_database_connection_and_crud(db_session: AsyncSession):
    # Create Project
    project = Project(
        name="Test Production Service",
        repo_url="https://github.com/example/prod-service.git",
        default_branch="main"
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)

    assert project.id is not None
    assert project.name == "Test Production Service"

    # Query Project back
    result = await db_session.execute(select(Project).where(Project.id == project.id))
    fetched_project = result.scalar_one_or_none()
    assert fetched_project is not None
    assert fetched_project.name == "Test Production Service"

    # Create Incident associated with Project
    incident = Incident(
        project_id=project.id,
        title="High Memory Usage Alert",
        severity="high",
        status="open",
        source="sentry",
        description="OOM error detected on worker pod"
    )
    db_session.add(incident)
    await db_session.commit()
    await db_session.refresh(incident)

    assert incident.id is not None
    assert incident.project_id == project.id
