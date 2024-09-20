import numpy as np
from scipy.interpolate import interpn


def scale_data3d(data: np.ndarray, target_size: tuple) -> np.ndarray:
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
