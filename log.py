import logging.config
import os

logging.config.fileConfig(os.path.join(os.path.dirname(os.path.abspath(__file__)), "logging.conf"))
logger = logging.getLogger(__name__)
