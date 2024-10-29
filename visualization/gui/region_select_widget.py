from platform import processor

import matplotlib
import numpy as np
from PIL import Image
from scipy.ndimage import zoom
import time

from common.entity import DataFrame

matplotlib.use('QtAgg')  # 使用 QtAgg 后端
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from PyQt6.QtWidgets import QWidget, QVBoxLayout

from common.entity import UniformGrid
from visualization.core import processor
from visualization.gui.signal_group import signals

from visualization.components.minimap import Minimap


class RegionSelectWidget(QWidget):
    # Data
    regions = []
    marks = []
    frame_marks = []
    bounds = []
    seabed = UniformGrid()
    frame = DataFrame()
    frame_index = -1
    region_selected = []

    max_count_region_id = -1

    def __init__(self):
        super(RegionSelectWidget, self).__init__()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        self.canvas = MplCanvas()

        canvas_box = QWidget()
        canvas_box_layout = QVBoxLayout()
        # canvas_box.setFixedHeight(300)
        canvas_box_layout.setContentsMargins(0, 0, 0, 0)
        canvas_box_layout.addWidget(self.canvas)
        canvas_box.setLayout(canvas_box_layout)

        #layout.addWidget(canvas_box)

        #mp = Minimap()
        #layout.addWidget(mp)

        # 生成示例数组
        self.array = np.zeros((100, 100), dtype=int)
        self.contour = None
        self.region_num = 0
        self.region_id_list = []
        self.color_region_dict = {}

        # 自定义颜色映射
        # self.static_color_map_list = ['white', 'gray', 'gray', 'gray']
        self.temp_color_list = ['mintcream']
        self.cmap = ListedColormap(self.temp_color_list)

        # global slots
        #signals.region_loaded.connect(self.on_region_loaded)
        #signals.seabed_loaded.connect(self.on_seabed_loaded)
        #signals.bounds_changed.connect(self.on_bounds_changed)
        #signals.frame_loaded.connect(self.on_frame_loaded)
        #signals.frame_rendering.connect(self.on_frame_rendering)

    # ========================================
    # slots functions
    # ========================================
    def on_region_loaded(self, regions: list, marks: np.ndarray):
        self.regions = regions
        self.marks = marks

    def on_seabed_loaded(self, seabed: UniformGrid):
        self.seabed = seabed

    def on_bounds_changed(self, bounds):
        self.bounds = bounds
        self.on_frame_rendering()

    def on_frame_loaded(self, frame: DataFrame, group_index: int, frame_index: int, group_size: int):
        self.frame = frame
        self.frame_index = frame_index

    def on_frame_rendering(self):
        # print(time.time())
        self.preprocess()
        # print(time.time())
        self.load_regions()
        # print(time.time())


    def preprocess(self):
        marks_grid = self.frame.imaging.copy()
        marks_grid.data = self.marks[self.frame_index]
        self.frame_marks = processor.cut_uniform(marks_grid, self.bounds).data
        #self.seabed = processor.cut_uniform(self.seabed, self.bounds)


    # --------------------------------------------------------------------------------


    def get_region_array(self):
        #print(time.time())
        #sz = self.frame_marks.shape
        #M = np.zeros((sz[0], sz[1]), np.int32)
        M = np.amax(self.frame_marks, axis=2)
        # for i in range(sz[0]):
        #     for j in range(sz[1]):
        #         t = self.frame_marks[i, j, :]
        #         for region in self.frame_regions:
        #             if region.id in t:
        #                 M[i][j] = int(region.id)
        #                 break
        #print(time.time())
        return M


    def on_click(self, event):
        # if event.dblclick
        if event.inaxes is not None:  # and event.dblclick:
            x, y = int(event.ydata), int(event.xdata)
            for region_id, color_region in self.color_region_dict.items():
                if color_region.is_within_range(x, y):
                    if color_region.is_chosen:
                        self.temp_color_list[region_id] = 'gray'
                        self.color_region_dict[region_id].is_chosen = False
                        signals.remove_region.emit(region_id)
                        self.region_selected.remove(region_id)
                        #print('unselect region: ', region_id)
                    else:
                        self.temp_color_list[region_id] = 'orange'
                        self.color_region_dict[region_id].is_chosen = True
                        signals.add_region.emit(region_id)
                        self.region_selected.append(region_id)
                        #print('select region: ', region_id)
                    self.draw()
                    return

    def init_color_region_dict(self):
        h, w = self.array.shape
        for i in range(h):
            for j in range(w):
                v = self.array[i][j]
                if v > 0:
                    self.add_to_dict(v, (i, j))
        for region_id, color_region in self.color_region_dict.items():
            self.region_id_list.append(region_id)
            color_region.index_list.sort()
            # 初始化最小值和最大值
            min_x = min_y = float('inf')
            max_x = max_y = float('-inf')

            # 遍历元组列表
            for x, y in color_region.index_list:
                if x < min_x:
                    min_x = x
                if y < min_y:
                    min_y = y
                if x > max_x:
                    max_x = x
                if y > max_y:
                    max_y = y
            color_region.boundary_box = [(min_x, min_y), (max_x, max_y)]
        self.region_id_list.sort()
        for i in range(1, self.region_id_list[-1] + 1):
            if i in self.region_id_list:
                self.temp_color_list.append("gray")
            else:
                self.temp_color_list.append("white")

        # 默认选择区域面积最大的
        # max_count = 0
        # max_count_id = -1
        # for region in self.regions:
        #     if region.id in self.region_id_list and region.count > max_count:
        #         max_count_id = region.id
        #         max_count = region.count
        #
        # self.temp_color_list[max_count_id] = 'orange'
        # self.color_region_dict[max_count_id].is_chosen = True
        # self.max_count_region_id = max_count_id
        # config.signals.region_picked.emit(max_count_id)

    def add_to_dict(self, key, value):
        if key in self.color_region_dict:
            self.color_region_dict[key].index_list.append(value)  # 如果键存在，向列表中添加新元素
        else:
            self.region_num += 1
            color_region = ColorRegion()
            color_region.mark = self.region_num
            color_region.index_list = [value]
            self.color_region_dict[key] = color_region  # 如果键不存在，创建新的键值对

    def draw(self):
        plt.figure(figsize=(8, 8))
        plt.axis("off")

        plt.contour(self.contour, levels=30, cmap='viridis')
        # 保存最终的图像，只包含绘制信息
        cache_image_path = "../data/image/cache.png"
        plt.savefig(cache_image_path, bbox_inches='tight', pad_inches=0, transparent=True)
        plt.close()

        self.canvas.ax.clear()
        self.canvas.ax.axis("off")
        w, h = self.array.shape
        gradient_image = Image.open("../res/background/gradient.png")
        plt.imshow(gradient_image)
        self.canvas.ax.imshow(gradient_image, extent=[0, h, 0, w])
        cache_image = Image.open(cache_image_path)
        self.canvas.ax.imshow(cache_image, extent=[0, h, 0, w])

        self.cmap = ListedColormap(self.temp_color_list)
        self.canvas.ax.imshow(self.array, cmap=self.cmap, interpolation='nearest')
        self.canvas.fig.canvas.mpl_connect('button_press_event', self.on_click)

        # 添加带透明背景的小尺寸 PNG 图片
        locate_0_path = "../res/icons/locate0.png"
        locate_0 = Image.open(locate_0_path)
        locate_1_path = "../res/icons/locate1.png"
        locate_1 = Image.open(locate_1_path)

        for key, region in self.color_region_dict.items():
            index_list = region.index_list
            index = int(len(index_list) / 2)
            x, y = index_list[index]
            if region.is_chosen:
                self.canvas.ax.imshow(locate_1, extent=[y - 16, y + 16, x - 2, x + 30])
            else:
                self.canvas.ax.imshow(locate_0, extent=[y - 16, y + 16, x - 2, x + 30])
        self.canvas.ax.imshow(cache_image, extent=[0, h, 0, w], alpha=0.0)

        self.canvas.draw()

    def load_regions(self):
        # 加载并处理区域数据
        origin_data = zoom(self.get_region_array(), (2, 2), order=0)
        self.array = np.flip(origin_data, axis=1)
        # 加载并处理等高线数据
        #contour_small_size = config.dataset.bathy.data.copy()
        contour_small_size = processor.cut_uniform(self.seabed, self.bounds).data
        image = Image.fromarray(contour_small_size)
        # 指定新的尺寸
        new_size = self.array.shape  # 将图像放大到与array同尺寸
        # 使用 PIL 的 resize 方法将图像放大到指定尺寸
        resized_image = image.resize(new_size, Image.Resampling.LANCZOS)
        # 如果你想将 PIL 图像转换回 numpy 数组
        contour = np.array(resized_image).astype(np.int32)
        # np.savetxt("rD:\Desktop\DIY\contour_xxx.txt", contour, fmt="%.2f")
        # contour_min = np.min(contour)
        # contour_max = np.max(contour)
        # self.distance = contour_max - contour_min
        contour = contour + abs(np.min(contour))
        contour = np.flip(contour, axis=1)
        # contour = np.rot90(contour, k=3)
        self.contour = contour

        self.region_num = 0
        self.region_id_list = []
        self.temp_color_list = [[0, 0, 0, 0]]
        self.color_region_dict = {}
        self.init_color_region_dict()

        for region_id in self.region_selected:
            self.temp_color_list[region_id] = 'orange'
            self.color_region_dict[region_id].is_chosen = True

        self.draw()


class MplCanvas(FigureCanvas):

    def __init__(self, parent=None):
        self.fig, self.ax = plt.subplots()
        self.ax.axis('off')  # 禁用坐标轴
        super(MplCanvas, self).__init__(self.fig)
        self.parent = parent
        self.fig.tight_layout()
        self.fig.patch.set_facecolor('#454545')  # 设置背景颜色为浅灰色


class ColorRegion:
    def __init__(self):
        self.mark = 0
        self.is_chosen = False
        self.index_list = []
        self.boundary_box = []

    def is_within_range(self, x, y):
        # x1, y1 = self.boundary_box[0]
        # x2, y2 = self.boundary_box[1]
        # return x1 <= x <= x2 and y1 <= y <= y2
        return (x, y) in self.index_list
