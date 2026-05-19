import logging
from typing import Any

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)


class YouTubeClient:
    def __init__(self, credentials: Credentials) -> None:
        # We MUST type this as `Any`. `googleapiclient` creates methods like
        # `liveBroadcasts()` dynamically at runtime based on Google's JSON discovery docs.
        # The base `Resource` class does NOT actually contain these methods, so 
        # statically typing it as `Resource` guarantees a type-checker error.
        self._service: Any = build("youtube", "v3", credentials=credentials)

    def find_broadcast(
        self, scheduled_start_iso: str, broadcastStatus: str = "all"
    ) -> dict[str, Any] | None:
        """
        Find broadcast by scheduled start time.

        Args:
            scheduled_start_iso: Scheduled start time in ISO 8601 format.
            broadcastStatus: Status of the broadcast. Can be 'all', 'active', 'upcoming', 
                'live', 'completed', 'none'. Defaults to 'all'.

        Returns:
            dict[str, Any] | None: Dictionary containing broadcast information if found, 
                None otherwise.
        """
        response = (
            self._service.liveBroadcasts()
            .list(
                part="id,snippet,status",
                broadcastType="all",
                mine=True,
                maxResults=50,
            )
            .execute()
        )
        for item in response.get("items", []):
            if item["snippet"].get("scheduledStartTime") == scheduled_start_iso:
                return item
        return None

    def create_broadcast(
        self, title: str, scheduled_start_iso: str, description: str = ""
    ) -> dict[str, Any]:
        return (
            self._service.liveBroadcasts()
            .insert(
                part="snippet,status",
                body={
                    "snippet": {
                        "title": title,
                        "scheduledStartTime": scheduled_start_iso,
                        "description": description,
                    },
                    "status": {"privacyStatus": "public"},
                },
            )
            .execute()
        )

    def create_stream(self, title: str) -> dict[str, Any]:
        return (
            self._service.liveStreams()
            .insert(
                part="snippet,cdn",
                body={
                    "snippet": {"title": title},
                    "cdn": {
                        "frameRate": "variable",
                        "ingestionType": "rtmp",
                        "resolution": "variable",
                    },
                },
            )
            .execute()
        )

    def bind_broadcast(self, broadcast_id: str, stream_id: str) -> dict[str, Any]:
        return (
            self._service.liveBroadcasts()
            .bind(part="id,contentDetails", id=broadcast_id, streamId=stream_id)
            .execute()
        )

    def get_broadcast_status(self, broadcast_id: str) -> str | None:
        response = (
            self._service.liveBroadcasts()
            .list(part="status", id=broadcast_id)
            .execute()
        )
        items = response.get("items", [])
        return items[0]["status"]["lifeCycleStatus"] if items else None
