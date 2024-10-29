import numpy as np

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QGridLayout, QHBoxLayout, QCheckBox

from visualization.components.minimap import Minimap
from visualization.core.viewer import Viewer
from visualization.core import reader
from visualization.gui.region_select_widget import RegionSelectWidget
from visualization.gui.signal_group import signals

from common.entity import DataFrame


class VTKWidget(QWidget):
    colormap_name = 'Smoke'
    opacity = 0.0

    def __init__(self):
        super().__init__()
        layout = QGridLayout()
        self.setLayout(layout)
        layout.setContentsMargins(0, 0, 0, 0)
        box_widget = QWidget()
        box_layout = QVBoxLayout()
        box_widget.setLayout(box_layout)
        box_widget.setObjectName("boxWidget")
        box_widget.setStyleSheet('QWidget#boxWidget{background-color:#454545;}')

        # 声明组件
        self.viewer = Viewer()
        self.interactor = self.viewer.create_interactor()
        self.viewer.create_light()

        # 添加组件
        layout.addWidget(box_widget)
        box_layout.addWidget(self.interactor)


        # **************************************************
        # 右上角 选择框
        # **************************************************
        check_boxes = QWidget()
        check_boxes.setMinimumSize(100, 70)
        check_boxes.setObjectName("check_boxes")
        check_boxes.setStyleSheet("background-color:#333333;color:#bbbbbb")

        check_boxes_layout = QVBoxLayout()
        axis_check_box = QCheckBox("axis")
        axis_check_box.setStyleSheet("""QCheckBox::indicator:unchecked {
                                        background-color: #43494a;
                                        border: 1px solid #6b6b6b;
                                    }""")
        seabed_check_box = QCheckBox("seabed")
        seabed_check_box.setStyleSheet("""QCheckBox::indicator:unchecked {
                                        background-color: #43494a;
                                        border: 1px solid #6b6b6b;
                                    }""")
        diffuse_check_box = QCheckBox("diffuse flow")
        diffuse_check_box.setStyleSheet("""QCheckBox::indicator:unchecked {
                                        background-color: #43494a;
                                        border: 1px solid #6b6b6b;
                                    }""")

        axis_check_box.clicked.connect(lambda state: signals.axis_clicked.emit(state))
        seabed_check_box.clicked.connect(lambda state: signals.seabed_clicked.emit(state))
        diffuse_check_box.clicked.connect(lambda state: signals.diffuse_clicked.emit(state))

        check_boxes_layout.addWidget(axis_check_box)
        check_boxes_layout.addWidget(seabed_check_box)
        check_boxes_layout.addWidget(diffuse_check_box)

        check_boxes.setLayout(check_boxes_layout)


        # **************************************************
        # 左下角地图
        # **************************************************
        #region_select_widget = RegionSelectWidget()
        #region_select_widget.setFixedSize(300, 300)

        self.minimap = Minimap()

        layout1 = QHBoxLayout()
        layout1.addStretch(1)
        layout1.addWidget(check_boxes)

        layout2 = QHBoxLayout()
        #layout2.addWidget(region_select_widget)
        layout2.addWidget(self.minimap)
        layout2.addStretch(1)

        layout3 = QVBoxLayout()
        layout3.addLayout(layout1)
        layout3.addStretch(1)
        layout3.addLayout(layout2)

        self.interactor.setLayout(layout3)


        # --------------------------------------------------
        # global slots
        # --------------------------------------------------
        signals.load_region.connect(self.on_region_load)
        signals.load_frame.connect(self.on_frame_load)
        signals.frame_rendering.connect(self.on_frame_rendering)
        signals.bounds_changed.connect(self.on_bounds_changed)
        signals.bounds_slider_changed.connect(self.on_bounds_slider_changed)

        signals.axis_clicked.connect(self.on_axis_clicked)
        signals.seabed_clicked.connect(self.on_seabed_clicked)
        signals.diffuse_clicked.connect(self.on_diffuse_clicked)

        signals.add_region.connect(self.on_region_added)
        signals.remove_region.connect(self.on_region_removed)

        signals.volume_clicked.connect(self.on_volume_clicked)
        signals.colormap_changed.connect(self.on_colormap_changed)
        signals.opacity_changed.connect(self.on_opacity_changed)

        signals.contour_clicked.connect(self.on_contour_changed)
        signals.contour_value_changed.connect(self.on_contour_value_changed)

        signals.centerline_clicked.connect(self.on_centerline_clicked)

        signals.gradient_arrow_clicked.connect(self.on_gradient_arrow_clicked)
        signals.gradient_streamline_clicked.connect(self.on_gradient_streamline_clicked)

        signals.heat_flux_clicked.connect(self.on_heat_flux_clicked)
        signals.velocity_streamline_clicked.connect(self.on_velocity_streamline_clicked)



    # --------------------------------------------------
    # basic workflow
    # --------------------------------------------------
    # 加载新的区域数据时
    def on_region_load(self, regions: list, marks: np.ndarray):
        self.viewer.regions = regions
        self.viewer.marks = marks
        signals.region_loaded.emit(regions, marks)

    # 每一帧数据加载时
    def on_frame_load(self, frame: DataFrame, group_index: int, frame_index: int, group_size: int):
        self.group_index = group_index

        # 判断是否需要加载新的地形
        if ((self.viewer.frame.time_str == '' or 2010 <= int(self.viewer.frame.time_str[:4]) <= 2015)
            and 2018 <= int(frame.time_str[:4]) <= 2023):
            # load 2018-2023
            seabed_data = reader.read_seabed('../res/bathy/bathy-2018To2023.bin')
            self.viewer.seabed_data = seabed_data
            signals.seabed_loaded.emit(seabed_data)
        elif ((self.viewer.frame.time_str == '' or 2018 <= int(self.viewer.frame.time_str[:4]) <= 2023)
            and 2010 <= int(frame.time_str[:4]) <= 2015):
            # load 2010-2015
            seabed_data = reader.read_seabed('../res/bathy/bathy-2010To2015.bin')
            self.viewer.seabed_data = seabed_data
            signals.seabed_loaded.emit(seabed_data)
        self.viewer.frame = frame
        signals.frame_loaded.emit(frame, group_index, frame_index, group_size)

    def on_frame_rendering(self):
        #print('rendering: frame ', self.viewer.frame.time_str)
        self.viewer.set_plumes_color_function(self.colormap_name)
        self.viewer.set_plumes_opacity_function(self.opacity)
        self.repaint_frame()
        self.viewer.refresh()


    # --------------------------------------------------
    # bounds cut
    # --------------------------------------------------
    # 区域范围滑动条发生变化
    def on_bounds_slider_changed(self, bounds: list):
        self.viewer.remove_outline()
        self.viewer.draw_outline(bounds)
        self.viewer.refresh()

    # 区域范围确定被改变
    def on_bounds_changed(self, bounds: list):
        self.viewer.bounds = bounds
        self.viewer.remove_outline()
        self.repaint_all()
        self.viewer.refresh()


    # --------------------------------------------------
    # global draw
    # --------------------------------------------------
    # 点击axis，选择或取消选择时
    def on_axis_clicked(self, state: int):
        if state:
            self.viewer.draw_axis()
        else:
            self.viewer.remove_axis()
        self.viewer.refresh()

    # 点击seabed，选择或取消选择时
    def on_seabed_clicked(self, state: int):
        if state:
            self.viewer.draw_seabed()
        else:
            self.viewer.remove_seabed()
        self.viewer.refresh()

    # 点击diffuse，选择或取消选择时
    def on_diffuse_clicked(self, state: int):
        if state:
            self.viewer.draw_diffuse()
        else:
            self.viewer.remove_diffuse()
        self.viewer.refresh()


    # --------------------------------------------------
    # region selection
    # --------------------------------------------------
    # 选择区域
    def on_region_added(self, region_id: int):
        self.viewer.add_selected_region(region_id)
        self.centerline_graph_repaint()
        self.viewer.refresh()
        #print('add', region_id)

    # 取消选择区域
    def on_region_removed(self, region_id: int):
        self.viewer.remove_selected_region(region_id)
        #signals.remove_centerline_graph.emit(region_id)
        self.centerline_graph_repaint()
        self.viewer.refresh()
        #print('remove', region_id)


    # --------------------------------------------------
    # direct volume rendering
    # --------------------------------------------------
    # 直接体渲染show按钮选择或取消选择时
    def on_volume_clicked(self, state: int):
        if state:
            self.viewer.volume_selected()
        else:
            self.viewer.volume_unselected()
        self.viewer.refresh()

    # 直接体渲染更改colormap时
    def on_colormap_changed(self, colormap_name: str):
        self.colormap_name = colormap_name
        self.viewer.set_plumes_color_function(colormap_name)
        if self.viewer.volume_selected_flag:
            self.viewer.volume_unselected()
            self.viewer.volume_selected()
            self.viewer.refresh()

    # 直接体渲染更改透明度时
    def on_opacity_changed(self, opacity: float):
        self.opacity = opacity
        self.viewer.set_plumes_opacity_function(opacity)
        if self.viewer.volume_selected_flag:
            self.viewer.volume_unselected()
            self.viewer.volume_selected()
            self.viewer.refresh()


    # --------------------------------------------------
    # iso-surface rendering
    # --------------------------------------------------
    def on_contour_changed(self, state: int):
        if state:
            self.viewer.contour_selected()
        else:
            self.viewer.contour_unselected()
        self.viewer.refresh()

    def on_contour_value_changed(self, values):
        if self.viewer.contour_selected_flag:
            self.viewer.contour_unselected()
        self.viewer.contour_value_changed(values)
        self.viewer.contour_selected()
        self.viewer.refresh()


    # --------------------------------------------------
    # centerline
    # --------------------------------------------------
    def on_centerline_clicked(self, state: int):
        if state:
            self.viewer.centerline_selected()
        else:
            self.viewer.centerline_unselected()
        self.centerline_graph_repaint()
        self.viewer.refresh()

    def centerline_graph_repaint(self):
        signals.remove_all_centerline_graph.emit()
        if self.viewer.centerline_selected_flag:
            for region_id in self.viewer.selected_regions:
                strid = str(region_id)
                signals.add_centerline_graph.emit(region_id, self.viewer.centerline_points[strid], self.viewer.centerline_curvatures[strid])



    # --------------------------------------------------
    # gradient
    # --------------------------------------------------
    def on_gradient_arrow_clicked(self, state: int):
        if state:
            self.viewer.gradient_arrow_selected()
        else:
            self.viewer.gradient_arrow_unselected()
        self.viewer.refresh()

    def on_gradient_streamline_clicked(self, state: int):
        if state:
            self.viewer.gradient_streamline_selected()
        else:
            self.viewer.gradient_streamline_unselected()
        self.viewer.refresh()


    # --------------------------------------------------
    # doppler
    # --------------------------------------------------
    def on_heat_flux_clicked(self, state: int):
        if state:
            self.viewer.heat_flux_selected()
        else:
            self.viewer.heat_flux_unselected()
        self.viewer.refresh()

    def on_velocity_streamline_clicked(self, state: int):
        if state:
            self.viewer.velocity_streamline_selected()
        else:
            self.viewer.velocity_streamline_unselected()
        self.viewer.refresh()


    # --------------------------------------------------
    # repaint
    # --------------------------------------------------
    def repaint_frame(self):
        if self.viewer.diffuse_selected_flag:
            self.viewer.remove_diffuse()
            self.viewer.draw_diffuse()
        if self.viewer.volume_selected_flag:
            self.viewer.volume_unselected()
            self.viewer.volume_selected()
        if self.viewer.contour_selected_flag:
            self.viewer.contour_unselected()
            self.viewer.contour_selected()
        if self.viewer.centerline_selected_flag:
            self.viewer.centerline_unselected()
            self.viewer.centerline_selected()
            self.centerline_graph_repaint()
        if self.viewer.gradient_arrow_selected_flag:
            self.viewer.gradient_arrow_unselected()
            self.viewer.gradient_arrow_selected()
        if self.viewer.gradient_streamline_selected_flag:
            self.viewer.gradient_streamline_unselected()
            self.viewer.gradient_streamline_selected()
        if self.viewer.heat_flux_selected_flag:
            self.viewer.heat_flux_unselected()
            self.viewer.heat_flux_selected()
        if self.viewer.velocity_streamline_selected_flag:
            self.viewer.velocity_streamline_unselected()
            self.viewer.velocity_streamline_selected()


    def repaint_all(self):
        if self.viewer.axis_selected_flag:
            self.viewer.remove_axis()
            self.viewer.draw_axis()
        if self.viewer.seabed_selected_flag:
            self.viewer.remove_seabed()
            self.viewer.draw_seabed()

        self.repaint_frame()


    def closeEvent(self, a0):
        super().closeEvent(a0)
        self.interactor.Finalize()
        self.minimap.close()

