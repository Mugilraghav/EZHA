from __future__ import annotations

from urllib.parse import quote

import requests
from flask import current_app


class StorageConfigurationError(RuntimeError):
    pass


class StorageUploadError(RuntimeError):
    pass


class SupabaseStorage:
    def __init__(self):
        self.base_url = current_app.config.get("SUPABASE_URL", "").rstrip("/")
        self.bucket = current_app.config.get("SUPABASE_STORAGE_BUCKET", "")
        self.service_key = current_app.config.get("SUPABASE_SERVICE_ROLE_KEY", "")

    @property
    def configured(self) -> bool:
        return bool(self.base_url and self.bucket and self.service_key)

    @property
    def partially_configured(self) -> bool:
        return any((self.base_url, self.bucket, self.service_key)) and not self.configured

    def public_url(self, object_path: str) -> str:
        if not self.configured:
            raise StorageConfigurationError("Supabase Storage is not configured")
        bucket = quote(self.bucket, safe="")
        path = quote(object_path.lstrip("/"), safe="/")
        return f"{self.base_url}/storage/v1/object/public/{bucket}/{path}"

    def upload(self, file_stream, object_path: str, content_type: str) -> str:
        if not self.configured:
            raise StorageConfigurationError("Set SUPABASE_URL, SUPABASE_STORAGE_BUCKET, and SUPABASE_SERVICE_ROLE_KEY")
        bucket = quote(self.bucket, safe="")
        path = quote(object_path.lstrip("/"), safe="/")
        url = f"{self.base_url}/storage/v1/object/{bucket}/{path}"
        try:
            response = requests.post(
                url,
                headers={
                    "apikey": self.service_key,
                    "Authorization": f"Bearer {self.service_key}",
                    "Content-Type": content_type or "application/octet-stream",
                    "x-upsert": "false",
                },
                data=file_stream,
                timeout=30,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise StorageUploadError("Supabase Storage could not save this image") from exc
        return self.public_url(object_path)


def portfolio_image_url(filename: str, storage_provider: str = "local") -> str:
    if storage_provider == "supabase":
        return SupabaseStorage().public_url(filename)
    return f"/api/v1/artisan/portfolio/{quote(filename, safe='')}"