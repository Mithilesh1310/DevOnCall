from fastapi import APIRouter
from app.api.v1.endpoints import status, projects, incidents, agent_runs, github, agent, webhooks, sandbox, browser, whatsapp, staging, brain, observability, deployment, system

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(status.router, tags=["status"])
api_router.include_router(system.router, prefix="/system", tags=["system"])
api_router.include_router(github.router, prefix="/github", tags=["github"])
api_router.include_router(projects.router, prefix="/projects", tags=["projects"])
api_router.include_router(incidents.router, prefix="/incidents", tags=["incidents"])
api_router.include_router(agent_runs.router, prefix="/agent-runs", tags=["agent-runs"])
api_router.include_router(agent.router, prefix="/agent", tags=["agent-runtime"])
api_router.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])
api_router.include_router(sandbox.router, prefix="/sandbox", tags=["sandbox"])
api_router.include_router(browser.router, prefix="/browser", tags=["browser"])
api_router.include_router(whatsapp.router, prefix="/whatsapp", tags=["whatsapp"])
api_router.include_router(staging.router, prefix="/staging", tags=["staging"])
api_router.include_router(brain.router, tags=["brain"])
api_router.include_router(observability.router, prefix="/observability", tags=["observability"])
api_router.include_router(deployment.router, prefix="/deployment", tags=["deployment"])




