import argparse
import cv2
import json
import pathlib

from log import logger


class VideoJSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Video):
            return o.as_dict()
        return json.JSONEncoder.default(self, o)


class Video:
    def __init__(self, filename, path, frames, frame_rate, profile):
        self.filename = filename
        self.path = path
        self.frames = frames
        self.frame_rate = frame_rate
        self.duration = frames/frame_rate
        self.profile = profile

    def get_time_to_render(self, encoder_fps):
        return self.frames/encoder_fps

    def as_dict(self):
        return {
            "filename": self.filename,
            "profile": self.profile,
            "frames": self.frames,
            "frame_rate": self.frame_rate,
            "duration": self.duration,
            "path": str(self.path)
        }

    def __str__(self):
        return "Video(filename={},path={},frames={},frame_rate={},duration={})".format(
            self.filename, self.path, self.frames, self.frame_rate, self.duration
        )

    def __repr__(self):
        return self.__str__()


class Queue:
    def __init__(self, queue_base_path):
        self.jobs_in_queue = False
        self.encoder_conversion_rates = json.loads(pathlib.Path(queue_base_path, "rates.json").read_text())
        self.queue_info = dict.fromkeys(self.encoder_conversion_rates.keys())
        for encoder in self.queue_info:
            self.queue_info[encoder] = {"load": 0, "jobs": []}

    def add_videos_to_queue(self, jobs: [Video]):
        logger.info("Adding files to queue")
        for job in jobs:
            temp_loads = dict.fromkeys(self.queue_info.keys(), 0)
            job_loads = dict.fromkeys(self.queue_info.keys(), 0)
            for encoder in self.queue_info:
                temp_loads[encoder] = self.queue_info[encoder]["load"]
                encoder_rate = self.encoder_conversion_rates[encoder][job.profile]
                temp_loads[encoder] += job.frames / encoder_rate
                job_loads[encoder] = job.frames / encoder_rate

            shortest_queue_machine = min(temp_loads, key=temp_loads.get)
            logger.debug("Adding {} to {}".format(job.filename, shortest_queue_machine))
            self.queue_info[shortest_queue_machine]["jobs"].append(job)

            # Alternative way of doing the above, but adds a "load" key to each job in the job list,
            # just the raw time the job takes to complete.  Can be computed by hand.
            # self.queue_info[shortest_queue_machine]["jobs"].append(job.as_dict())
            # self.queue_info[shortest_queue_machine]["jobs"][-1]["load"] = job_loads[shortest_queue_machine]

            self.queue_info[shortest_queue_machine]["load"] += job_loads[shortest_queue_machine]
            self.jobs_in_queue = True

    def distribute_jobs(self, encoders_path, debug=False):
        if not self.jobs_in_queue:
            logger.error("No jobs in queue, cannot distribute nothing!")
            return

        logger.info("Distributing files to calculated encoders")
        for encoder in self.queue_info:
            for job in self.queue_info[encoder]["jobs"]:
                logger.debug("Encoder [{}]-[{}]: Appending: {}".format(encoder, job.profile, job.filename))
                if not debug:
                    pathlib.Path(job.path).rename(pathlib.Path(encoders_path, encoder, job.profile, job.filename))
                    # os.rename(job.path, os.path.join(encoders_path, encoder, job.profile, job.filename))

        for encoder in self.queue_info:
            logger.info("Encoder [{}] queue: {}".format(encoder, self.queue_info[encoder]["load"]))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("base_path", help="Paths-like object")
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    base_path = pathlib.Path(args.base_path)
    rates_file = base_path.joinpath("rates.json")

    if not (base_path.exists() and base_path.is_dir()):
        raise FileNotFoundError("Base path [{}] does not exists/is not a directory, exiting.".format(base_path))
    if not rates_file.exists():
        raise FileNotFoundError("[rates.json] has not been calculated, please run rate_calculator.py")

    encoder_path = base_path.joinpath("encoders")
    input_path = base_path.joinpath("inputs")
    output_path = base_path.joinpath("output")

    pending_jobs = []

    logger.info("Scanning for files to enqueue")
    for input_profile in input_path.iterdir():
        logger.debug("Scanning profile [{}]".format(input_profile.name))
        for file in input_profile.iterdir():
            logger.debug("Scanning file [{}]".format(file.name))
            capture = cv2.VideoCapture(str(file))
            frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = capture.get(cv2.CAP_PROP_FPS)
            pending_jobs.append(Video(file.name, file, frame_count, fps, input_profile.name.lower()))
            capture.release()

    pending_jobs_sorted = sorted(pending_jobs, key=lambda x: x.frames, reverse=True)

    queue = Queue(base_path)
    queue.add_videos_to_queue(pending_jobs_sorted)
    if not args.debug:
        base_path.joinpath("queue.json").write_text(json.dumps(queue.queue_info, indent=4, cls=VideoJSONEncoder))
    queue.distribute_jobs(encoder_path, debug=args.debug)
