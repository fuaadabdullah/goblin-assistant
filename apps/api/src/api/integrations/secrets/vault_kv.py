from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from .base import SecretMetadata


def parse_vault_time(time_str: Optional[str]) -> Optional[datetime]:
    if not time_str:
        return None
    try:
        return datetime.fromisoformat(time_str.replace("Z", "+00:00"))
    except Exception:
        return None


def build_kv2_metadata(mount_point: str, metadata: Dict[str, Any]) -> SecretMetadata:
    return SecretMetadata(
        created_at=parse_vault_time(metadata.get("created_time")),
        updated_at=parse_vault_time(metadata.get("updated_time")),
        version=metadata.get("version"),
        custom_metadata=metadata.get("custom_metadata", {}),
        backend_specific={
            "vault_kv_version": 2,
            "mount_point": mount_point,
            "cas_version": metadata.get("cas_version"),
        },
    )


def build_kv1_metadata(mount_point: str) -> SecretMetadata:
    return SecretMetadata(
        created_at=None,
        updated_at=None,
        version=None,
        custom_metadata={},
        backend_specific={
            "vault_kv_version": 1,
            "mount_point": mount_point,
        },
    )


def detect_kv_version(client: Any, mount_point: str) -> int:
    mounts = client.sys.list_mounted_secrets_engines()
    if mount_point in mounts:
        mount_config = mounts[mount_point]
        options = mount_config.get("options", {})
        version = options.get("version")
        if version in ["1", "2"]:
            return int(version)
    return 1


def read_secret_payload(
    client: Any,
    mount_point: str,
    path: str,
    version: Optional[int],
    kv_version: int,
) -> tuple[Dict[str, str], SecretMetadata]:
    if kv_version == 2:
        if version is not None:
            response = client.secrets.kv.v2.read_secret_version(
                path=path,
                version=version,
                mount_point=mount_point,
            )
        else:
            response = client.secrets.kv.v2.read_secret_version(
                path=path,
                mount_point=mount_point,
            )
        return response["data"]["data"], build_kv2_metadata(
            mount_point, response["data"]["metadata"]
        )

    response = client.secrets.kv.v1.read_secret(
        path=path,
        mount_point=mount_point,
    )
    return response["data"], build_kv1_metadata(mount_point)


def write_secret_payload(
    client: Any,
    mount_point: str,
    path: str,
    data: Dict[str, str],
    metadata: Optional[Dict[str, Any]],
    version: Optional[int],
    kv_version: int,
) -> SecretMetadata:
    if kv_version == 2:
        write_params: Dict[str, Any] = {"data": data}
        if metadata:
            write_params["options"] = {"cas": version} if version is not None else {}
            write_params["metadata"] = metadata
        elif version is not None:
            write_params["options"] = {"cas": version}

        response = client.secrets.kv.v2.create_or_update_secret(
            path=path,
            secret=write_params,
            mount_point=mount_point,
        )
        return build_kv2_metadata(mount_point, response["data"]["metadata"])

    client.secrets.kv.v1.create_or_update_secret(
        path=path,
        secret=data,
        mount_point=mount_point,
    )
    return build_kv1_metadata(mount_point)


def list_secret_paths(
    client: Any, mount_point: str, prefix: str, limit: int, kv_version: int
) -> list[str]:
    if kv_version == 2:
        response = client.secrets.kv.v2.list_secrets(
            path=prefix,
            mount_point=mount_point,
        )
    else:
        response = client.secrets.kv.v1.list_secrets(
            path=prefix,
            mount_point=mount_point,
        )

    if response and "data" in response and "keys" in response["data"]:
        return [path for path in response["data"]["keys"] if not path.endswith("/")][:limit]
    return []


def delete_secret_path(
    client: Any,
    mount_point: str,
    path: str,
    version: Optional[int],
    kv_version: int,
) -> None:
    if kv_version == 2:
        if version is not None:
            client.secrets.kv.v2.delete_secret_versions(
                path=path,
                versions=[version],
                mount_point=mount_point,
            )
        else:
            client.secrets.kv.v2.delete_latest_version_of_secret(
                path=path,
                mount_point=mount_point,
            )
        return

    client.secrets.kv.v1.delete_secret(
        path=path,
        mount_point=mount_point,
    )
