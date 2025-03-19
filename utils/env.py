import os
import logging
import streamlit as st
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("load_secrets")

KEYS = ["GEMINI_API_KEY", "MONGODB_URI", "APP_PASSWORD"]
load_dotenv()


def report_results(secrets):
    missing_secrets = [key for key, value in secrets.items() if value is None]
    if missing_secrets:
        logger.error(f"Secret(s) missing from environment: {', '.join(missing_secrets)}")
    else:
        logger.info("All secrets loaded successfully from environment.")


def load_from_toml_file():
    try:
        logger.info("Trying to load secrets from toml file...")
        success = st.secrets.load_if_toml_exists()
        if success:
            logger.info("All secrets loaded successfully from toml file.")
        else:
            logger.info("Could not find toml file. Trying to load from environment...")
        return success
    except AttributeError:
        return False


def load_secrets():
    # First, we'll try to load the secrets from toml file   - Locally
    loaded_from_toml = load_from_toml_file()

    # If successful, we're done
    if loaded_from_toml:
        return

    # Else, we'll try to load them from environment         - AWS
    secrets = {key: os.environ.get(key) for key in KEYS}
    report_results(secrets)
    st.secrets = secrets
