# ============================================================
# 多普勒数据计算速度场，热通量
# ============================================================

import numpy as np
import vtk, vtkmodules
import math
import scipy
from sklearn.preprocessing import normalize

from common.entity import UniformGrid
from visualization.core import processor

th = 3e-5
lamb = 1.06
lamb2 = lamb * lamb
alpha = 0.1
alpha_T = 1.32e-4
ro_ref = 1.04e3
Cp = 3.92e3
g = 9.8


# class DopplerRegion:
#     def __init__(self):
#         self.id = -1
#         self.bounds = []
#
#
# def calculate_centerline_points(region, image, marks, interval=1):
#     bounds = image.bounds
#     spacing = image.spacing
#     points = []
#     [min_x, max_x, min_y, max_y, min_z, max_z] = region.bounds
#     bounding_data = image.data[min_x:max_x + 1, min_y:max_y + 1, min_z:max_z + 1]
#     bounding_marks = marks[min_x:max_x + 1, min_y:max_y + 1, min_z:max_z + 1]
#     for z in range(0, bounding_data.shape[2], interval):
#         plane_data = bounding_data[:, :, z]
#         plane_marks = bounding_marks[:, :, z]
#         plane_data[plane_marks != region.id] = 0
#
#         max_v = np.max(plane_data)
#         max_points = np.where(plane_data == max_v)
#         local_points = (max_points[0][0] + min_x, max_points[1][0] + min_y, z + min_z)
#         points.append((local_points[0] * spacing[0] + bounds[0], local_points[1] * spacing[1] + bounds[2],
#                        local_points[2] * spacing[2] + bounds[4]))
#     return points


def interpolate_sight_velocity(doppler: UniformGrid, center_line: dict):
    doppler_data = doppler.data
    grid_bounds = doppler.bounds
    grid_spacing = doppler.spacing

    npoints = np.array(center_line['center_points'])

    i = np.array([np.floor((npoints[:, 0] - grid_bounds[0]) / grid_spacing[0]),
                  np.ceil((npoints[:, 0] - grid_bounds[0]) / grid_spacing[0])]).astype(np.int32)
    j = np.array([np.floor((npoints[:, 1] - grid_bounds[2]) / grid_spacing[1]),
                  np.ceil((npoints[:, 1] - grid_bounds[2]) / grid_spacing[1])]).astype(np.int32)
    k = np.array([np.floor((npoints[:, 2] - grid_bounds[4]) / grid_spacing[2]),
                  np.ceil((npoints[:, 2] - grid_bounds[4]) / grid_spacing[2])]).astype(np.int32)
    wx = np.zeros(shape=i.shape)
    wx[1, :] = np.abs((i[0, :] * grid_spacing[0] + grid_bounds[0]) - npoints[:, 0]) / grid_spacing[0]
    wx[0, :] = 1 - wx[1, :]
    wy = np.zeros(shape=i.shape)
    wy[1, :] = np.abs((j[0, :] * grid_spacing[1] + grid_bounds[2]) - npoints[:, 1]) / grid_spacing[1]
    wy[0, :] = 1 - wy[1, :]
    wz = np.zeros(shape=i.shape)
    wz[1, :] = np.abs((k[0, :] * grid_spacing[2] + grid_bounds[4]) - npoints[:, 2]) / grid_spacing[2]
    wz[0, :] = 1 - wz[1, :]
    points_v = np.zeros(len(npoints))
    for n in range(2):
        for m in range(2):
            for l in range(2):
                w = wx[l, :] * wy[m, :] * wz[n, :]
                points_v = points_v + doppler_data[i[l, :], j[m, :], k[n, :]] * w

    center_line['sight_velocity'] = points_v
    return


def calculate_center_velocity(center_line: dict, origin=(0.0, 0.0, 0.0)):
    size = center_line['size']
    points = center_line['center_points']
    center_velocity = np.zeros(size)

    tan_vec = np.zeros((size, 3))
    tan_vec[0] = points[1] - points[0]
    tan_vec[-1] = points[size - 1] - points[size - 2]
    tan_vec[1: size - 1] = ((points[1: size - 1] - points[0: size - 2]) + (points[2:] - points[1:size - 1])) / 2

    sight_vec = np.array(points - origin)

    unit_tan_vec = normalize(tan_vec, axis=1, norm='l2')
    unit_sight_vec = normalize(sight_vec, axis=1, norm='l2')

    center_velocity = center_line['sight_velocity'] / np.sum(unit_tan_vec * unit_sight_vec, axis=1)
    center_line['center_velocity'] = center_velocity
    center_line['tan_vec'] = unit_tan_vec
    center_line['sight_vec'] = unit_sight_vec

    return


def calculate_velocity_field(doppler, center_line: dict):
    shape = [doppler.data.shape[0], doppler.data.shape[1], doppler.data.shape[2]]
    velocity_field = np.zeros((shape + [3]))
    bounds = [0, doppler.data.shape[0], 0, doppler.data.shape[1], 0, doppler.data.shape[2]]
    spacing = doppler.spacing

    size = center_line['size']
    points = center_line['center_points']
    center_v = center_line['center_velocity']
    center_tan_vec = center_line['tan_vec']

    for k in range(size):
        z = points[k][2]
        zi = k + bounds[4]
        v_vec = center_v[k] * center_tan_vec[k]
        vh = np.array([v_vec[0], v_vec[1], 0.0])
        for i in range(bounds[0], bounds[1]):
            for j in range(bounds[2], bounds[3]):
                if doppler.data[i][j][zi] <= 1e-9:
                    continue
                vp = doppler.data[i][j][zi]
                p = np.array([bounds[0] + i * spacing[0],
                              bounds[1] + j * spacing[1],
                              z])
                unit_p = p / np.linalg.norm(p)
                wp = (vp - np.dot(vh, unit_p)) / unit_p[2]
                velocity_field[i][j][zi] = [v_vec[0], v_vec[1], wp]

    return velocity_field


def Q_M_estimate(w_field, center_line, spacing):
    size = center_line['size']
    points = center_line['center_points']
    center_v = center_line['center_velocity']
    center_tan_vec = center_line['tan_vec']

    Q = np.zeros(size)
    M = np.zeros(size)

    center_w = np.einsum('i, ij->ij', center_v, center_tan_vec)[:, 2]

    for k in range(size):
        plane_w_field = w_field[:, :, k]
        plane_w_field[plane_w_field < (center_w[k] * 0.1)] = 0
        Q[k] = np.sum(plane_w_field * np.power(spacing, 2)) / 0.9
        M[k] = np.sum(np.power(plane_w_field, 2) * np.power(spacing, 2)) / 0.99

    return Q, M


def be_estimate(Q, M):
    return Q / np.sqrt(2 * np.pi * M)


def Zi_estimate(be):
    return (5 * be) / (6 * alpha)


def B0_estimate(Q, Zi):
    return np.power(Q, 3) / ((3 * np.pi * (1 + lamb2)) / (2 * np.power(5 / (6 * alpha), 4)) * np.power(Zi, 5))


def H0_estimate(B0):
    return (Cp * ro_ref) / (g * alpha_T) * B0


def get_H0(v_field, center_line, spacing):
    w_field = v_field[:, :, :, 2]
    Q, M = Q_M_estimate(w_field, center_line, spacing)
    be = be_estimate(Q, M)
    Zi = Zi_estimate(be)
    B0 = B0_estimate(Q, Zi)
    H0 = H0_estimate(B0)
    return H0


def calculate_H_field(v_field, spacing):
    w_field = v_field[:, :, :, 2]
    dS = np.power(spacing, 2)
    Q_field = w_field * dS
    # M_field = np.power(w_field, 2) * dS
    be = 1 / np.sqrt(2 * np.pi)
    Zi = (5 * be) / (6 * alpha)
    B_field = B0_estimate(Q_field, Zi)
    H_field = H0_estimate(B_field)
    return H_field


# 计算速度场
# def get_velocity_field(image, doppler, region0, marks):
#     bounds = image.bounds
#     region = DopplerRegion()
#     region.id = region0.id
#     region.bounds = region0.bounds[2:]
#     centerline_points = calculate_centerline_points(region, image, marks)
#     centerline_points, _ = processor.poly_curve_fit(centerline_points)
#
#     centerline_list_points = []
#
#     for p in centerline_points:
#         centerline_list_points.append([min(max(p[0], bounds[0]), bounds[1]),
#                                        min(max(p[1], bounds[2]), bounds[3]),
#                                        min(max(p[2], bounds[4]), bounds[5])])
#
#     center_line = {
#         'center_points': np.array(centerline_list_points),
#         'size': len(centerline_list_points)
#     }
#
#     interpolate_sight_velocity(doppler.data, center_line, image.bounds, image.spacing)
#     calculate_center_velocity(center_line)
#     v_field = calculate_velocity_field(doppler, marks, region, center_line)
#
#     return v_field, center_line

def get_velocity_field(image: UniformGrid, doppler: UniformGrid):
    centerline_points = processor.calculate_centerline_points(image)
    centerline_points, _ = processor.poly_curve_fit(centerline_points)

    center_line = {
        'center_points': np.array(centerline_points),
        'size': len(centerline_points)
    }

    interpolate_sight_velocity(doppler, center_line)
    calculate_center_velocity(center_line)
    v_field = calculate_velocity_field(doppler, center_line)

    return v_field, center_line


# 计算热通量场
def get_heat_flux_field(v_field, center_line, spacing=0.25):
    H = get_H0(v_field, center_line, spacing)
    H_field = calculate_H_field(v_field, spacing)

    return H, H_field


def build_image_grid(array_dict, bounds, spacing, need_smooth=True):
    # points = [(x[i], y[i], z[i]) for i in range(len(x))]
    image = vtk.vtkImageData()
    image.SetDimensions(math.ceil((bounds[1] - bounds[0]) / spacing[0]) + 1,
                        math.ceil((bounds[3] - bounds[2]) / spacing[1]) + 1,
                        math.ceil((bounds[5] - bounds[4]) / spacing[2]) + 1)

    image.SetOrigin(bounds[0], bounds[2], bounds[4])
    image.SetSpacing(spacing[0], spacing[1], spacing[2])

    dims = image.GetDimensions()
    pointsNum = dims[0] * dims[1] * dims[2]
    size = pointsNum

    vtk_arrays = []
    input_arrays = []

    array_num = 0
    for array_name, array_value in array_dict.items():
        if need_smooth and len(array_value.shape) <= 3:
            array_value = scipy.ndimage.gaussian_filter(array_value, sigma=1.1, mode='nearest')
        if len(array_value.shape) < 3:
            temp_array = vtkmodules.util.numpy_support.numpy_to_vtk(array_value, deep=True, array_type=vtk.VTK_FLOAT)
            temp_array.SetName(array_name)
            temp_array.SetNumberOfComponents(array_value.shape[-1])
            vtk_arrays.append(temp_array)
        else:
            vtk_arrays.append(vtk.vtkDoubleArray())
            vtk_arrays[array_num].SetName(array_name)
            if len(array_value.shape) == 4:
                vtk_arrays[array_num].SetNumberOfComponents(array_value.shape[3])
                vtk_arrays[array_num].SetNumberOfTuples(size)
            else:
                vtk_arrays[array_num].SetNumberOfComponents(1)
                vtk_arrays[array_num].SetNumberOfTuples(size)
            index = 0
            for z in range(dims[2]):
                for y in range(dims[1]):
                    for x in range(dims[0]):
                        if len(array_value.shape) == 4:
                            vtk_arrays[-1].InsertTuple(index, array_value[x][y][z])
                        else:
                            vtk_arrays[-1].InsertTuple1(index, array_value[x][y][z])
                        index += 1
        array_num += 1

    for array in vtk_arrays:
        image.GetPointData().AddArray(array)
    return image


def save_image(image, path_dir, file_name):
    writer = vtk.vtkXMLImageDataWriter()
    writer.SetInputData(image)
    writer.SetFileName(path_dir + file_name)
    # writer.SetFileTypeToBinary()
    writer.Write()


# 对标量场的三线性插值采样
def trilinear_interlop(field, point):
    dim = field.shape
    [x, y, z] = point
    if x < 0 or y < 0 or z < 0:
        return 0
    ix = np.floor(x)
    iy = np.floor(y)
    iz = np.floor(z)
    fx = x - ix
    fy = y - iy
    fz = z - iz
    curr_data = field[int(ix)][int(iy)][int(iz)]
    if ix + 1 == dim[0]:
        ix -= 1
    if iy + 1 == dim[1]:
        iy -= 1
    if iz + 1 == dim[2]:
        iz -= 1
    dx = field[int(ix+1)][int(iy)][int(iz)]
    dy = field[int(ix)][int(iy+1)][int(iz)]
    dz = field[int(ix)][int(iy)][int(iz+1)]
    return curr_data + fx*(dx-curr_data) + fy*(dy-curr_data) + fz*(dz-curr_data)


# 寻找一个点作为速度场流线种子点选取的中心，这里沿中心线寻找热通量值最大的一个点作为中心点
def find_seeds_center(centerline_points, H_field, bounds, spacing):
    max_v = 0
    max_idx = 0
    for i in range(len(centerline_points)):
        point = centerline_points[i]
        grid_p = ((point[0]-bounds[0])/spacing[0], (point[1]-bounds[2])/spacing[1], (point[2]-bounds[4])/spacing[2])
        vi = trilinear_interlop(H_field, grid_p)
        if vi > max_v:
            max_v = vi
            max_idx = i
    return centerline_points[max_idx]
