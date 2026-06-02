import json
import re
import secrets
import string
import time
from datetime import datetime
from typing import Any, Optional
from urllib.parse import quote, unquote

import requests
from requests.exceptions import ConnectionError as RequestsConnectionError
from requests.exceptions import RequestException

import config

PANEL_RETRIES = 3
PANEL_RETRY_DELAY = 2


class PanelError(Exception):
    pass


class PanelClient:
    def __init__(self):
        self.session = requests.Session()
        self.session.verify = True
        self.session.trust_env = False
        self.session.proxies = {"http": None, "https": None}
        self._csrf: Optional[str] = None

    def _fetch_csrf(self):
        r = self.session.get(f"{config.PANEL_URL}/", timeout=30)
        r.raise_for_status()
        m = re.search(r'csrf-token" content="([^"]+)"', r.text)
        if not m:
            raise PanelError("CSRF token not found")
        self._csrf = m.group(1)

    def login(self):
        self._fetch_csrf()
        r = self.session.post(
            f"{config.PANEL_URL}/login",
            headers={"X-CSRF-Token": self._csrf},
            data={"username": config.PANEL_USER, "password": config.PANEL_PASS},
            timeout=30,
        )
        data = r.json()
        if not data.get("success"):
            raise PanelError(data.get("msg", "Login failed"))

    def _ensure_auth(self):
        try:
            r = self.session.get(
                f"{config.PANEL_URL}/panel/api/inbounds/list", timeout=30
            )
            if r.status_code == 404 or not r.text.strip():
                self.login()
        except RequestException:
            self.login()

    def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: Any = None,
        data: Any = None,
        retry_auth: bool = True,
    ) -> dict:
        last_err: Optional[Exception] = None

        for attempt in range(PANEL_RETRIES):
            try:
                self._ensure_auth()
                url = f"{config.PANEL_URL}{path}"
                headers = {}
                if self._csrf and method.upper() != "GET":
                    headers["X-CSRF-Token"] = self._csrf

                r = self.session.request(
                    method,
                    url,
                    json=json_body,
                    data=data,
                    headers=headers,
                    timeout=60,
                )
                if r.status_code == 404 and retry_auth:
                    self.login()
                    return self._request(
                        method, path, json_body=json_body, data=data, retry_auth=False
                    )

                if not r.text.strip():
                    raise PanelError(f"Empty response from {path}")

                if "text/html" in (r.headers.get("content-type") or "").lower() or r.text.lstrip().startswith("<"):
                    raise PanelError(
                        "پنل HTML برگرداند (احتمالاً درخواست از مسیر پروکسی رفته). "
                        "پروکسی فقط باید برای تلگرام باشد — ربات را ری‌استارت کنید."
                    )

                try:
                    payload = r.json()
                except json.JSONDecodeError as e:
                    raise PanelError(f"Invalid JSON from {path}: {r.text[:200]}") from e

                if not payload.get("success"):
                    raise PanelError(payload.get("msg", "Request failed"))
                return payload

            except PanelError:
                raise
            except (RequestsConnectionError, RequestException) as e:
                last_err = e
                if attempt < PANEL_RETRIES - 1:
                    time.sleep(PANEL_RETRY_DELAY * (attempt + 1))
                    try:
                        self.login()
                    except Exception:
                        pass
                    continue
                raise PanelError(
                    "اتصال به پنل برقرار نشد. چند ثانیه بعد دوباره امتحان کنید."
                ) from e

        raise PanelError("اتصال به پنل برقرار نشد.") from last_err

    def list_inbounds(self) -> list[dict]:
        return self._request("GET", "/panel/api/inbounds/list").get("obj") or []

    def get_inbound(self, inbound_id: int) -> dict:
        return self._request("GET", f"/panel/api/inbounds/get/{inbound_id}").get("obj")

    def new_uuid(self) -> str:
        obj = self._request("GET", "/panel/api/server/getNewUUID").get("obj")
        if isinstance(obj, dict):
            return obj["uuid"]
        return str(obj)

    def get_client_traffic(self, email: str) -> dict:
        return self._request(
            "GET", f"/panel/api/inbounds/getClientTraffics/{email}"
        ).get("obj")

    def get_client_links(self, inbound_id: int, email: str) -> list[str]:
        return (
            self._request(
                "GET", f"/panel/api/inbounds/getClientLinks/{inbound_id}/{email}"
            ).get("obj")
            or []
        )

    def get_sub_links(self, sub_id: str) -> list[str]:
        return (
            self._request("GET", f"/panel/api/inbounds/getSubLinks/{sub_id}").get("obj")
            or []
        )

    def get_last_online(self):
        """Returns dict {email: timestamp_ms} or list of {email, lastOnline}."""
        return self._request("POST", "/panel/api/inbounds/lastOnline").get("obj") or {}

    def client_email_exists(self, email: str, inbound_id: Optional[int] = None) -> bool:
        inbounds = [self.get_inbound(inbound_id)] if inbound_id else self.list_inbounds()
        for inbound in inbounds:
            settings = json.loads(inbound.get("settings") or "{}")
            for c in settings.get("clients", []):
                if c.get("email") == email:
                    return True
        return False

    def find_client_by_uuid(self, uuid: str, inbound_ids: Optional[list[int]] = None) -> Optional[dict]:
        inbounds = self.list_inbounds()
        for inbound in inbounds:
            if inbound_ids and inbound["id"] not in inbound_ids:
                continue
            settings = json.loads(inbound.get("settings") or "{}")
            for c in settings.get("clients", []):
                if c.get("id") == uuid:
                    return {
                        "inbound_id": inbound["id"],
                        "inbound_remark": inbound.get("remark", ""),
                        "client": c,
                    }
        return None

    def get_inbound_remark(self, inbound_id: int) -> str:
        return self.get_inbound(inbound_id).get("remark", "")

    def add_client(
        self,
        inbound_id: int,
        email: str,
        uuid: str,
        sub_id: str,
        total_bytes: int,
        expiry_time_ms: int = 0,
    ):
        inbound = self.get_inbound(inbound_id)
        settings = json.loads(inbound["settings"])
        sample = settings.get("clients", [{}])[0] if settings.get("clients") else {}
        flow = sample.get("flow", "")

        client = {
            "comment": "",
            "email": email,
            "enable": True,
            "expiryTime": expiry_time_ms,
            "flow": flow,
            "id": uuid,
            "limitIp": 0,
            "reset": 0,
            "subId": sub_id,
            "tgId": "",
            "totalGB": total_bytes,
        }
        body = {
            "id": inbound_id,
            "settings": json.dumps({"clients": [client]}),
        }
        return self._request("POST", "/panel/api/inbounds/addClient", json_body=body)

    def _find_client_in_inbound(self, inbound_id: int, client_uuid: str) -> Optional[dict]:
        inbound = self.get_inbound(inbound_id)
        settings = json.loads(inbound["settings"])
        for c in settings.get("clients", []):
            if c.get("id") == client_uuid:
                return c
        return None

    def update_client_total(
        self, inbound_id: int, client_uuid: str, new_total_bytes: int, enable: Optional[bool] = None
    ):
        client = self._find_client_in_inbound(inbound_id, client_uuid)
        if not client:
            raise PanelError("Client not found in inbound")
        client["totalGB"] = new_total_bytes
        if enable is not None:
            client["enable"] = enable
        body = {
            "id": inbound_id,
            "settings": json.dumps({"clients": [client]}),
        }
        return self._request(
            "POST", f"/panel/api/inbounds/updateClient/{client_uuid}", json_body=body
        )

    def set_client_enabled(self, inbound_id: int, client_uuid: str, enabled: bool):
        client = self._find_client_in_inbound(inbound_id, client_uuid)
        if not client:
            raise PanelError("Client not found in inbound")
        client["enable"] = enabled
        body = {
            "id": inbound_id,
            "settings": json.dumps({"clients": [client]}),
        }
        return self._request(
            "POST", f"/panel/api/inbounds/updateClient/{client_uuid}", json_body=body
        )

    def delete_client(self, inbound_id: int, client_uuid: str):
        return self._request(
            "POST", f"/panel/api/inbounds/{inbound_id}/delClient/{client_uuid}"
        )


panel = PanelClient()


def days_to_expiry_ms(days: int) -> int:
    """
    مقدار expiryTime برای پنل 3X-UI:
    - 0 = نامحدود
    - منفی = Start After First Use (|value| = مدت به ms، از اولین اتصال)
    - مثبت = تاریخ انقضای مطلق (ms) — استفاده نمی‌شود
    """
    if days <= 0:
        return 0
    return -(days * 86400 * 1000)


def format_expiry_ms(expiry_ms: int) -> str:
    if not expiry_ms:
        return "نامحدود"
    if expiry_ms < 0:
        duration_days = abs(expiry_ms) // (86400 * 1000)
        if duration_days > 0:
            return f"پس از اولین اتصال ({duration_days} روز)"
        hours = abs(expiry_ms) // (3600 * 1000)
        return f"پس از اولین اتصال ({hours} ساعت)" if hours else "پس از اولین اتصال"
    try:
        return datetime.fromtimestamp(expiry_ms / 1000).strftime("%Y-%m-%d %H:%M")
    except (OSError, ValueError, OverflowError):
        return "نامشخص"


def random_sub_id(length: int = 16) -> str:
    alphabet = string.ascii_lowercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def random_client_name() -> str:
    return f"user-{random_sub_id(6)}"


def normalize_client_name(name: str) -> str:
    name = name.strip().lstrip("-")
    name = re.sub(r"\s+", "-", name)
    name = re.sub(r"[^a-zA-Z0-9._-]", "", name)
    return name[:63]


def to_panel_email(display_name: str) -> str:
    """Panel client email: hyphen prefix avoids clash with existing panel names."""
    name = display_name.lstrip("-")
    if not name:
        return ""
    return f"-{name}"[:64]


def is_duplicate_error(msg: str) -> bool:
    m = (msg or "").lower()
    return any(k in m for k in ("duplicate", "exist", "already", "تکراری", "موجود"))


def fix_link_fragment(link: str, inbound_remark: str, client_name: str) -> str:
    if not link or link == "—":
        return link
    expected = f"{inbound_remark}-{client_name}"
    if "#" not in link:
        return f"{link}#{quote(expected, safe='')}"

    base, frag = link.rsplit("#", 1)
    frag = unquote(frag)
    if frag.startswith(expected):
        return link

    traffic = ""
    m = re.search(r"(-[0-9.]+\s*(?:MB|GB|TB)[^\s]*)", frag, re.I)
    if m:
        traffic = m.group(1)

    if frag == inbound_remark or not frag.startswith(f"{inbound_remark}-"):
        return f"{base}#{quote(expected + traffic, safe='')}"
    return link


def parse_client_name_from_link(link: str, inbound_remark: str = "") -> Optional[str]:
    if "#" not in link:
        return None
    frag = unquote(link.rsplit("#", 1)[1])
    frag = re.sub(r"-[0-9.]+\s*(MB|GB|TB).*$", "", frag, flags=re.I).strip()
    if inbound_remark and frag.startswith(inbound_remark + "-"):
        return frag[len(inbound_remark) + 1 :]
    if "-" in frag:
        return frag.split("-", 1)[1]
    return frag or None


def sub_url(sub_id: str) -> str:
    return f"{config.SUB_BASE_URL}{sub_id}"


def parse_config_link(link: str) -> Optional[str]:
    link = link.strip()
    if link.startswith("vless://"):
        part = link[len("vless://") :].split("@")[0]
        return unquote(part)
    if link.startswith("trojan://"):
        part = link[len("trojan://") :].split("@")[0]
        return unquote(part)
    if link.startswith("vmess://"):
        import base64

        try:
            data = json.loads(base64.b64decode(link[8:] + "==").decode())
            return data.get("id")
        except Exception:
            return None
    return None


def format_bytes(n: int) -> str:
    if n <= 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB"]
    v = float(n)
    for u in units:
        if v < 1024 or u == units[-1]:
            return f"{v:.2f} {u}"
        v /= 1024
    return f"{n} B"


def gb_to_bytes(gb: float) -> int:
    return int(gb * config.GB)
