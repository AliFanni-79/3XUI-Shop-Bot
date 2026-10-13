"""SpeedyBot production entrypoint.

SpeedyBot v4 is a single integrated application. The business core and the
Control Center live in the ``speedybot`` package; this file is the canonical
runtime entrypoint used by systemd, manual runs, installation and updates.

Architecture (Phase 2+):
  • Long polling thread  — Telegram bot (pyTelegramBotAPI)
  • Uvicorn thread       — FastAPI Mini App REST API on WEBAPP_PORT (default 8080)
"""
import os
import threading

from speedybot import core
import speedybot


def _start_api_server():
    """Start the FastAPI / Uvicorn server in a daemon thread."""
    try:
        import uvicorn
        from speedybot.api import app  # noqa: PLC0415

        port = int(os.getenv("WEBAPP_PORT", "8080"))
        host = os.getenv("WEBAPP_HOST", "0.0.0.0")

        print(f"🌐 Mini App API starting on http://{host}:{port}")
        uvicorn.run(
            app,
            host=host,
            port=port,
            log_level="warning",  # keep output clean alongside bot logs
            access_log=False,
        )
    except ImportError:
        print("⚠️  uvicorn / fastapi not installed — Mini App API disabled.")
        print("   Run: pip install -r requirements.txt")


def run():
    if not core.BOT_TOKEN or core.BOT_TOKEN == "DUMMY_TEST_TOKEN":
        print("\n" + "=" * 60)
        print("❌ خطا: فایل .env وجود ندارد یا مقدار BOT_TOKEN در آن تنظیم نشده است!")
        print("لطفاً یک کپی از فایل .env با نام .env بسازید:")
        print("   copy .env .env")
        print("سپس توکن ربات تلگرام خود را درون فایل .env قرار دهید:")
        print("   BOT_TOKEN='123456789:ABC...'")
        print("=" * 60 + "\n")
        return

    speedybot.install(core)
    print(f"SpeedyBot {speedybot.VERSION} is running...")
    core.bot.remove_webhook()
    core.recover_processing_transactions()
    core.reconcile_missing_referral_commissions()
    core.start_startup_panel_reconcile()
    core.start_service_monitor()
    speedybot.start_background()

    # Start FastAPI in a background thread (daemon=False keeps process alive)
    api_thread = threading.Thread(target=_start_api_server, name="uvicorn", daemon=True)
    api_thread.start()

    # Configure Telegram Chat Menu Button to open Mini App if WEBAPP_URL is set
    try:
        webapp_url = core.get_db_setting("webapp_url", "").strip() or os.getenv("WEBAPP_URL", "").strip()
        if webapp_url and hasattr(core.types, "MenuButtonWebApp"):
            core.bot.set_chat_menu_button(
                menu_button=core.types.MenuButtonWebApp(
                    type="web_app",
                    text="🚀 ورود به اپلیکیشن",
                    web_app=core.types.WebAppInfo(url=webapp_url)
                )
            )
            print(f"📱 Telegram Menu Button configured: {webapp_url}")
    except Exception as exc:
        print(f"ℹ️ Notice on setting menu button: {exc}")

    # Bot long-polling runs on the main thread
    core.bot.infinity_polling()


if __name__ == "__main__":
    run()
