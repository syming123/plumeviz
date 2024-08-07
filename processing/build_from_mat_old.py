# ============================================================
# build_from_mat_old.py
# ------------------------------------------------------------
# Convert mat data into data that can be read directly.
# Data from 2010 to 2015.
# ============================================================

import numpy as np
import scipy
import scipy.io as sio
from scipy.interpolate import interpn
import joblib
import os


def scale_data(data, target_size):
    size = data.shape
    x1 = np.linspace(0, size[0] - 1, size[0])
    x2 = np.linspace(0, size[1] - 1, size[1])
    x3 = np.linspace(0, size[2] - 1, size[2])
    points = (x1, x2, x3)

    x1_new = np.linspace(0, size[0] - 1, target_size[0])
    x2_new = np.linspace(0, size[1] - 1, target_size[1])
    x3_new = np.linspace(0, size[2] - 1, target_size[2])
    xx, yy, zz = np.meshgrid(x1_new, x2_new, x3_new, indexing='ij')
    new_points = np.array([xx, yy, zz]).T

    result = interpn(points, data, new_points, bounds_error=False, fill_value=True).transpose(2, 1, 0)
    return result


def load_imaging_from_mat_old(file_path):
    image = {}
    data = sio.loadmat(file_path)
    covis = data['covis'][0][0]
    grid = covis['grid'][0][0]
    bounds = grid['axis'][0]
    spacing = grid['spacing'][0][0]
    image['data'] = grid['v'].transpose(1, 0, 2)
    image['bounds'] = bounds
    image['spacing'] = [spacing['dx'][0][0], spacing['dy'][0][0], spacing['dz'][0][0]]
    return image


def load_doppler_from_mat(file_path):
    doppler = {}
    data = sio.loadmat(file_path)
    covis = data['covis'][0][0]
    grid = covis['grid'][0][0][0][0]
    bounds = grid['axis'][0]
    spacing = grid['spacing'][0][0]
    spacing = [spacing[0][0][0]/2, spacing[1][0][0]/2, spacing[2][0][0]/2]
    old_size = grid['v_filt'].shape
    new_size = [(old_size[0]-1)*2+1, (old_size[1]-1)*2+1, (old_size[2]-1)*2+1]
    new_data = scale_data(grid['v_filt'], new_size)
    doppler['data'] = new_data.transpose(1, 0, 2)
    doppler['bounds'] = bounds
    doppler['spacing'] = spacing
    return doppler


def load_diffuse_from_mat_old(file_path):
    diffuse = {}
    data = sio.loadmat(file_path)
    covis = data['covis'][0][0]
    grid = covis['grid'][0][0][0][0]
    bounds = grid['axis'][0]
    spacing = grid['spacing'][0][0]
    spacing = [spacing[0][0][0], spacing[1][0][0]]
    diffuse['data'] = grid['v'].transpose()
    diffuse['bounds'] = bounds
    diffuse['spacing'] = spacing
    return diffuse


def load_bathy_old(file_path):
    with open(file_path, 'rb') as file:
        bathy = joblib.load(file)
    return bathy


def make_bundle(image_path, doppler_path, bathy_path, diffuse_path):
    image = load_imaging_from_mat_old(image_path)
    doppler = load_doppler_from_mat(doppler_path)
    bathy = load_bathy_old(bathy_path)
    diffuse = load_diffuse_from_mat_old(diffuse_path)
    bundle = {'image': image, 'doppler': doppler, 'bathy': bathy, 'diffuse': diffuse}
    return bundle


def write_bundle(bundle, file_path):
    with open(file_path, "wb") as file:
        joblib.dump(bundle, file)


def sweep(image_dir, doppler_dir, diffuse_dir, bathy_path, target_dir):
    image = {}
    doppler = {}
    diffuse = {}
    for filename in os.listdir(image_dir):
        if filename[0] == 'A':
            image[filename[21:32]] = image_dir + '/' + filename
    for filename in os.listdir(doppler_dir):
        if filename[0] == 'A':
            doppler[filename[21:32]] = doppler_dir + '/' + filename
    for filename in os.listdir(diffuse_dir):
        if filename[0] == 'A':
            diffuse[filename[21:32]] = diffuse_dir + '/' + filename

    for file_date in image:
        if file_date in doppler and file_date in diffuse:
            print('data: ' + file_date)
            my_bundle = make_bundle(image[file_date], doppler[file_date], bathy_path, diffuse[file_date])
            write_bundle(my_bundle, target_dir + '/' + 'Data-' + file_date + '00.bin')


# build
if __name__ == '__main__':
    sweep('./data/mat/image',
          './data/mat/doppler',
          './data/mat/diffuse',
          './res/bathy/bathy-2010To2015.bin',
          './data/processed')
