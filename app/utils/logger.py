import logging
import sys


def setup_logging():
    app_logger = logging.getLogger("app")
    app_logger.setLevel(logging.INFO)
    app_logger.propagate = False

    if not any(getattr(handler, "_weather_handler", False) for handler in app_logger.handlers):
        handler = logging.StreamHandler(sys.stdout)
        handler._weather_handler = True
        handler.setFormatter(logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        ))
        app_logger.addHandler(handler)

    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
    logging.getLogger("httpx").setLevel(logging.WARNING)

    logger = logging.getLogger("app.utils.logger")
    logger.info("Logging configured successfully.")
    return app_logger
