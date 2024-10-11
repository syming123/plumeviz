import os
import numpy as np
import joblib

from common.entity import DataFrame
from preprocessing import load_from_mat
from preprocessing import region_detector


# 从指定目录中读取所有mat数据文件
def load_data(file_dir: str) -> list[DataFrame]:
    files = os.listdir(file_dir)
    data_frames = []

    # from 2010 to 2015
    if files[0][:5] == 'APLUW':
        imagings = {}
        dopplers = {}
        diffuses = {}
        for filename in files:
            if filename[42:49] == 'IMAGING':
                imagings[filename[21:32]] = filename
            elif filename[42:49] == 'DOPPLER':
                dopplers[filename[21:32]] = filename
            elif filename[42:49] == 'DIFFUSE':
                diffuses[filename[21:32]] = filename

        for time_str in imagings.keys():
            if time_str in dopplers.keys() and time_str in diffuses.keys():
                data_frame = DataFrame()
                data_frame.imaging = load_from_mat.load_imaging_from_mat_old(file_dir + '/' + imagings[time_str])
                data_frame.doppler = load_from_mat.load_doppler_from_mat(file_dir + '/' + dopplers[time_str])
                data_frame.diffuse = load_from_mat.load_diffuse_from_mat_old(file_dir + '/' + diffuses[time_str])
                data_frame.time_str = time_str + '00'
                data_frames.append(data_frame)

    # from 2018 to 2023
    elif files[0][:5] == 'COVIS':
        imagings = {}
        diffuses = {}
        for filename in files:
            if filename[22:29] == 'imaging':
                imagings[filename[6:17]] = filename
            elif filename[22:29] == 'diffuse':
                diffuses[filename[6:17]] = filename

        for time_str in imagings.keys():
            if time_str in diffuses.keys():
                data_frame = DataFrame()
                data_frame.imaging = load_from_mat.load_imaging_from_mat(file_dir + '/' + imagings[time_str])
                data_frame.diffuse = load_from_mat.load_diffuse_from_mat(file_dir + '/' + diffuses[time_str])
                data_frame.time_str = time_str + '00'
                data_frames.append(data_frame)

    return data_frames


# 对数据帧进行插值，以获取更多数据帧
def frame_interp(frame0: DataFrame, frame1: DataFrame, frame_number: int) -> list[DataFrame]:
    frames = [frame0]
    hours0 = int(frame0.time_str[9:11])
    hours1 = int(frame1.time_str[9:11])
    dt = int((hours1 - hours0) * 60 / (frame_number - 1))

    delta = 1 / (frame_number - 1)
    for i in range(frame_number-2):
        frame_i = frame0.copy()
        left = delta * (i + 1)
        right = delta * (frame_number - i - 2)
        frame_i.imaging.data = left * frame1.imaging.data + right * frame0.imaging.data
        frame_i.diffuse.data = left * frame1.diffuse.data + right * frame0.diffuse.data
        if frame0.doppler.dim == 3:
            frame_i.doppler.data = left * frame1.doppler.data + right * frame0.doppler.data
        frame_i.time_str = frame0.time_str[:9] + str(int(hours0 + (i + 1) * dt / 60)).zfill(2) + str((i + 1) * dt % 60).zfill(2)
        frames.append(frame_i)

    frames.append(frame1)
    return frames


# 对数据帧列表进行插值，以获取更多数据帧
def interp_frames(frames: list[DataFrame]):
    frame0 = frames[0]
    hours0 = int(frame0.time_str[9:11])
    results = [frame0]
    for i in range(1, len(frames)):
        frame = frames[i]
        hours = int(frame.time_str[9:11])
        new_frames = frame_interp(frame0, frame, (hours - hours0) * 6 + 1)
        frame0 = frame
        hours0 = hours
        results = results + new_frames[1:]

    return results


# 从数据帧列表构建数据帧文件，并返回文件名列表
def build_frames(frames: list[DataFrame], target_dir: str) -> list[str]:
    frame_index = []
    for frame in frames:
        file_name = 'data-' + frame.time_str + '.bin'
        target_path = target_dir + '/' + file_name
        with open(target_path, "wb") as file:
            joblib.dump(frame, file)
            frame_index.append(file_name)
            print('build file: ' + target_path)
    return frame_index


# 构建区域文件，并返回文件名
def build_regions(datas: np.ndarray, target_dir: str) -> str:
    datas = np.array(datas)
    regions, marks = region_detector.calculate_region3d(datas)
    regions, marks = region_detector.region_filter(regions, marks, threshold=100*marks.shape[0])
    region_file = {
        'regions': regions,
        'marks': marks
    }
    file_name = 'region' + '.bin'
    target_path = target_dir + '/' + file_name
    with open(target_path, "wb") as file:
        joblib.dump(region_file, file)
        print('build region file: ' + target_path)
    return file_name

# 指定源路径和目标路径，自动完成数据构建
def build_all(file_dir: str, target_dir: str):
    frames = load_data(file_dir)
    new_frames = interp_frames(frames)
    for i in range(len(new_frames)):
        new_frames[i].id = i
    frame_index = build_frames(new_frames, target_dir)
    datas = []
    for i in range(len(new_frames)):
        datas.append(new_frames[i].imaging.data)
    datas = np.array(datas)
    region_index = build_regions(datas, target_dir)
    index_file = {
        'frame_files': frame_index,
        'region_file': region_index
    }
    index_path = target_dir + '/index.bin'
    with open(index_path, "wb") as file:
        joblib.dump(index_file, file)
        print('build index file: ' + index_path)


if __name__ == '__main__':
    build_all('../data/mat/20210509', '../data/processed/20210509')

