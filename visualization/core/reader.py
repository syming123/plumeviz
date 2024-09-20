# ============================================================
# 从预处理后的文件中读取数据
# ============================================================

import joblib
import json

from common.entity import DataFrame, UniformGrid


def read_index(file_path: str):
    with open(file_path, 'rb') as file:
        index_file = joblib.load(file)
        frame_files = index_file['frame_files']
        region_file = index_file['region_file']
        return frame_files, region_file


def read_frame(file_path: str) -> DataFrame:
    with open(file_path, 'rb') as file:
        data_file = joblib.load(file)
        return data_file


def read_regions(file_path: str):
    with open(file_path, 'rb') as file:
        regions_file = joblib.load(file)
        regions = regions_file['regions']
        marks = regions_file['marks']
        return regions, marks

def read_seabed(file_path: str) -> UniformGrid:
    with open(file_path, 'rb') as file:
        fdata = joblib.load(file)
        grid = UniformGrid()
        grid.data = fdata['data']
        grid.bounds = fdata['bounds']
        grid.spacing = fdata['spacing']
        grid.dim = 2
        return grid


# colormap
class ColorMap:
    def __init__(self, colors):
        self.colors = colors

    def get_color(self, value):
        return self.colors[int(value * (len(self.colors) - 1))]


def load_colormap(filepath):
    with open(filepath, 'r', encoding='utf-8') as file:
        json_str = file.read()
    json_data = json.loads(json_str)
    colors = []
    for color in json_data['ColorMap']:
        colors.append((color[0] / 255, color[1] / 255, color[2] / 255))
    color_map = ColorMap(colors)
    return color_map
