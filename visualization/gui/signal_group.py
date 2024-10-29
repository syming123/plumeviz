import numpy as np
from PyQt6.QtCore import pyqtSignal, QObject

from common.entity import DataFrame, UniformGrid


class SignalGroup(QObject):
    # --------------------------------------------------
    # 加载region
    # params: regions: list, marks: np.ndarray
    # --------------------------------------------------
    # 读取region文件后触发
    load_region = pyqtSignal(list, np.ndarray)
    # 将region数据保存至viewer后触发
    region_loaded = pyqtSignal(list, np.ndarray)


    # --------------------------------------------------
    # 加载完成seabed数据后触发
    # params: seabed: UniformGrid
    # --------------------------------------------------
    seabed_loaded = pyqtSignal(UniformGrid)


    # --------------------------------------------------
    # 加载frame
    # params: frame: DataFrame, group_index: int, frame_index: int, group_size: int
    # --------------------------------------------------
    # 选择一个数据帧文件并加载后触发
    load_frame = pyqtSignal(DataFrame, int, int, int)
    # 将frame数据保存至viewer后触发
    frame_loaded = pyqtSignal(DataFrame, int, int, int)


    # --------------------------------------------------
    # 开始对frame的渲染
    # params: None
    # --------------------------------------------------
    frame_rendering = pyqtSignal()


    # --------------------------------------------------
    # 更改所选择的数据帧时触发，用于交互选择数据帧或顺序播放
    # params: group_index: int, frame_index: int
    # --------------------------------------------------
    pick_changed = pyqtSignal(int, int)


    # --------------------------------------------------
    # 区域裁剪
    # param: bounds: list
    # [min_x, max_x, min_y, max_y, min_z, max_z]
    # --------------------------------------------------
    # 确认裁剪边界更改时触发
    bounds_changed = pyqtSignal(list)
    # 裁剪滑块被拖动时触发
    bounds_slider_changed = pyqtSignal(list)


    # --------------------------------------------------
    # 点击axis, seabed, diffuse的选择框，选取或取消选取
    # param: state: int
    # --------------------------------------------------
    axis_clicked = pyqtSignal(int)
    seabed_clicked = pyqtSignal(int)
    diffuse_clicked = pyqtSignal(int)


    # --------------------------------------------------
    # 选择，取消选择region
    # params: region_id: int
    # --------------------------------------------------
    add_region = pyqtSignal(int)
    remove_region = pyqtSignal(int)


    # --------------------------------------------------
    # 主视角发生旋转
    # params: angle: float
    # --------------------------------------------------
    camera_rotated = pyqtSignal(float)


    # --------------------------------------------------
    # 羽流直接体渲染
    # param: state: int
    # param: colormap_name: str
    # param: opacity: float
    # --------------------------------------------------
    volume_clicked = pyqtSignal(int)
    colormap_changed = pyqtSignal(str)
    opacity_changed = pyqtSignal(float)

    # --------------------------------------------------
    # 羽流等值面提取
    # param: state: int
    # param: values: list
    # --------------------------------------------------
    contour_clicked = pyqtSignal(int)    # 1:draw, 0:reset
    contour_value_changed = pyqtSignal(list)

    # --------------------------------------------------
    # 羽流中心线绘制
    # param: state: int
    # --------------------------------------------------
    centerline_clicked = pyqtSignal(int)

    # --------------------------------------------------
    # 中心线图表绘制
    # param: region_id: int, points: list, k: list
    # param: region_id
    # --------------------------------------------------
    add_centerline_graph = pyqtSignal(int, list, list)
    remove_all_centerline_graph = pyqtSignal()

    # --------------------------------------------------
    # 羽流梯度特征绘制
    # param: state: int
    # --------------------------------------------------
    gradient_arrow_clicked = pyqtSignal(int)
    gradient_streamline_clicked = pyqtSignal(int)

    # --------------------------------------------------
    # doppler特征绘制
    # param: state: int
    # --------------------------------------------------
    heat_flux_clicked = pyqtSignal(int)
    velocity_streamline_clicked = pyqtSignal(int)

# ==================================================
# 全局信号变量
# ==================================================
signals = SignalGroup()
