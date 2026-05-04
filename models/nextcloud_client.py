"""Modern WebDAV client wrapper for Nextcloud.

Centralises authentication, retry, logging, and the few OCS endpoints
(public-link creation) that fall outside WebDAV. All other modules
(`kj_letters` etc.) should call this wrapper rather than `requests`
directly.

Per-company credentials are read from `res.company` so multi-company
deployments map naturally onto multiple NC servers/users.
"""
import io
import logging
import time
from typing import BinaryIO, Iterable, Optional
from urllib.parse import quote, urljoin

from odoo import _, api, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

try:
    import requests
    from webdav4.client import Client, ResourceAlreadyExists, ResourceNotFound
except ImportError:  # pragma: no cover - import guarded; surfaces in __manifest__
    Client = None  # type: ignore[assignment]
    requests = None  # type: ignore[assignment]
    ResourceAlreadyExists = ResourceNotFound = Exception  # type: ignore[assignment]


_RETRY_STATUSES = {500, 502, 503, 504}
_RETRY_BACKOFF = (0.5, 1.5, 4.0)


class NextcloudClient(models.AbstractModel):
    """Stateless service model — `env['nextcloud.client']`.

    Methods accept a `company` recordset to pick credentials. Default
    is `self.env.company`. Raises `UserError` with a translated message
    on misconfiguration; raises `webdav4` exceptions on transport errors
    so callers can decide retry policy themselves when needed.
    """

    _name = 'nextcloud.client'
    _description = 'Nextcloud WebDAV Client'

    # ----- helpers ----------------------------------------------------

    @api.model
    def _resolve_company(self, company=None):
        return company or self.env.company

    @api.model
    def _credentials(self, company=None):
        company = self._resolve_company(company).sudo()
        url = (company.nextcloud_url or '').rstrip('/')
        username = company.nextcloud_username or ''
        password = company.nextcloud_password or ''
        if not (url and username and password):
            raise UserError(_(
                "Nextcloud is not configured for company %s. "
                "Set the URL, username and app-password in Settings → "
                "Companies → Nextcloud.",
                company.display_name,
            ))
        return url, username, password

    @api.model
    def _dav_root(self, company=None):
        url, username, _pwd = self._credentials(company)
        return f"{url}/remote.php/dav/files/{username}"

    @api.model
    def _client(self, company=None):
        if Client is None:
            raise UserError(_(
                "The Python package `webdav4` is required by the Nextcloud "
                "module. Install it with `pip install webdav4`."
            ))
        url, username, password = self._credentials(company)
        return Client(
            base_url=f"{url}/remote.php/dav/files/{username}",
            auth=(username, password),
            timeout=30,
        )

    # ----- WebDAV verbs ----------------------------------------------

    @api.model
    def test_connection(self, company=None):
        """Return (ok: bool, message: str)."""
        try:
            client = self._client(company)
            client.ls("")  # PROPFIND on root
            return True, _("Connection Test Successful!")
        except Exception as exc:  # noqa: BLE001 — surface anything to UI
            _logger.warning("Nextcloud connection test failed: %s", exc)
            return False, _("Connection Test Unsuccessful: %s") % exc

    @api.model
    def exists(self, path, company=None):
        client = self._client(company)
        try:
            return client.exists(path)
        except ResourceNotFound:
            return False

    @api.model
    def mkdir(self, path, company=None, parents=True):
        """Create a directory at *path*. Idempotent: existing directory
        is treated as success.
        """
        client = self._client(company)
        path = self._normalize(path)
        if parents:
            parts = [p for p in path.split('/') if p]
            current = ''
            for part in parts:
                current = f"{current}/{part}" if current else part
                try:
                    client.mkdir(current)
                except ResourceAlreadyExists:
                    continue
        else:
            try:
                client.mkdir(path)
            except ResourceAlreadyExists:
                pass
        return path

    @api.model
    def upload(self, path, fileobj, company=None, overwrite=True):
        """Upload bytes / file-like object to *path*. Returns the path."""
        client = self._client(company)
        path = self._normalize(path)
        # Ensure parent dir exists.
        parent = '/'.join(path.split('/')[:-1])
        if parent:
            self.mkdir(parent, company=company)
        if isinstance(fileobj, (bytes, bytearray)):
            fileobj = io.BytesIO(fileobj)
        last_exc = None
        for attempt, backoff in enumerate((0,) + _RETRY_BACKOFF):
            if backoff:
                time.sleep(backoff)
            try:
                client.upload_fileobj(fileobj, path, overwrite=overwrite)
                return path
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                status = getattr(exc, 'status_code', None) or getattr(
                    getattr(exc, 'response', None), 'status_code', None
                )
                if status not in _RETRY_STATUSES:
                    raise
                _logger.info(
                    "Nextcloud upload retry %s/%s for %s (status=%s)",
                    attempt + 1, len(_RETRY_BACKOFF), path, status,
                )
                # Reset stream for retry.
                if hasattr(fileobj, 'seek'):
                    fileobj.seek(0)
        raise last_exc  # type: ignore[misc]

    @api.model
    def ls(self, path, company=None):
        return self._client(company).ls(self._normalize(path))

    @api.model
    def download(self, path, company=None) -> bytes:
        client = self._client(company)
        buf = io.BytesIO()
        client.download_fileobj(self._normalize(path), buf)
        return buf.getvalue()

    @api.model
    def delete(self, path, company=None):
        try:
            self._client(company).remove(self._normalize(path))
        except ResourceNotFound:
            return False
        return True

    # ----- OCS share API (not WebDAV) --------------------------------

    @api.model
    def create_public_share(self, path, company=None, label: Optional[str] = None,
                            permissions: int = 1):
        """POST to Nextcloud's OCS sharing API. Returns the public URL or False."""
        if requests is None:
            raise UserError(_("`requests` is required for share creation."))
        url, username, password = self._credentials(company)
        path = self._normalize(path)
        share_endpoint = f"{url}/ocs/v2.php/apps/files_sharing/api/v1/shares"
        data = {
            'path': '/' + path,
            'shareType': 3,  # public link
            'permissions': permissions,
        }
        if label:
            data['name'] = label
        headers = {
            'OCS-APIRequest': 'true',
            'Accept': 'application/json',
        }
        resp = requests.post(
            share_endpoint, headers=headers, data=data,
            auth=(username, password), timeout=30,
        )
        if resp.status_code != 200:
            _logger.error(
                "Nextcloud share creation failed for %s: %s %s",
                path, resp.status_code, resp.text[:200],
            )
            return False
        share_data = resp.json().get('ocs', {}).get('data', {}) or {}
        return share_data.get('url') or False

    # ----- utils ------------------------------------------------------

    @staticmethod
    def _normalize(path: str) -> str:
        """Strip leading/trailing slashes, collapse duplicates."""
        if not path:
            return ''
        parts = [p for p in path.split('/') if p]
        return '/'.join(parts)
