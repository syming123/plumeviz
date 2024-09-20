import numpy as np
import queue


from common.entity import Region


def calculate_region3d(datas, threshold=1e-6, interval=4):
    region_group = []
    size = datas.shape
    marks = np.zeros(size, np.int32)

    # 3维区域扩散
    def region_growing3d(region_id, seed, th=threshold):
        que = queue.Queue()
        que.put(seed)
        marks[seed] = -1
        region = Region()
        region.id = region_id
        region.bounds[0] = size[0]
        region.bounds[2] = size[1]
        region.bounds[4] = size[2]
        region.bounds[6] = size[3]

        while not que.empty():
            pnt = que.get()
            if datas[pnt] > th:
                marks[pnt] = region_id
                region.count = region.count + 1
                region.bounds[0] = min(region.bounds[0], pnt[0])
                region.bounds[1] = max(region.bounds[1], pnt[0])
                region.bounds[2] = min(region.bounds[2], pnt[1])
                region.bounds[3] = max(region.bounds[3], pnt[1])
                region.bounds[4] = min(region.bounds[4], pnt[2])
                region.bounds[5] = max(region.bounds[5], pnt[2])
                region.bounds[6] = min(region.bounds[6], pnt[3])
                region.bounds[7] = max(region.bounds[7], pnt[3])
            else:
                continue

            dt = [1, -1, 0,  0, 0,  0, 0,  0]
            dx = [0,  0, 1, -1, 0,  0, 0,  0]
            dy = [0,  0, 0,  0, 1, -1, 0,  0]
            dz = [0,  0, 0,  0, 0,  0, 1, -1]
            max_t = size[0] - 1
            max_x = size[1] - 1
            max_y = size[2] - 1
            max_z = size[3] - 1

            for ii in range(8):
                t = pnt[0] + dt[ii]
                x = pnt[1] + dx[ii]
                y = pnt[2] + dy[ii]
                z = pnt[3] + dz[ii]

                if 0 <= t <= max_t and 0 <= x <= max_x and 0 <= y <= max_y and 0 <= z <= max_z and marks[t][x][y][z] == 0:
                    que.put((t, x, y, z))
                    marks[t][x][y][z] = -1
        return region

    # 间隔选取种子点计算区域
    for h in range(size[0]):
        for i in range(0, size[1], interval):
            for j in range(0, size[2], interval):
                for k in range(0, size[3], interval):
                    if marks[h][i][j][k] == 0:
                        region = region_growing3d(len(region_group) + 1, (h, i, j, k))
                        if region.count > 0:
                            region_group.append(region)
    return region_group, marks


def region_filter(regions, marks, threshold=100):
    new_regions = []
    ids = []
    for region in regions:
        if region.count > threshold:
            new_regions.append(region)
            ids.append(region.id)

    # !!! too slow !!!
    for t in range(marks.shape[0]):
        for i in range(marks.shape[1]):
            for j in range(marks.shape[2]):
                for k in range(marks.shape[3]):
                    if marks[t][i][j][k] not in ids:
                        marks[t][i][j][k] = 0
    return new_regions, marks

