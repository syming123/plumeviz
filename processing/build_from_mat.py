# ============================================================
# build_from_mat.py
# ------------------------------------------------------------
# Convert mat data into data that can be read directly.
# Data from 2018 to 2023.
# ============================================================

import numpy as np
import scipy.io as sio
import joblib
import os


def load_imaging_from_mat(file_path, data_type='Id_filt'):
    image = {}
    data = sio.loadmat(file_path)
    covis = data['imaging'][0][0]
    grid = covis['grid'][0][0]
    bounds = grid['axis'][0]
    spacing = grid['spacing'][0][0]
    image['data'] = grid[data_type].transpose(1, 0, 2)
    image['bounds'] = bounds
    image['spacing'] = [spacing['dx'][0][0], spacing['dy'][0][0], spacing['dz'][0][0]]
    return image


def load_diffuse_from_mat(file_path, diffuse_type='decorrelation intensity', bathy_type='bathy_filt'):
    diffuse = {}
    bathy = {}
    data = sio.loadmat(file_path)
    covis = data['diffuse'][0][0]
    grids = covis['grid'][0]
    for grid in grids:
        if grid[0][0]['type'][0] == diffuse_type:
            diffuse['data'] = grid[0][0]['v'].transpose()
            diffuse['bounds'] = grid[0][0]['axis'][0, 0:4]
            diffuse['spacing'] = [grid[0][0]['spacing'][0]['dx'][0][0][0], grid[0][0]['spacing'][0]['dy'][0][0][0]]
        elif grid[0][0]['type'][0] == bathy_type:
            bathy['data'] = grid[0][0]['v'].transpose()
            bathy['bounds'] = grid[0][0]['axis'][0, 0:4]
            bathy['spacing'] = [grid[0][0]['spacing'][0]['dx'][0][0][0], grid[0][0]['spacing'][0]['dy'][0][0][0]]
    return diffuse, bathy


def load_bathy(file_path):
    with open(file_path, 'rb') as file:
        bathy = joblib.load(file)
    return bathy


def make_bundle(image_path, bathy_path, diffuse_path):
    image = load_imaging_from_mat(image_path)
    diffuse, _ = load_diffuse_from_mat(diffuse_path)
    bathy = load_bathy(bathy_path)
    bundle = {'image': image, 'diffuse': diffuse, 'bathy': bathy}
    return bundle


def write_bundle(bundle, file_path):
    with open(file_path, "wb") as file:
        joblib.dump(bundle, file)


def sweep(image_dir, bathy_path, diffuse_dir, target_dir):
    image = {}
    diffuse = {}
    for filename in os.listdir(image_dir):
        if filename[0] == 'C':
            image[filename[6:17]] = image_dir + '/' + filename
    for filename in os.listdir(diffuse_dir):
        if filename[0] == 'C':
            diffuse[filename[6:17]] = diffuse_dir + '/' + filename

    for file_date in image:
        if file_date in diffuse:
            print('data: ' + file_date)
            my_bundle = make_bundle(image[file_date], bathy_path, diffuse[file_date])
            write_bundle(my_bundle, target_dir + '/' + 'Data-' + file_date + '00.bin')


# build
if __name__ == '__main__':
    sweep('./data/mat/image', './res/bathy/bathy-2018To2023.bin', './data/mat/diffuse', '../data/processed')

