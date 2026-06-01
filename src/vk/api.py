import requests

from src.vk.models.group import VKGroupInfoDTO
from src.vk.models.group_wall import VKWallResponseDTO
from src.vk.models.group import VKGroupOnlineStatusDTO


class VKAPIClient:
    def __init__(
        self,
        user_id: int,
        token: str,
        api_version: float,
    ) -> None:
        self._user_id = user_id
        self._token = token
        self._api_version = api_version
        self._client = requests.Session()

    def _request(
        self,
        method: str,
        extra_params: dict,
    ) -> requests.Response:
        params = {
            "access_token": self._token,
            "v": self._api_version,
            **extra_params,
        }
        return self._client.get(
            f"https://api.vk.com/method/{method}",
            params=params,
        )

    def resolve_group_id(self, screen_name: str) -> int | None:
        """screen_name → group_id, или None если это не группа."""
        resp = self._request(
            "utils.resolveScreenName",
            {"screen_name": screen_name},
        )
        if not resp.json()["response"]:
            return None
        if resp.json()["response"].get("type") != "group":
            return None
        return resp.json()["response"]["object_id"]

    def get_group_wall(
        self,
        group_id: int,
        count: int = 100,
        offset: int = 0,
    ) -> VKWallResponseDTO:
        response = self._request(
            "wall.get",
            {
                "owner_id": group_id,
                "filter": "owner",
                "count": count,
                "offset": offset,
            },
        )
        return VKWallResponseDTO.model_validate(
            response.json()["response"],
        )

    def get_online_status(
        self,
        group_id: int,
        can_message: bool = True,
    ) -> VKGroupOnlineStatusDTO:
        if not can_message:
            return VKGroupOnlineStatusDTO(
                status=None,
                minutes=None,
            )
        response = self._request(
            "groups.getOnlineStatus",
            {"group_id": group_id},
        )
        return VKGroupOnlineStatusDTO.model_validate(
            response.json()["response"],
        )

    def get_group_info(self, group_id: int | str) -> VKGroupInfoDTO:
        fields = [
            # A–K
            "activity",
            "addresses",
            "age_limits",
            "ban_info",
            "can_create_topic",
            "can_message",
            "can_post",
            "can_see_all_posts",
            "can_upload_doc",
            "can_upload_story",
            "can_upload_video",
            "city",
            "contacts",
            "counters",
            "country",
            "cover",
            "crop_photo",
            "description",
            "fixed_post",
            "has_photo",
            "is_favorite",
            "is_hidden_from_feed",
            "is_messages_blocked",
            # L–W
            "links",
            "main_album_id",
            "main_section",
            "market",
            "member_status",
            "members_count",
            "place",
            "public_date_label",
            "site",
            "start_date",
            "finish_date",
            "status",
            "trending",
            "verified",
            "vk_ticket",
            "wall",
            "wiki_page",
        ]
        fields_str = ",".join(fields)
        response = self._request(
            "groups.getById",
            {
                "group_id": group_id,
                "fields": fields_str,
                "extended": 1,
            },
        )
        return VKGroupInfoDTO.model_validate(
            response.json()["response"]["groups"][0],
        )
