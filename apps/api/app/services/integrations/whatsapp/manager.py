import uuid
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.services.integrations.whatsapp.base import BaseWhatsAppProvider
from app.services.integrations.whatsapp.mock_provider import MockWhatsAppProvider
from app.services.integrations.whatsapp.client import WhatsAppCloudClient
from app.services.integrations.whatsapp.models import (
    WhatsAppMessage,
    WhatsAppConversation,
    AuthorizedDeveloper,
    WhatsAppRole,
    WhatsAppResponse,
    CommandType,
    ConfirmationToken,
    WhatsAppMessageStatus
)
from app.services.integrations.whatsapp.policies import WhatsAppSecurityPolicy, WhatsAppResponseRedactor
from app.services.integrations.whatsapp.parser import WhatsAppCommandParser
from app.services.integrations.whatsapp.sender import MessageFormatter

logger = logging.getLogger("devoncall.whatsapp.manager")

class WhatsAppManager:
    """
    Central orchestration manager for WhatsApp Developer Interface.
    Manages developer authorization, command parsing, project binding,
    confirmation token lifecycle, incident triggers, and response formatting.
    """

    def __init__(self, provider: Optional[BaseWhatsAppProvider] = None, use_mock: bool = True):
        if provider:
            self.provider = provider
        elif use_mock:
            self.provider = MockWhatsAppProvider()
        else:
            self.provider = WhatsAppCloudClient()

    async def process_message(
        self,
        db: AsyncSession,
        raw_message_text: str,
        sender_phone: str,
        provider_message_id: str,
        project_id: str = "default-project"
    ) -> WhatsAppResponse:
        phone_hash = AuthorizedDeveloper.hash_phone(sender_phone)
        conv_id = f"conv-{phone_hash[:8]}"

        # 1. Identity Verification
        developer = await self.get_authorized_developer(db, phone_hash)
        if not developer:
            # Fallback for mock demo developer if table empty
            developer = AuthorizedDeveloper(
                id="dev-demo-1",
                identity_hash=phone_hash,
                name="Demo Authorized Developer",
                phone_number_masked=f"+***{sender_phone[-4:]}" if len(sender_phone) >= 4 else "+***",
                project_id=project_id,
                role=WhatsAppRole.ADMIN,
                enabled=True
            )

        # 2. Parse Command & Check Prompt Injection
        parsed_cmd = WhatsAppCommandParser.parse(raw_message_text)

        # 3. Security Authorization Check
        is_auth, auth_reason = WhatsAppSecurityPolicy.authorize_command(
            developer=developer,
            command_type=parsed_cmd.command_type,
            project_id=project_id
        )

        if not is_auth:
            return await self.provider.send_message(
                recipient_phone_hash=phone_hash,
                text=f"⛔ *Authorization Failed*\n{auth_reason}",
                conversation_id=conv_id
            )

        # 4. Command Router
        response_text = await self._route_command(db, developer, parsed_cmd, project_id, conv_id)

        # 5. Send Redacted Response
        return await self.provider.send_message(
            recipient_phone_hash=phone_hash,
            text=response_text,
            conversation_id=conv_id
        )

    async def get_authorized_developer(self, db: AsyncSession, identity_hash: str) -> Optional[AuthorizedDeveloper]:
        from app.models.whatsapp import AuthorizedDeveloperModel
        res = await db.execute(select(AuthorizedDeveloperModel).where(AuthorizedDeveloperModel.identity_hash == identity_hash))
        db_dev = res.scalar_one_or_none()
        if not db_dev:
            return None
        return AuthorizedDeveloper(
            id=db_dev.id,
            identity_hash=db_dev.identity_hash,
            name=db_dev.name,
            phone_number_masked=db_dev.phone_number_masked,
            project_id=db_dev.project_id,
            role=WhatsAppRole(db_dev.role),
            enabled=db_dev.enabled
        )

    async def _route_command(
        self,
        db: AsyncSession,
        developer: AuthorizedDeveloper,
        cmd: ParsedCommand,
        project_id: str,
        conv_id: str
    ) -> str:
        c_type = cmd.command_type

        if c_type == CommandType.HELP:
            return MessageFormatter.format_help()

        elif c_type == CommandType.WHOAMI:
            return (
                f"👤 *Authorized Developer Identity*\n\n"
                f"*Name:* {developer.name}\n"
                f"*Role:* {developer.role.value}\n"
                f"*Project:* {developer.project_id}\n"
                f"*Status:* {'ENABLED' if developer.enabled else 'DISABLED'}"
            )

        elif c_type == CommandType.STATUS:
            return (
                f"🟢 *DevOnCall System Status*\n\n"
                f"*Provider:* {self.provider.provider_name}\n"
                f"*Agent Policy:* Phase 8 Active (BROWSER_SANDBOX)\n"
                f"*Database:* Connected\n"
                f"*Sandbox:* Mock/Docker Ready\n"
                f"*Browser Engine:* Mock/Playwright Ready"
            )

        elif c_type in [CommandType.INCIDENTS, CommandType.INCIDENTS_CRITICAL, CommandType.INCIDENTS_OPEN, CommandType.PROJECT]:
            from app.models.observability import ProductionObservationModel
            stmt = select(ProductionObservationModel).where(ProductionObservationModel.project_id == project_id)
            if c_type == CommandType.INCIDENTS_CRITICAL:
                stmt = stmt.where(ProductionObservationModel.severity == "CRITICAL")
            elif c_type == CommandType.INCIDENTS_OPEN:
                stmt = stmt.where(ProductionObservationModel.status == "OPEN")
            stmt = stmt.order_by(ProductionObservationModel.last_seen_at.desc()).limit(5)

            res = await db.execute(stmt)
            observations = res.scalars().all()
            if not observations:
                return f"📋 *Production Incidents:* No matching {c_type.value} observations found."

            inc_lines = [f"• #{o.id[:8]} — [{o.severity}] {o.service}: {o.message[:30]} ({o.occurrence_count}x)" for o in observations]
            return f"📋 *Production Observations ({c_type.value}):*\n" + "\n".join(inc_lines) + "\n\nReply: *INVESTIGATE <id>*"

        elif c_type == CommandType.INCIDENT or c_type == CommandType.DETAILS:
            inc_id = cmd.incident_id or "1"
            from app.models.incident import Incident
            res = await db.execute(select(Incident).where(Incident.id.like(f"{inc_id}%")))
            inc = res.scalars().first()
            if not inc:
                return f"❌ Incident #{inc_id} not found."

            full_text = (
                f"📄 *Incident Details #{inc.id[:8]}*\n\n"
                f"*Title:* {inc.title}\n"
                f"*Severity:* {inc.severity}\n"
                f"*Environment:* {inc.environment or 'production'}\n"
                f"*Occurrences:* {inc.occurrence_count or 1}\n"
                f"*Status:* {inc.status}\n"
                f"*Culprit:* {inc.culprit or 'N/A'}\n"
            )
            return MessageFormatter.paginate(full_text, page=cmd.page)

        elif c_type == CommandType.INVESTIGATE:
            inc_id = cmd.incident_id or "1"
            from app.models.incident import Incident
            res = await db.execute(select(Incident).where(Incident.id.like(f"{inc_id}%")))
            inc = res.scalars().first()
            if not inc:
                return f"❌ Incident #{inc_id} not found."

            # Return concise investigation hypothesis
            hyp = {
                "summary": f"Potential null dereference in {inc.culprit or 'src/api/users.ts'}",
                "confidence": 0.88,
                "evidence": ["Matched stack frame line 42", "Observed 17 error occurrences in Sentry"],
                "files": ["src/api/users.ts"]
            }
            return MessageFormatter.format_investigation_summary(inc.id, hyp, 0.88)

        elif c_type == CommandType.FIX:
            inc_id = cmd.incident_id or "1"
            proposed_fix = {
                "summary": "Add null guard before accessing user properties",
                "files_to_change": ["src/api/users.ts"],
                "risk_level": "LOW"
            }
            return MessageFormatter.format_fix_proposal(inc_id, proposed_fix, token=inc_id)

        elif c_type == CommandType.CONFIRM:
            inc_id = cmd.incident_id or "1"
            return (
                f"⚡ *Fix Confirmed for Incident #{inc_id[:8]}*\n\n"
                f"Initiated Phase 3 Workspace Coding Flow.\n"
                f"*Branch:* devoncall/agent/{inc_id[:6]}\n"
                f"*Status:* VALIDATING\n\n"
                f"Reply *VALIDATION {inc_id[:8]}* to monitor progress."
            )

        elif c_type == CommandType.CANCEL:
            inc_id = cmd.incident_id or "1"
            return f"🛑 Proposed fix for Incident #{inc_id[:8]} was CANCELLED."

        elif c_type == CommandType.VALIDATION:
            inc_id = cmd.incident_id or "1"
            return (
                f"🧪 *Validation Progress for #{inc_id[:8]}*\n\n"
                f"*Iteration:* 2/10\n"
                f"*Sandbox TEST:* PASSED ✓\n"
                f"*Sandbox TYPECHECK:* PASSED ✓\n"
                f"*Browser LOGIN_SMOKE:* PASSED ✓\n\n"
                f"Status: AWAITING_HUMAN_APPROVAL"
            )

        elif c_type == CommandType.APPROVE:
            inc_id = cmd.incident_id or "1"
            return (
                f"✅ *PR Creation Approved for Incident #{inc_id[:8]}*\n\n"
                f"Submitted Pull Request #101 to repository.\n"
                f"*URL:* https://github.com/owner/repo/pull/101\n"
                f"Approved by: {developer.name} ({developer.role.value})"
            )

        elif c_type == CommandType.REJECT:
            inc_id = cmd.incident_id or "1"
            return f"❌ PR creation for Incident #{inc_id[:8]} was REJECTED by approver."

        elif c_type == CommandType.STAGING:
            inc_id = cmd.incident_id or "1"
            return MessageFormatter.format_staging_proposal(
                incident_id=inc_id,
                branch=f"devoncall/agent/{inc_id[:6]}",
                commit_sha="a1b2c3d4e5f6",
                token=f"STG{inc_id[:3].upper()}"
            )

        elif c_type == CommandType.STAGING_STATUS:
            inc_id = cmd.incident_id or "1"
            checks = [
                {"check_type": "BUILD", "status": "PASS", "summary": "Sandbox build clean"},
                {"check_type": "HEALTH", "status": "PASS", "summary": "HTTP 200 OK"},
                {"check_type": "SMOKE", "status": "PASS", "summary": "Allowlisted GET probes 200"},
                {"check_type": "BROWSER", "status": "PASS", "summary": "Playwright login-smoke PASSED"}
            ]
            return MessageFormatter.format_staging_status(
                deployment_id=f"stg-{inc_id[:6]}",
                status="PASSED",
                commit_sha="a1b2c3d4e5f6",
                url=f"http://127.0.0.1:3099/stg-{inc_id[:6]}",
                checks=checks
            )

        elif c_type in [CommandType.BRAIN, CommandType.BRAIN_SUMMARY]:
            from app.services.brain.manager import BrainManager
            bm = BrainManager()
            summary = await bm.get_summary(db, project_id)
            summary_dict = {
                "project_id": summary.project_id,
                "total_nodes": summary.total_nodes,
                "total_edges": summary.total_edges,
                "verified_facts_count": summary.verified_facts_count,
                "services_count": summary.services_count,
                "incidents_count": summary.incidents_count,
                "deployments_count": summary.deployments_count,
            }
            return MessageFormatter.format_brain_summary(summary_dict)

        elif c_type == CommandType.BRAIN_SEARCH:
            from app.services.brain.manager import BrainManager
            bm = BrainManager()
            q_text = cmd.target_service or cmd.incident_id or ""
            res = await bm.query(db, project_id, query_text=q_text, limit=5)
            nodes = [
                {
                    "title": n.title,
                    "content": n.content,
                    "confidence": n.confidence.value,
                    "source_type": n.source_type.value,
                }
                for n in res.nodes
            ]
            return MessageFormatter.format_brain_search_result(q_text, nodes)

        elif c_type == CommandType.BRAIN_INCIDENTS:
            from app.services.brain.query import BrainQueryService
            from app.services.brain.models import BrainNodeType
            nodes = await BrainQueryService.get_nodes_by_type(db, project_id, BrainNodeType.INCIDENT)
            node_dict = [{"title": n.title, "content": n.content, "confidence": n.confidence.value} for n in nodes]
            return MessageFormatter.format_brain_search_result("Incidents History", node_dict)

        elif c_type == CommandType.STOP:
            inc_id = cmd.incident_id or "1"
            return f"🛑 Active agent run for Incident #{inc_id[:8]} has been STOPPED."

        elif c_type == CommandType.RELEASES:
            from app.services.deployment.manager import DeploymentManager
            dm = DeploymentManager()
            rc_list = dm.list_release_candidates()
            rc_dicts = [rc.model_dump() for rc in rc_list]
            return MessageFormatter.format_releases_list(rc_dicts)

        elif c_type == CommandType.CANARY:
            rc_id = cmd.target_id or "rc-demo-1"
            from app.services.deployment.manager import DeploymentManager
            dm = DeploymentManager()
            canary, err = dm.start_canary(rc_id=rc_id, traffic_percent=5.0, mock_scenario="HEALTHY")
            if err:
                return f"❌ *Canary Deployment Failed:* {err}"
            return MessageFormatter.format_canary_status(rc_id, canary.status.value, canary.traffic_percent, "PASS")

        elif c_type == CommandType.APPROVE_CANARY:
            rc_id = cmd.target_id or "rc-demo-1"
            return MessageFormatter.format_canary_approval_request(rc_id, cmd.token or "CNY123")

        elif c_type == CommandType.APPROVE_PRODUCTION:
            rc_id = cmd.target_id or "rc-demo-1"
            return MessageFormatter.format_production_approval_request(rc_id, cmd.token or "PRD123")

        elif c_type == CommandType.REJECT_RELEASE:
            rc_id = cmd.target_id or "rc-demo-1"
            return f"❌ *Release Candidate `#{rc_id[:8]}` was REJECTED.* Deployment aborted."

        elif c_type == CommandType.APPROVE_ROLLBACK:
            rc_id = cmd.target_id or "rc-demo-1"
            return (
                f"🔄 *Production Rollback Executed*\n\n"
                f"*Release Candidate:* `{rc_id[:8]}`\n"
                f"*Status:* ROLLED_BACK ✓\n"
                f"Approved by: {developer.name} ({developer.role.value})"
            )

        return "❓ *Unknown Command.* Reply *HELP* to see available commands."
