from abc import ABC, abstractmethod
from typing import List, Optional
from app.services.browser.models import BrowserScenario, BrowserRunResult

class BaseBrowserProvider(ABC):
    """
    Abstract Base Class for Browser Verification Providers.
    Encapsulates browser automation logic (Mock or Playwright).
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Returns MOCK_BROWSER or PLAYWRIGHT_BROWSER"""
        pass

    @abstractmethod
    async def run_scenario(
        self,
        scenario: BrowserScenario,
        project_id: str,
        workspace_id: str,
        agent_run_id: Optional[str] = None,
        allowed_base_urls: Optional[List[str]] = None
    ) -> BrowserRunResult:
        """Executes a BrowserScenario and returns a structured BrowserRunResult."""
        pass
