import scipy.io as sio

from common.entity import UniformGrid
from common.method import scale_data3d


# 从2018-2023年预处理后的mat文件中读取imaging数据
def load_imaging_from_mat(file_path: str, data_type: str = 'Id_filt') -> UniformGrid:
    image = UniformGrid()
    data = sio.loadmat(file_path)
    covis = data['imaging'][0][0]
    grid = covis['grid'][0][0]
    bounds = grid['axis'][0]
    spacing = grid['spacing'][0][0]
    image.data = grid[data_type].transpose(1, 0, 2)
    image.bounds = bounds
    image.spacing = [spacing['dx'][0][0], spacing['dy'][0][0], spacing['dz'][0][0]]
    image.dim = 3
    return image


# 从2018-2023年预处理后的mat文件中读取diffuse数据
def load_diffuse_from_mat(file_path: str, diffuse_type: str = 'decorrelation intensity') -> UniformGrid:
    diffuse = UniformGrid()
    data = sio.loadmat(file_path)
    covis = data['diffuse'][0][0]
    grids = covis['grid'][0]
    for grid in grids:
        if grid[0][0]['type'][0] == diffuse_type:
            diffuse.data = grid[0][0]['v'].transpose()
            diffuse.bounds = grid[0][0]['axis'][0, 0:4]
            diffuse.spacing = [grid[0][0]['spacing'][0]['dx'][0][0][0], grid[0][0]['spacing'][0]['dy'][0][0][0]]
            diffuse.dim = 2
            break
    return diffuse


# 从2010-2015年预处理后的mat文件中读取imaging数据
def load_imaging_from_mat_old(file_path: str) -> UniformGrid:
    image = UniformGrid()
    data = sio.loadmat(file_path)
    covis = data['covis'][0][0]
    grid = covis['grid'][0][0]
    bounds = grid['axis'][0]
    spacing = grid['spacing'][0][0]
    image.data = grid['v'].transpose(1, 0, 2)
    image.bounds = bounds
    image.spacing = [spacing['dx'][0][0], spacing['dy'][0][0], spacing['dz'][0][0]]
    image.dim = 3
    return image

# 从2010-2015年预处理后的mat文件中读取doppler数据
def load_doppler_from_mat(file_path: str) -> UniformGrid:
    doppler = UniformGrid()
    data = sio.loadmat(file_path)
    covis = data['covis'][0][0]
    grid = covis['grid'][0][0][0][0]
    bounds = grid['axis'][0]
    spacing = grid['spacing'][0][0]
    spacing = [spacing[0][0][0]/2, spacing[1][0][0]/2, spacing[2][0][0]/2]
    old_size = grid['v_filt'].shape
    new_size = ((old_size[0]-1)*2+1, (old_size[1]-1)*2+1, (old_size[2]-1)*2+1)
    new_data = scale_data3d(grid['v_filt'], new_size)
    doppler.data = new_data.transpose(1, 0, 2)
    doppler.bounds = bounds
    doppler.spacing = spacing
    doppler.dim = 3
    return doppler


# 从2010-2015年预处理后的mat文件中读取diffuse数据
def load_diffuse_from_mat_old(file_path: str) -> UniformGrid:
    diffuse = UniformGrid()
    data = sio.loadmat(file_path)
    covis = data['covis'][0][0]
    grid = covis['grid'][0][0][0][0]
    bounds = grid['axis'][0]
    spacing = grid['spacing'][0][0]
    spacing = [spacing[0][0][0], spacing[1][0][0]]
    diffuse.data = grid['v'].transpose()
    diffuse.bounds = bounds
    diffuse.spacing = spacing
    diffuse.dim = 2
    return diffuse
