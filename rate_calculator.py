import argparse
import json
import math
import os
import requests
import shutil

from datetime import datetime
from log import logger

TEST_FILE_NAME = "jellyfish-40-mbps-hd-h264.mkv"
TEST_FILE_TOTAL_FRAMES = 908  # hardcoded, thanks jellyfish buds <3


def get_conversion_rate(sample_path, profile_path, output_path):
    logger.debug("Copying {} to {}".format(TEST_FILE_NAME, profile_path))
    shutil.copy(sample_path, os.path.join(profile_path, TEST_FILE_NAME))
    file_size = -1
    output_file_path = os.path.join(output_path, TEST_FILE_NAME)
    logger.debug("Waiting for encoder to encode...")
    start_time = datetime.now()
    while True:
        if os.path.exists(output_file_path):
            if os.path.getsize(output_file_path) == file_size:
                break
            else:
                logger.info("Sample still copying...")
                file_size = os.path.getsize(output_file_path)

    if os.path.exists(os.path.join(profile_path, TEST_FILE_NAME)):
        os.remove(os.path.join(profile_path, TEST_FILE_NAME))
    duration = datetime.fromtimestamp(os.path.getmtime(output_file_path)) - start_time
    os.remove(output_file_path)  # Cleanup for next profile to process / when complete
    return math.floor(TEST_FILE_TOTAL_FRAMES / duration.total_seconds())


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("base_path", help="Paths-like object")
    parser.add_argument("--force_download", help="Force download/overwrite of sample file", action="store_true")
    parser.add_argument("--recalculate", help="Force recalculating of rates", action="store_true")
    args = parser.parse_args()

    if not (os.path.exists(args.base_path) and os.path.isdir(args.base_path)):
        raise FileNotFoundError("Base path [{}] does not exists/is not a directory, exiting.".format(args.base_path))

    test_file_path = os.path.join(args.base_path, TEST_FILE_NAME)
    encoder_rates = {}

    if not os.path.exists(os.path.join(args.base_path, "rates.json")) or args.recalculate:
        if not os.path.exists(test_file_path) or args.force_download:
            test_file_url = "http://jell.yfish.us/media/{}".format(TEST_FILE_NAME)
            request = requests.get(test_file_url, allow_redirects=True)
            with open(test_file_path, "wb") as test_file:
                test_file.write(request.content)

        encoders = os.path.join(args.base_path, "encoders")
        for encoder in os.scandir(encoders):
            logger.info("Calculating rates for {}".format(encoder.name))
            encoder_rates[encoder.name] = {}

            for profile in os.scandir(encoder.path):
                logger.info("Calculating rate for {}/{}".format(encoder.name, profile.name))
                if profile.name.lower() == "anime" or profile.name.lower() == "animation":
                    logger.warning("No test file for animation; assuming same encode rate as 'shows' rate")
                    encoder_rates[encoder.name][profile.name.lower()] = "FIXME"
                else:
                    encoder_rates[encoder.name][profile.name.lower()] = get_conversion_rate(
                        test_file_path, profile.path, os.path.join(args.base_path, "output")
                    )

            for profile in encoder_rates[encoder.name]:
                if encoder_rates[encoder.name][profile.lower()] == "FIXME":
                    encoder_rates[encoder.name][profile.lower()] = encoder_rates[encoder.name]["shows"]

        with open(os.path.join(args.base_path, "rates.json"), "w") as encoder_rates_file:
            json.dump(encoder_rates, encoder_rates_file, indent=4, sort_keys=True)

    else:
        print("rates.json exists, not recalculating.")
