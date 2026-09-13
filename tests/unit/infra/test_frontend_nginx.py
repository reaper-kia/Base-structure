from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize(
    "config_path",
    [
        PROJECT_ROOT / "frontend" / "nginx.conf",
        PROJECT_ROOT / "frontend" / "nginx.local.conf",
    ],
)
def test_proxy_uses_docker_dns_for_recreated_services(config_path: Path) -> None:
    config = config_path.read_text(encoding="utf-8")

    assert "resolver 127.0.0.11 valid=10s ipv6=off;" in config
    assert "set $app_upstream app:8000;" in config
    assert "set $stt_upstream stt_service:8200;" in config
    assert "proxy_pass http://$app_upstream;" in config
    assert "proxy_pass http://$stt_upstream;" in config
    assert "proxy_pass http://app:8000;" not in config
    assert "proxy_pass http://stt_service:8200/stt;" not in config
