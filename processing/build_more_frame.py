# ============================================================
# build_more_frame.py
# ------------------------------------------------------------
# Interpolate data to get more frames.
# ============================================================

import numpy as np
import joblib
import os

from imaging.core import reader


def frame_interlop(frame0, frame1, frame_number):
    frames = []
    frames.append(frame0)

    delta = 1 / (frame_number - 1)
    for i in range(frame_number-2):
        frame_i = frame0.copy()
        left = delta * (i + 1)
        right = delta * (frame_number - i - 2)
        frame_i.image.data = left * frame1.image.data + right * frame0.image.data
        frame_i.bathy.data = left * frame1.bathy.data + right * frame0.bathy.data
        frame_i.diffuse.data = left * frame1.diffuse.data + right * frame0.diffuse.data
        if frame0.doppler.dim == 3:
            frame_i.doppler.data = left * frame1.doppler.data + right * frame0.doppler.data
        frames.append(frame_i)

    frames.append(frame1)
    return frames


def write_file(frame, filename):
    bundle = {}
    image = {
        'data': frame.image.data,
        'bounds': frame.image.bounds,
        'spacing': frame.image.spacing
    }
    diffuse = {
        'data': frame.diffuse.data,
        'bounds': frame.diffuse.bounds,
        'spacing': frame.diffuse.spacing
    }
    bathy = {
        'data': frame.bathy.data,
        'bounds': frame.bathy.bounds,
        'spacing': frame.bathy.spacing
    }
    bundle['image'] = image
    bundle['diffuse'] = diffuse
    bundle['bathy'] = bathy

    if frame.doppler.dim == 3:
        doppler = {
            'data': frame.doppler.data,
            'bounds': frame.doppler.bounds,
            'spacing': frame.doppler.spacing
        }
        bundle['doppler'] = doppler

    with open(filename, 'wb') as f:
        joblib.dump(bundle, f)


def sweep_and_interlop(file_dir, target_dir, target_date):
    files = {}
    for filename in os.listdir(file_dir):
        if filename[5:13] == target_date:
            files[filename[14:18]] = filename
    keys = sorted(files.keys())

    targets = []
    key0 = keys[0]
    frame0 = reader.read_file(file_dir + '/' + files[key0])
    targets.append(frame0)
    for i in range(1, len(keys)):
        key_i = keys[i]
        frame1 = reader.read_file(file_dir + '/' + files[key_i])
        dt = int(key_i[:2]) - int(key0[:2])
        new_files = frame_interlop(frame0, frame1, dt * 6 + 1)
        targets = targets + new_files[1:]
        key0 = key_i
        frame0 = frame1

    for i in range(len(targets)):
        hour = int(i / 6)
        minute = (i % 6) * 10
        time_str = str(hour).zfill(2) + str(minute).zfill(2)
        target_name = 'Data-' + target_date + 'T' + time_str + '.bin'
        print('create: ' + target_name)
        write_file(targets[i], target_dir + '/' + target_name)


# build
if __name__ == '__main__':
    sweep_and_interlop('./data/processed', './data/interlop', '20211010')
    sweep_and_interlop('./data/processed', './data/interlop', '20141008')

