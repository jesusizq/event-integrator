import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
import logging
from flask import current_app

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
BACKOFF_FACTOR = (
    0.3  # sleep for {backoff factor} * (2 ** ({number of total retries} - 1))
)


class ProviderClient:
    """
    A client for interacting with the provider API.
    """

    def __init__(self, base_url: str = None, timeout: int = None):
        """
        Initialize the provider client with optional base URL and timeout.
        """

        self.base_url = (
            base_url if base_url is not None else current_app.config["PROVIDER_API_URL"]
        )

        self.timeout = (
            timeout
            if timeout is not None
            else current_app.config["PROVIDER_API_TIMEOUT"]
        )

        self.session = self._create_session()

    def _create_session(self) -> requests.Session:
        """
        Creates a requests session with retry logic.
        """
        session = requests.Session()
        retry_strategy = Retry(
            total=MAX_RETRIES,
            backoff_factor=BACKOFF_FACTOR,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=[
                "HEAD",
                "GET",
                "OPTIONS",
            ],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session

    def get_events_xml(self) -> str | None:
        """
        Fetches events XML data from the provider API.

        Returns:
            str: The XML content as a string if successful, None otherwise.
        """
        try:
            response = self.session.get(self.base_url, timeout=self.timeout)
            response.raise_for_status()
            return response.text
        except requests.exceptions.HTTPError as http_err:
            status_code = getattr(http_err.response, "status_code", "N/A")
            response_text = getattr(http_err.response, "text", "N/A")
            logger.error(
                f"HTTP error occurred: {http_err} - Status: {status_code} - Response: {response_text}"
            )
        except requests.exceptions.ConnectionError as conn_err:
            logger.error(f"Connection error occurred: {conn_err}")
        except requests.exceptions.Timeout as timeout_err:
            logger.error(f"Timeout error occurred: {timeout_err}")
        except requests.exceptions.RequestException as req_err:
            logger.error(f"An unexpected error occurred during the request: {req_err}")
        return None
