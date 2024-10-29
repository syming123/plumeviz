import numpy as np
import matplotlib.pyplot as plt

from common.entity import Region
from visualization.core import reader

if __name__ == '__main__':
    frame = reader.read_frame('../data/processed/20210509/data-20210509T0000.bin')
    regions, marks = reader.read_regions('../data/processed/20210509/region.bin')
    max_r = Region()
    for region in regions:
        if region.count > max_r.count:
            max_r = region
    data = frame.imaging.data[max_r.bounds[2]:max_r.bounds[3],max_r.bounds[4]:max_r.bounds[5], max_r.bounds[6]:max_r.bounds[7]]
    xx = data.reshape(-1)
    #xx[xx < 1e-6] = 1e-6
    #xx = np.log10(xx)
    d = []
    for i in xx:
        if i > 1e-6:
            d.append(i)
    d = np.array(d)
    d = np.log10(d)
    print(np.min(d), np.max(d))

    plt.hist(x=d,
             bins=50,
             #log=True,
             color='steelblue',
             density=True,
             edgecolor='black'
             )
    # 添加x轴和y轴标签
    plt.xlabel('v')
    plt.ylabel('f')
    plt.title('bin')
    plt.show()

