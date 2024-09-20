# ============================================================
# 数据裁剪，特征区域提取，提取羽流中心线
# ============================================================

import numpy as np
import queue
from scipy.optimize import curve_fit

from common.entity import DataFrame, UniformGrid


# ------------------------------------------------------------
# 进行数据裁剪
# ------------------------------------------------------------

# 计算公共边界
def calculate_bounds(frame: DataFrame) -> list:
    image = frame.imaging
    doppler = frame.doppler
    diffuse = frame.diffuse

    bounds_2d = []
    bounds_3d = []
    if image.dim == 3:
        bounds_2d.append(image.bounds[:4])
        bounds_3d.append(image.bounds[4:])
    if doppler.dim == 3:
        bounds_2d.append(doppler.bounds[:4])
        bounds_3d.append(doppler.bounds[4:])
    if diffuse.dim == 2:
        bounds_2d.append(diffuse.bounds[:4])
    arr2d = np.array(bounds_2d)
    arr3d = np.array(bounds_3d)
    return [max(arr2d[:, 0]), min(arr2d[:, 1]), max(arr2d[:, 2]), min(arr2d[:, 3]), max(arr3d[:, 0]), min(arr3d[:, 1])]


# 对均匀网格数据进行裁剪
def cut_uniform(old_data: UniformGrid, new_bounds: list) -> UniformGrid:
    new_data = old_data.copy()
    old_bounds = old_data.bounds
    spacing = old_data.spacing
    dim = old_data.dim
    size = new_data.data.shape

    delta = []
    for i in range(dim*2):
        delta.append(int((abs(new_bounds[i] - old_bounds[i])) / spacing[int(i / 2)]))

    new_data.bounds = new_bounds
    if dim == 2:
        new_data.data = new_data.data[delta[0]:size[0]-delta[1], delta[2]:size[1]-delta[3]]
    elif dim == 3:
        new_data.data = new_data.data[delta[0]:size[0]-delta[1], delta[2]:size[1]-delta[3], delta[4]:size[2]-delta[5]]
    return new_data


# 对所有声纳数据进行裁剪
def cut_all(sonar_data, bounds):
    cut_all_data = []
    if sonar_data.imaging.dim == 3:
        cut_all_data.image = cut_uniform(sonar_data.imaging, bounds)
    if sonar_data.doppler.dim == 3:
        cut_all_data.doppler = cut_uniform(sonar_data.doppler, bounds)
    if sonar_data.bathy.dim == 2:
        cut_all_data.bathy = cut_uniform(sonar_data.bathy, bounds)
    if sonar_data.diffuse.dim == 2:
        cut_all_data.diffuse = cut_uniform(sonar_data.diffuse, bounds)
    return cut_all_data


# ------------------------------------------------------------
# 特征区域检测
# ------------------------------------------------------------

# 定义特征区域对象
class Region:
    def __init__(self):
        self.id = 0
        self.count = 0
        self.bounds = [0, 0, 0, 0, 0, 0]


# 特征区域提取
def calculate_region(data, threshold=1e-6, interval=4):
    region_group = []
    size = data.shape
    marks = np.zeros(size, np.int32)

    # 3维区域扩散
    def region_growing(region_id, seed, th=threshold):
        que = queue.Queue()
        que.put(seed)
        marks[seed] = -1
        region = Region()
        region.id = region_id
        region.bounds[0] = size[0]
        region.bounds[2] = size[1]
        region.bounds[4] = size[2]

        while not que.empty():
            pnt = que.get()
            if data[pnt] > th:
                marks[pnt] = region_id
                region.count = region.count + 1
                region.bounds[0] = min(region.bounds[0], pnt[0])
                region.bounds[1] = max(region.bounds[1], pnt[0])
                region.bounds[2] = min(region.bounds[2], pnt[1])
                region.bounds[3] = max(region.bounds[3], pnt[1])
                region.bounds[4] = min(region.bounds[4], pnt[2])
                region.bounds[5] = max(region.bounds[5], pnt[2])
            else:
                continue

            dx = [1, -1, 0, 0, 0, 0]
            dy = [0, 0, 1, -1, 0, 0]
            dz = [0, 0, 0, 0, 1, -1]
            max_x = size[0] - 1
            max_y = size[1] - 1
            max_z = size[2] - 1
            for ii in range(6):
                x = pnt[0] + dx[ii]
                y = pnt[1] + dy[ii]
                z = pnt[2] + dz[ii]
                if 0 <= x <= max_x and 0 <= y <= max_y and 0 <= z <= max_z and marks[x][y][z] == 0:
                    que.put((x, y, z))
                    marks[x][y][z] = -1
        return region

    # 间隔选取种子点计算区域
    for i in range(0, size[0], interval):
        for j in range(0, size[1], interval):
            for k in range(0, size[2], interval):
                if marks[i][j][k] == 0:
                    region = region_growing(len(region_group) + 1, (i, j, k))
                    if region.count > 0:
                        region_group.append(region)
    return region_group, marks


# ------------------------------------------------------------
# 提取羽流中心线
# ------------------------------------------------------------

# 计算中心线点集
# def centerline_points(region, image, marks, interval=1):
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


def calculate_centerline_points(region_grid: UniformGrid, interval=1):
    bounds = region_grid.bounds
    spacing = region_grid.spacing
    points = []
    for z in range(0, region_grid.data.shape[2], interval):
        plane_data = region_grid.data[:, :, z]
        max_v = np.max(plane_data)
        if max_v > 1e-9:
            max_points = np.where(plane_data == max_v)
            points.append((max_points[0][0] * spacing[0] + bounds[0], max_points[1][0] * spacing[1] + bounds[2],
                        z * spacing[2] + bounds[4]))
    return points


# 多项式函数曲线拟合
def poly_curve_fit(points):
    points_array = np.array(points)
    x = points_array[:, 0]
    y = points_array[:, 1]
    z = points_array[:, 2]

    def curve_func(t, a0, a1, a2):
        return a0 + a1 * t + a2 * t ** 2

    p0 = [1, 1, 1]
    params_x, pcov_x = curve_fit(curve_func, z, x, p0)
    params_y, pcov_x = curve_fit(curve_func, z, y, p0)

    xx = curve_func(z, *params_x)
    yy = curve_func(z, *params_y)

    new_points = []
    for i in range(len(points)):
        new_points.append((xx[i], yy[i], z[i]))

    return new_points, [params_x, params_y]


# 计算曲率
def calculate_curvature(points, params):
    K = []
    for p in points:
        (x, y, z) = p
        x1 = 2*params[0][0]*z + params[0][1]
        x2 = 2*params[0][0]
        y1 = 2*params[1][0]*z + params[1][1]
        y2 = 2*params[1][0]
        k = abs(x1*y2 - x2*y1)/np.sqrt(x1**2 + y1**2)
        K.append(k)
    return K
