# Handbrake Balancer

Created to complement https://github.com/jlesage/docker-handbrake (specifcally, https://github.com/jlesage/docker-handbrake/issues/125)

## Requirements/Assumptions:

### Directory Structure:

```
path/to/base/directory/
  encoders/
    encoder-1/
      watch-profile-1/
      watch-profile-2/
      ...
    encoder-2/
      watch-profile-1/
      watch-profile-2/
      ...
    ...
  inputs/
    watch-profile-1/
    watch-profile-2/
    ...
  output/
    [all encoded files]
```

You must have the same directories in `inputs/` directory as you do your `encoder/*` directories.

The encoders can be named however you please (I used `hostname-#` while testing), but the scripts are hardcoded to assume `encoders/`, `inputs`, and `output` all exists at this directory.

### Software

* Python 3.8.2 was used, I imagine this will work with any Python 3 but I can't guarantee nor recommend Python 2.  C'mon y'all, it's dead, let it be dead.
* Libraries to install:
  * `opencv-python` / `cv2` - used to calculate the number of frames and frame rate of input files, not required if you're only calculating the FPS of your encoders
  * `requests` - used to download testing sample files from `http://jell.yfish.us/`, not required if you've already calculated the FPS of your encoders.
* (Optional) Active network connection - as said above, `rate_calculator.py` will download a 142MB file from the internet, so you must either provide that file or a network connection to download it.

### Configuration

You should set your encoders to delete/move the source file after encoding.  I mean, there's not really any _need_ to but I think it's good practice to delete files you won't be using, and if item 7 in the **Shortcomings** is completed then these scripts will see those left-behind files as unencoded/to-be-requeued files and move them to other encoders, wasting CPU power and time to redo compelted work.

As detailed below, you should set the handbrake image environment variables `AUTOMATED_CONVERSION_SOURCE_STABLE_TIME` and `AUTOMATED_CONVERSION_CHECK_INTERVAL` to `1` when calculating processing rate, or else your processing rate calculations will be off - I saw a 'loss' between 50% and 60% when set to the default `5`.

## Program Flow

First, run `rate_calculator.py path/to/base/directory/` to calculate the FPS of your encoders.  This will download a sample file and run it through each of your predefined profiles, then calculate roughly how fast the encoders can process files for that profile.  It will download the sample file to `path/to/base/directory/`, then copy it to each 

Once the script has finished (testing 2 profiles for 4 encoders took me ~5 minutes, YMMV for processor power), it will create `rates.json`, a simple define of how fast each profile is on each encoder.  Here's mine, for example:

```
{
    "folkvangr": {
        "animation": 20,
        "movies": 19,
        "shows": 20
    },
    "folkvangr-2": {
        "animation": 21,
        "movies": 19,
        "shows": 21
    },
    "myrkheim": {
        "animation": 26,
        "movies": 25,
        "shows": 26
    },
    "myrkheim-2": {
        "animation": 26,
        "movies": 25,
        "shows": 26
    }
}
```

After that, you're free to run `balancer.py path/to/base/directory/` to calculate file load and distribute jobs to the individual encoders.

Both scripts are hands off, you could probably just run `python3 rate_calculator.py path/to/base/directory/ && python3 balancer.py path/to/base/directory/` and go watch a movie while you wait for encodes to complete.

## Shortcomings / Areas for Improvement

1. The calculation of FPS will be 13-15% lower than your 'real' FPS, because the script starts timing as soon as the sample file copy has finished and uses the final modification time of the output file as the duration for calculation (Total Frames / Duration = Processing FPS).  It's not perfect and could likely be improved, but this works and I consider this acceptable when taking into account transfer speeds and scripted wait time in the original image.  I **highly recommend** you set the environment variables `AUTOMATED_CONVERSION_SOURCE_STABLE_TIME` and `AUTOMATED_CONVERSION_CHECK_INTERVAL` to `1` when calculating processing rate, to get your FPS as close as correct.  Alternatively, you can encode a file yourself manually (there is a web GUI, after all) and write down the average FPS you see.  If you have an alternative way of calculating processing rate, please let me know or open a pull request!

2. The rate calculator requires one of your profiles be named `shows` if you have a profile called `anime` or `animation`, because:

3. The rate calculator won't calculate for profiles that match `anime` or `animation`, because I didn't go looking for an example animated video to use for sampling.  This really shouldn't matter for most people, but I was concerned for my animated video profile so I decided to leave it alone and do some assumptions.  I set the animated processing rate to be equal to TV show processing rate and that should be close enough.  If anyone knows of a publically available high bitrate animation sample file (~40Mbps, ~30s long) this project could use, please let me know or submit a PR that adds that functionality!

4. The balancer is not active, you have to run it every time you want to process files.  I debated adding the ability to calculate load on the fly and move files around, but since I didn't look into whether or not the original handbrake image exposes how far into processing it is, I decided against it and kept this as a simple batch analyzer/mover.  As usual, if you've got a better idea, I'm all ears.

5. The balancer only uses one algorithm for distributing load, and I'm sure there are better ones out there that I didn't think of.  Frankly, the default one is solid, it will evenly distribute the load so that each encoder you have will finish in roughly the same time.  I'll probably add additional simpler algorithms to use (like assigning encoder X every X file, encoder X+1 every X+1 files, or filling up one executor at a time until it matches the executor with the slowest load total, sort of like unRAID's Fill-Up method of data allocation), or perhaps tweaking the order files are added in (smallest first, get the small batch files out of the way while you're ripping additional files for another evaluation later)

6. The balancer should probably have an option to recalculate processing rate.

7. The balancer should probably be able to function if one or more encoders is offline (currently, it'll just send anywhere and not care).  I'll probably do this next, it should be as easy as getting the current "queue" of files and seeing if files are being written to the output folder, and if not then assume these files aren't being processed and should be moved elsewhere.
