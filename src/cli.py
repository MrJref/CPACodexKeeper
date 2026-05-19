from .maintainer import CPACodexKeeper
from .settings import SettingsError, load_settings
from .webui import serve_webui


def build_arg_parser():
    import argparse

    parser = argparse.ArgumentParser(description="CPACodexKeeper")
    parser.add_argument("--dry-run", action="store_true", help="演练模式，不实际修改 / Dry run")
    parser.add_argument("--daemon", action="store_true", default=True, help="守护模式，默认开启 / Run forever")
    parser.add_argument("--once", dest="daemon", action="store_false", help="仅执行一轮后退出 / Run once")
    parser.add_argument("--web", dest="webui", action="store_true", default=None, help="启动 WebUI / Start WebUI")
    parser.add_argument("--no-web", dest="webui", action="store_false", help="关闭 WebUI / Disable WebUI")
    return parser


def main() -> int:
    parser = build_arg_parser()
    args = parser.parse_args()
    try:
        settings = load_settings()
    except SettingsError as exc:
        parser.exit(status=2, message=f"Configuration error: {exc}\n")

    webui_enabled = settings.webui_enabled if args.webui is None else args.webui
    if webui_enabled:
        serve_webui(settings=settings, dry_run=args.dry_run, start_scheduler=True)
        return 0

    maintainer = CPACodexKeeper(settings=settings, dry_run=args.dry_run)
    if args.daemon:
        maintainer.run_forever(cron_expression=settings.cron_expression)
        return 0
    maintainer.run()
    return 0
