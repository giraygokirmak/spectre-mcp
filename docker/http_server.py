# spectre-mcp — standalone HTTP entrypoint
# Stdio yerine streamable-http transport ile calistirir.
# HostOriginGuard kapatilir: LAN uzerinden (192.168.2.x) erisimde 421 vermesin diye.
import os

from spectre.server import mcp  # noqa: E402  (tool'lar import sirasinda register olur)


def main() -> None:
    host = os.environ.get("SPECTRE_HTTP_HOST", "0.0.0.0")
    port = int(os.environ.get("SPECTRE_HTTP_PORT", "7001"))
    try:
        mcp.settings.host = host
        mcp.settings.port = port
        mcp.settings.http_path = "/mcp"
    except Exception:
        pass
    mcp.run(
        transport="streamable-http",
        host=host,
        port=port,
        path="/mcp",
        host_origin_protection=False,
    )


if __name__ == "__main__":
    main()
