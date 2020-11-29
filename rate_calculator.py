import argparse
import json
import math
import pathlib
import requests
import shutil

from datetime import datetime
from log import logger

SAMPLE_FILE_NAME = "jellyfish-40-mbps-hd-h264.mkv"
SAMPLE_FILE_TOTAL_FRAMES = 908  # hardcoded, thanks jellyfish buds <3


def download_sample_file(local_sample_file_path, debug=False):
    sample_file_url = "http://jell.yfish.us/media/{}".format(SAMPLE_FILE_NAME)
    logger.debug("Downloading [{}] to [{}]".format(sample_file_url, local_sample_file_path))
    if not debug:
        request = requests.get(sample_file_url, allow_redirects=True)
        local_sample_file_path.write_bytes(request.content)


def get_conversion_rate(sample_path, profile_path, output_path, debug=False):
    profile_test_file_path = pathlib.Path(profile_path, SAMPLE_FILE_NAME)
    output_file_path = pathlib.Path(output_path, SAMPLE_FILE_NAME)

    logger.debug("Copying [{}] -> [{}]".format(sample_path, profile_test_file_path))
    if not debug:
        shutil.copy(sample_path, profile_test_file_path)

    file_size = -1
    logger.debug("Waiting for sample job to complete")
    start_time = datetime.now()

    if not debug:
        while True:
            if output_file_path.exists():
                if output_file_path.stat().st_size == file_size:
                    break
                else:
                    file_size = output_file_path.stat().st_size

    if debug:
        conversion_fps = 0
        logger.debug("Debug encode complete; conversion FPS = [{}]".format(conversion_fps))
    else:
        duration = datetime.fromtimestamp(output_file_path.stat().st_mtime) - start_time
        conversion_fps = math.floor(SAMPLE_FILE_TOTAL_FRAMES / duration.total_seconds())
        logger.debug("Encode complete; conversion FPS = [{}]".format(conversion_fps))

    profile_test_file_path.unlink(missing_ok=True)
    output_file_path.unlink(missing_ok=True)

    return conversion_fps


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("base_path", help="Paths-like object")
    parser.add_argument("--force_download", help="Force download/overwrite of sample file", action="store_true")
    parser.add_argument("--recalculate", help="Force recalculating of rates", action="store_true")
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    base_path = pathlib.Path(args.base_path)

    if not (base_path.exists() and base_path.is_dir()):
        raise FileNotFoundError("Base path [{}] does not exists/is not a directory, exiting.".format(base_path))

    rates_file = base_path.joinpath("rates.json")
    sample_file_path = base_path.joinpath(SAMPLE_FILE_NAME)
    
    encoders_path = base_path.joinpath("encoders")
    encoder_rates = {}

    if not rates_file.exists() or args.recalculate:
        if not sample_file_path.exists() or args.force_download:
            download_sample_file(sample_file_path, args.debug)

        for encoder in encoders_path.iterdir():
            logger.info("Calculating rates for [{}]".format(encoder.name))
            encoder_rates[encoder.name] = {}

            for profile in encoder.iterdir():
                logger.info("Calculating rate for [{}]/[{}]".format(encoder.name, profile.name))
                lower_profile = profile.name.lower()
                if lower_profile == "anime" or lower_profile == "animation":
                    logger.warning("No test file for animation; assuming same encode rate as 'shows' rate")
                    encoder_rates[encoder.name][lower_profile] = "TV_FPS"
                else:
                    encoder_rates[encoder.name][lower_profile] = get_conversion_rate(
                        sample_file_path, profile, base_path.joinpath("output"), args.debug
                    )

            for profile in encoder_rates[encoder.name]:
                if encoder_rates[encoder.name][profile.lower()] == "TV_FPS":
                    encoder_rates[encoder.name][profile.lower()] = encoder_rates[encoder.name]["shows"]

        if not args.debug:
            rates_file.write_text(json.dumps(encoder_rates, indent=4, sort_keys=True))

    else:
        logger.warning("[rates.json] exists, not recalculating.")
