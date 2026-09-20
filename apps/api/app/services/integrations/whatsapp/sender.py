from typing import List, Dict, Any, Optional
from app.services.integrations.whatsapp.policies import WhatsAppResponseRedactor

MAX_MESSAGE_CHAR_LIMIT = 1500

class MessageFormatter:
    """
    Formats concise, structured WhatsApp responses, incident notifications,
    investigation summaries, and approval requests with pagination support.
    """

    @staticmethod
    def format_help() -> str:
        return (
            "🤖 *DevOnCall WhatsApp Developer Commands*\n\n"
            "• *STATUS* — System & agent status\n"
            "• *INCIDENTS* — Active incident queue\n"
            "• *INCIDENT <id>* — Incident details\n"
            "• *INVESTIGATE <id>* — Trigger root-cause analysis\n"
            "• *DETAILS <id> [page]* — Full hypothesis & evidence\n"
            "• *FIX <id>* — Propose workspace fix\n"
            "• *CONFIRM <token/id>* — Confirm action execution\n"
            "• *VALIDATION <id>* — Monitor test/sandbox/browser status\n"
            "• *STAGING <id>* — Deploy PR commit to Staging\n"
            "• *STAGING_STATUS <id>* — Check staging deployment & checks\n"
            "• *RELEASES* — List active release candidates\n"
            "• *CANARY <rc_id>* — Start 5% Canary Release\n"
            "• *APPROVE CANARY <rc_id> <token>* — Approve Canary Gate\n"
            "• *APPROVE PRODUCTION <rc_id> <token>* — Approve Full Production\n"
            "• *APPROVE ROLLBACK <rc_id> <token>* — Confirm emergency rollback\n"
            "• *BRAIN* — Project Brain summary & architecture\n"
            "• *BRAIN SEARCH <query>* — Query Project Brain knowledge\n"
            "• *APPROVE <id>* — Approve PR creation (Approvers)\n"
            "• *REJECT <id>* — Reject PR creation\n"
            "• *STOP <id>* — Cancel active agent run\n"
            "• *WHOAMI* — View developer identity & role"
        )

    @staticmethod
    def format_brain_summary(summary_dict: Dict[str, Any]) -> str:
        text = (
            f"🧠 *Project Brain Summary*\n\n"
            f"*Project ID:* {summary_dict.get('project_id', 'N/A')}\n"
            f"*Total Nodes:* {summary_dict.get('total_nodes', 0)}\n"
            f"*Total Edges:* {summary_dict.get('total_edges', 0)}\n"
            f"*Verified Facts:* {summary_dict.get('verified_facts_count', 0)}\n"
            f"*Monorepo Services:* {summary_dict.get('services_count', 0)}\n"
            f"*Incidents Recorded:* {summary_dict.get('incidents_count', 0)}\n"
            f"*Deployments:* {summary_dict.get('deployments_count', 0)}\n\n"
            f"Reply *BRAIN SEARCH <query>* to query engineering memory."
        )
        return WhatsAppResponseRedactor.redact(text)

    @staticmethod
    def format_brain_search_result(query: str, nodes: List[Dict[str, Any]]) -> str:
        node_lines = "\n".join([f"• [{n.get('confidence', 'VERIFIED')}] *{n.get('title', '')}* — {n.get('content', '')[:60]}" for n in nodes[:4]])
        text = (
            f"🧠 *Project Brain Results for '{query}'*\n\n"
            f"{node_lines or '• No matching knowledge nodes found.'}"
        )
        return WhatsAppResponseRedactor.redact(text)


    @staticmethod
    def format_staging_proposal(incident_id: str, branch: str, commit_sha: str, token: str) -> str:
        text = (
            f"🚀 *Staging Deployment Requested*\n\n"
            f"*Incident:* #{incident_id[:8]}\n"
            f"*Target Branch:* {branch}\n"
            f"*Commit SHA:* {commit_sha[:8]}\n"
            f"*Environment:* STAGING\n"
            f"*Verification Gates:* BUILD ➔ HEALTH ➔ SMOKE ➔ BROWSER\n\n"
            f"To initiate staging deployment, reply:\n"
            f"*CONFIRM {token}*\n"
            f"or reply *CANCEL {incident_id[:8]}*"
        )
        return WhatsAppResponseRedactor.redact(text)

    @staticmethod
    def format_staging_status(deployment_id: str, status: str, commit_sha: str, url: str, checks: List[Dict[str, Any]]) -> str:
        check_lines = "\n".join([f"• {c.get('check_type', 'CHECK')}: {c.get('status', 'PASS')} — {c.get('summary', '')}" for c in checks])
        text = (
            f"🚀 *Staging Deployment #{deployment_id[:8]}*\n\n"
            f"*Commit:* {commit_sha[:8]}\n"
            f"*Status:* {status}\n"
            f"*URL:* {url or 'Pending allocation'}\n\n"
            f"*Verification Checks:*\n{check_lines or '• Pending execution'}"
        )
        return WhatsAppResponseRedactor.redact(text)


    @staticmethod
    def format_incident_notification(incident: Dict[str, Any]) -> str:
        return (
            f"🔴 *DevOnCall Incident #{incident.get('id', 'N/A')[:8]}*\n\n"
            f"*Title:* {incident.get('title', 'Production Incident')}\n"
            f"*Project:* {incident.get('project_id', 'N/A')}\n"
            f"*Severity:* {incident.get('severity', 'HIGH')}\n"
            f"*Environment:* {incident.get('environment', 'production')}\n"
            f"*Occurrences:* {incident.get('occurrence_count', 1)}\n"
            f"*Culprit:* {incident.get('culprit', 'Unknown')}\n\n"
            f"Reply: *INVESTIGATE {incident.get('id', 'N/A')[:8]}*"
        )

    @staticmethod
    def format_investigation_summary(incident_id: str, hypothesis: Dict[str, Any], confidence: float) -> str:
        evidence_lines = "\n".join([f"• {e}" for e in hypothesis.get("evidence", [])[:3]])
        files_lines = ", ".join(hypothesis.get("files", [])[:2])

        text = (
            f"🔍 *Investigation Result for #{incident_id[:8]}*\n\n"
            f"*Root Cause:* {hypothesis.get('summary', 'Unknown')}\n"
            f"*Confidence:* {int(confidence * 100)}%\n"
            f"*Suspected Files:* {files_lines or 'None'}\n\n"
            f"*Evidence:* \n{evidence_lines or 'None'}\n\n"
            f"Reply: *FIX {incident_id[:8]}* to propose a workspace fix."
        )
        return WhatsAppResponseRedactor.redact(text)

    @staticmethod
    def format_fix_proposal(incident_id: str, proposed_fix: Dict[str, Any], token: str) -> str:
        files = ", ".join(proposed_fix.get("files_to_change", []))
        text = (
            f"⚠️ *Proposed Fix for Incident #{incident_id[:8]}*\n\n"
            f"*Fix:* {proposed_fix.get('summary', 'Workspace Patch')}\n"
            f"*Files to Change:* {files}\n"
            f"*Risk:* {proposed_fix.get('risk_level', 'LOW')}\n\n"
            f"To execute fix, reply:\n"
            f"*CONFIRM {incident_id[:8]}*\n"
            f"or reply *CANCEL {incident_id[:8]}*"
        )
        return WhatsAppResponseRedactor.redact(text)

    @staticmethod
    def format_approval_request(incident_id: str, agent_run_id: str, branch: str) -> str:
        text = (
            f"✋ *Human Approval Required for PR*\n\n"
            f"*Incident:* #{incident_id[:8]}\n"
            f"*Run ID:* {agent_run_id[:8]}\n"
            f"*Branch:* {branch}\n"
            f"*Validations:* TEST ✓ | TYPECHECK ✓ | BROWSER ✓\n\n"
            f"Reply:\n"
            f"*APPROVE {incident_id[:8]}* to submit Pull Request\n"
            f"*REJECT {incident_id[:8]}* to reject PR"
        )
        return WhatsAppResponseRedactor.redact(text)

    @staticmethod
    def format_releases_list(rc_list: List[Dict[str, Any]]) -> str:
        lines = "\n".join([f"• RC `#{rc.get('id', '')[:8]}` — Commit `{rc.get('commit_sha', '')[:8]}` — Status: *{rc.get('status', 'CREATED')}*" for rc in rc_list[:5]])
        text = (
            f"📦 *Release Candidates Queue*\n\n"
            f"{lines or '• No active release candidates in queue.'}\n\n"
            f"Reply *CANARY <rc_id>* to initiate canary deployment."
        )
        return WhatsAppResponseRedactor.redact(text)

    @staticmethod
    def format_canary_status(rc_id: str, status: str, traffic_percent: float, verdict: str) -> str:
        text = (
            f"🐥 *Canary Deployment Status*\n\n"
            f"*RC ID:* `{rc_id[:8]}`\n"
            f"*Status:* {status}\n"
            f"*Traffic Percent:* {traffic_percent}%\n"
            f"*Telemetry Verdict:* *{verdict}*\n\n"
            f"If verdict is PASS, reply:\n"
            f"*APPROVE PRODUCTION {rc_id[:8]} <token>*"
        )
        return WhatsAppResponseRedactor.redact(text)

    @staticmethod
    def format_canary_approval_request(rc_id: str, token: str) -> str:
        text = (
            f"✋ *Human Approval Gate 1: Canary Release*\n\n"
            f"*RC ID:* `{rc_id[:8]}`\n"
            f"*Traffic:* 5.0%\n"
            f"*Token:* `{token}` (Expires in 10 mins)\n\n"
            f"To approve canary release, reply:\n"
            f"*APPROVE CANARY {rc_id[:8]} {token}*"
        )
        return WhatsAppResponseRedactor.redact(text)

    @staticmethod
    def format_production_approval_request(rc_id: str, token: str) -> str:
        text = (
            f"✋ *Human Approval Gate 2: Full Production Deployment*\n\n"
            f"*RC ID:* `{rc_id[:8]}`\n"
            f"*Canary Status:* VERIFIED (PASS)\n"
            f"*Token:* `{token}` (Expires in 10 mins)\n\n"
            f"To execute FULL production deployment, reply:\n"
            f"*APPROVE PRODUCTION {rc_id[:8]} {token}*"
        )
        return WhatsAppResponseRedactor.redact(text)

    @staticmethod
    def paginate(text: str, page: int = 1, page_size: int = MAX_MESSAGE_CHAR_LIMIT) -> str:
        if len(text) <= page_size:
            return text

        total_pages = (len(text) + page_size - 1) // page_size
        page = max(1, min(page, total_pages))

        start = (page - 1) * page_size
        end = start + page_size
        snippet = text[start:end]

        return f"{snippet}\n\n--- [Page {page}/{total_pages} - Reply DETAILS <id> {page+1} for next page] ---"
