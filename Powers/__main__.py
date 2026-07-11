from platform import system

from Powers import LOGGER
from Powers.bot_class import Gojo

if __name__ == "__main__":

    if system() != "Windows":
        try:
            import uvloop
            uvloop.install()
            LOGGER.info("uvloop installed successfully")
        except Exception as e:
            LOGGER.warning(f"uvloop not installed: {e}")
    else:
        LOGGER.info("Windows detected, skipping uvloop")

    Gojo().run()
