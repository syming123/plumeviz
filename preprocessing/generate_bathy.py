import numpy as np
import joblib
from scipy.interpolate import interpn

def scale_data(data, target_size):
    size = data.shape
    x1 = np.linspace(0, size[0] - 1, size[0])
    x2 = np.linspace(0, size[1] - 1, size[1])
    points = (x1, x2)

    x1_new = np.linspace(0, size[0] - 1, target_size[0])
    x2_new = np.linspace(0, size[1] - 1, target_size[1])
    xx, yy = np.meshgrid(x1_new, x2_new, indexing='ij')
    new_points = np.array([xx, yy]).T

    result = interpn(points, data, new_points, bounds_error=False, fill_value=True).transpose(1, 0)
    return result


if __name__ == '__main__':
    with open('../res/bathy/filtered_data_all.npy', 'rb') as file:
        points = joblib.load(file)
        data = np.zeros((51, 51))
        weight = np.zeros((51, 51))
    for p in points:
        #if -44 < p[0] < 6 and -38 < p[1] < 12:
        if -41 < p[0] < 9 and -38 < p[1] < 12:
            print(p)
            x = (p[0] + 41)
            y = (p[1] + 38)
            z = p[2]
            ii = [
                int(np.floor(x)),
                int(np.ceil(x))
            ]
            jj = [
                int(np.floor(y)),
                int(np.ceil(y))
            ]
            for i in range(len(ii)):
                wx = 1 - abs(ii[i] - x)
                for j in range(len(jj)):
                    wy = 1 - abs(jj[j] - y)
                    w = np.sqrt(wx**2 + wy**2)
                    data[ii[i]][jj[j]] = data[ii[i]][jj[j]] + w*z
                    weight[ii[i]][jj[j]] = weight[ii[i]][jj[j]] + w
    weight[weight == 0] = 1
    data = data / weight + 1
    data = scale_data(data, (101, 101))

    bathy = {
        'data': data,
        'bounds': [-40, 10, -40, 10, 0, 0],
        'spacing': [0.5, 0.5]
    }
    with open('../res/bathy/bathy-2010To2015.bin', "wb") as file:
        joblib.dump(bathy, file)