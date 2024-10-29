import math
import os
import numpy as np
from PyQt6 import QtCore
from PyQt6.QtCharts import QChart, QChartView, QSplineSeries, QValueAxis
from PyQt6.QtCore import QPointF, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QIcon, QPainter
from PyQt6.QtWidgets import QScrollArea, QVBoxLayout, QGraphicsDropShadowEffect, QWidget, QHBoxLayout, QPushButton, \
    QSpacerItem, QSizePolicy, QLabel, QComboBox, QSlider, QCheckBox, QLineEdit, QFileDialog, QTreeWidgetItem, \
    QTreeWidget

from visualization.core import reader, processor
from visualization.gui.signal_group import signals
from common.entity import DataFrame


class FeatureWidget(QScrollArea):
    def __init__(self):
        super().__init__()
        self.setWidgetResizable(True)
        widget = QWidget()
        self.setWidget(widget)
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.setSpacing(0)
        widget.setLayout(layout)
        # self.setStyleSheet("QScrollBar:vertical { border: 2px solid gray; background: lightgray; width: 10px; }")
        self.setStyleSheet("QScrollBar:vertical { border: 2px solid #333333; background: #454545}"
                           "QScrollBar::handle:vertical { background: #454545; }"
                           "QScrollBar::add-line:vertical { background: #333333; }"
                           "QScrollBar::sub-line:vertical { background: #333333; }")
        # declare children item
        item0 = DataWidget()
        item1 = VolumeWidget()
        item2 = CenterLineWidget()
        item3 = ContourWidget()
        item4 = GradientWidget()

        # add children item
        layout.addWidget(item0)
        layout.addWidget(item1)
        layout.addWidget(item2)
        layout.addWidget(item3)
        layout.addWidget(item4)


def add_shadow(widget, r=10, c=25):
    # 添加阴影
    effect_shadow = QGraphicsDropShadowEffect()
    effect_shadow.setOffset(0, 0)  # 偏移
    effect_shadow.setBlurRadius(r)  # 阴影半径
    effect_shadow.setColor(QColor(c, c, c))  # 阴影颜色
    widget.setGraphicsEffect(effect_shadow)


class FeatureItem(QWidget):
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.setStyleSheet("background-color:#454545;color:#bbbbbb")
        self.setLayout(layout)
        self.fixed_height = 50
        self.setFixedHeight(50)
        self.isShow = False

        box_widget = QWidget()
        self.box_layout = QVBoxLayout()
        self.box_layout.setContentsMargins(5, 5, 5, 5)
        box_widget.setLayout(self.box_layout)
        layout.addWidget(box_widget)

        # declare children component
        # 标题 展开/收回
        title_widget = QWidget()
        title_widget.setFixedHeight(40)
        title_layout = QHBoxLayout()
        # title_layout.setContentsMargins(5, 5, 5, 5)
        title_widget.setLayout(title_layout)
        # title_widget.setStyleSheet("border-radius:3px 3px")

        add_shadow(title_widget)

        self.label_title = QLabel('Title:')
        self.label_title.setFont(QFont('Arial', 10))
        self.label_title.setStyleSheet('color: #bbbbbb;')
        title_layout.addWidget(self.label_title)

        spacer = QSpacerItem(0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        title_layout.addItem(spacer)

        self.btn_show = QPushButton()
        self.btn_show.setIcon(QIcon('../res/icons/fold.png'))
        self.btn_show.setIconSize(QSize(20, 20))
        self.btn_show.setStyleSheet("background-color:#454545;border:0px")
        title_layout.addWidget(self.btn_show)

        # 内容
        self.show_widget = QWidget()
        self.show_widget.close()

        self.box_layout.addWidget(title_widget)

        # 绑定
        self.btn_show.clicked.connect(self.buttonClicked)

    def buttonClicked(self):
        if not self.isShow:
            self.setFixedHeight(self.fixed_height)
            self.isShow = True
            self.btn_show.setIcon(QIcon('../res/icons/unfold.png'))
            self.btn_show.setIconSize(QSize(20, 20))
            self.box_layout.addWidget(self.show_widget)
            self.show_widget.show()
        else:
            self.setFixedHeight(50)
            self.isShow = False
            self.btn_show.setIcon(QIcon('../res/icons/fold.png'))
            self.btn_show.setIconSize(QSize(20, 20))
            self.box_layout.removeWidget(self.show_widget)
            self.show_widget.close()


class VolumeWidget(FeatureItem):
    def __init__(self):
        super().__init__()
        self.fixed_height = 180
        self.label_title.setText('Plume Volume Rendering')
        layout = QVBoxLayout()
        self.show_widget.setLayout(layout)

        # button
        show_btn = QCheckBox('show')
        show_btn.clicked.connect(self.show_clicked)

        # color_combo
        color_combo_widget = QWidget()
        color_combo_widget_layout = QHBoxLayout()
        color_combo_widget.setLayout(color_combo_widget_layout)
        color_combo_widget_layout.setContentsMargins(0, 0, 0, 0)
        color_combo_widget_layout.setSpacing(0)
        color_label = QLabel("Color Map:")
        color_label.setFixedWidth(80)

        self.color_combo = QComboBox()
        self.color_combo.setStyleSheet("""
                                        QComboBox {
                                            border: 1px solid #646464;
                                            border-radius: 3px;
                                        }
                                      """)

        self.color_combo.addItem('default')
        colormaps = os.listdir('../res/colormap')
        for cmap in colormaps:
            cmap0 = os.path.splitext(cmap)[0]
            self.color_combo.addItem(cmap0)
        self.color_combo.currentIndexChanged.connect(self.colormap_changed)

        color_combo_widget_layout.addWidget(color_label)
        color_combo_widget_layout.addWidget(self.color_combo)

        # opacity
        opacity_slider_widget = QWidget()
        opacity_slider_widget_layout = QHBoxLayout()
        opacity_slider_widget_layout.setContentsMargins(0, 0, 0, 0)
        opacity_slider_widget.setLayout(opacity_slider_widget_layout)
        opacity_label = QLabel("Opacity Slider:")

        self.opacity_slider = QSlider()
        self.opacity_slider.setOrientation(Qt.Orientation.Horizontal)
        self.opacity_slider.setMaximum(100)
        self.opacity_slider.valueChanged.connect(self.opacity_changed)

        opacity_slider_widget_layout.addWidget(opacity_label)
        opacity_slider_widget_layout.addWidget(self.opacity_slider)

        # add widget
        layout.addWidget(show_btn)
        layout.addWidget(color_combo_widget)
        layout.addWidget(opacity_slider_widget)

    def colormap_changed(self, param):
        colormap_name = self.color_combo.currentText()
        signals.colormap_changed.emit(colormap_name)

    def opacity_changed(self, param):
        opacity = param / 100
        signals.opacity_changed.emit(opacity)

    def show_clicked(self, state):
        signals.volume_clicked.emit(state)


class CenterLineWidget(FeatureItem):
    selected_centerline = []

    def __init__(self):
        super().__init__()
        self.fixed_height = 300
        self.label_title.setText('Centerline')
        self.show_widget_layout = QVBoxLayout()
        self.show_widget_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.show_widget_layout.setContentsMargins(0, 0, 0, 0)
        self.show_widget.setLayout(self.show_widget_layout)

        show_check = QCheckBox()
        show_check.setText('Show center line')
        show_check.clicked.connect(lambda state: signals.centerline_clicked.emit(state))
        show_check.setObjectName("checkBox")
        show_check.setStyleSheet("""
                                    QCheckBox{
                                        background-color:#333333;padding:0px 3px;height:20px;
                                    }
                                    QCheckBox::indicator:unchecked {
                                        background-color: #43494a;
                                        border: 1px solid #6b6b6b;
                                    }
                                """)
        self.show_widget_layout.addWidget(show_check)

        label = QLabel("No Region Selected")
        label.setStyleSheet("font-size:20px")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label_widget = QWidget()
        self.label_widget.setFixedHeight(230)
        self.label_widget.setObjectName("labelWidget")
        self.label_widget.setStyleSheet("background:#333333")

        label_layout = QVBoxLayout()
        label_layout.addWidget(label)
        label_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.label_widget.setLayout(label_layout)
        self.show_widget_layout.addWidget(self.label_widget)

        self.data_dict = {}

        # config.signals.region_detected.connect(self.renew)
        # config.signals.add_centerline_curvature.connect(self.add_curvature)
        # config.signals.remove_centerline_curvature.connect(self.remove_curvature)

        # global slots
        signals.add_centerline_graph.connect(self.on_centerline_add)
        signals.remove_all_centerline_graph.connect(self.on_centerline_remove)



    def on_centerline_add(self, region_id: int, points: list, K: list):
        self.add_curvature([region_id, points, K])
        self.selected_centerline.append(region_id)

    def on_centerline_remove(self):
        self.selected_centerline = []
        self.clear_draw()



    def add_curvature(self, param):

        chart_view = self.show_widget.findChild(QChartView, "chartView")
        if chart_view:
            chart_view.setParent(None)
            chart_view.deleteLater()
        self.label_widget.close()
        region_id = param[0]
        points = param[1]  # x
        k = param[2]  # y
        if region_id in self.data_dict.keys():
            return

        data = []
        for i in range(len(points)):
            x = points[i][2]
            y = k[i]
            data.append((x, y))
        self.data_dict[region_id] = data
        print(len(self.data_dict.keys()))
        self.draw()

    def remove_curvature(self, param):
        region_id = param
        # 移除此区域对应的曲线
        self.data_dict.pop(region_id)
        if len(self.data_dict.items()) == 0:
            self.clear_draw()
        else:
            self.draw()

    def draw(self):

        old_chart_view = self.show_widget.findChild(QChartView, "chartView")
        if old_chart_view:
            old_chart_view.setParent(None)
            old_chart_view.deleteLater()

        chart = QChart()
        chart.setTitle('Curvature Variation with Height')
        font_chart_title = QFont()
        font_chart_title.setPointSize(12)
        chart.setTitleFont(font_chart_title)
        # 创建X轴和Y轴
        axis_x = QValueAxis()
        axis_y = QValueAxis()
        axis_x.setTitleText('Height')
        axis_y.setTitleText('Curvature')
        chart.setTitleBrush(QColor("#bbbbbb"))  # 设置标题颜色为白色
        chart.setBackgroundBrush(QColor("#333333"))  # 设置背景颜色为黑色

        # 设置坐标轴数值的字体大小
        font_title = QFont()
        font_title.setPointSize(10)  # 设置字体大小为10
        axis_x.setTitleFont(font_title)
        axis_y.setTitleFont(font_title)
        axis_x.setTitleBrush(QColor("#bbbbbb"))  # 设置X轴标题颜色为白色
        axis_y.setTitleBrush(QColor("#bbbbbb"))  # 设置Y轴标题颜色为白色
        font_label = QFont()
        font_label.setPointSize(7)  # 设置字体大小为7
        axis_x.setLabelsFont(font_label)
        axis_y.setLabelsFont(font_label)
        axis_x.setLabelsBrush(QColor("#bbbbbb"))  # 设置X轴标签颜色为白色
        axis_y.setLabelsBrush(QColor("#bbbbbb"))  # 设置Y轴标签颜色为白色

        # 将轴添加到图表
        chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
        chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)

        # 存储所有系列的数据点
        all_points_x = []
        all_points_y = []
        for key, data in self.data_dict.items():
            series = QSplineSeries()
            series.setName("Region {}".format(key))
            for point in data:
                series.append(QPointF(point[0], point[1]))
                all_points_x.append(point[0])
                all_points_y.append(point[1])
            chart.addSeries(series)

        if all_points_x and all_points_y:
            x_min = min(all_points_x)
            x_max = max(all_points_x)
            y_min = min(all_points_y)
            y_max = max(all_points_y)

            axis_x.setRange(x_min, x_max)
            axis_y.setRange(y_min, y_max)

        # chart.createDefaultAxes()

        # 将每个系列附加到轴
        for series in chart.series():
            series.attachAxis(axis_x)
            series.attachAxis(axis_y)

        # 去除图表的背景和边框
        # chart.setBackgroundVisible(False)
        chart.setMargins(QtCore.QMargins(0, 0, 0, 0))

        # 设置图例
        legend = chart.legend()
        legend.setVisible(True)  # 设置图例可见性
        # legend.setAlignment(Qt.AlignmentFlag.AlignBottom)  # 设置图例位置

        # 设置图例的字体
        legend_font = QFont()
        legend_font.setPointSize(8)  # 设置图例字体大小为10
        legend.setFont(legend_font)
        legend.setLabelColor(QColor("#bbbbbb"))
        # 创建一个图表视图 (QChartView) 并设置图表
        chart_view = QChartView(chart, self)
        chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        chart_view.setObjectName("chartView")
        chart_view.setStyleSheet("background:#333333;border-radius: 3px;")

        self.show_widget_layout.addWidget(chart_view)
        # add_shadow(chart_view)

    def clear_draw(self):
        chart_view = self.show_widget.findChild(QChartView, "chartView")
        if chart_view:
            chart_view.setParent(None)
            chart_view.deleteLater()
        self.data_dict.clear()
        self.label_widget.show()



class ContourWidget(FeatureItem):
    def __init__(self):
        super().__init__()
        self.exponent = 0
        self.true_value = 1
        self.fixed_height = 330
        self.label_title.setText('Contour')
        self.setMinimumHeight(50)
        self.slider_value = 1

        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.setContentsMargins(0, 0, 0, 0)
        self.show_widget.setLayout(layout)

        # 滑动条 添加数值
        slider_widget = QWidget()
        slider_widget.setFixedHeight(40)
        slider_widget_layout = QHBoxLayout()
        slider_widget_layout.setSpacing(10)
        slider_widget_layout.setContentsMargins(0, 0, 0, 0)

        # 滑动条
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setMinimum(0)
        self.slider.setMaximum(5)
        self.slider.setSingleStep(1)
        self.slider.setValue(self.slider_value)

        self.text_right = QLabel()
        self.text_right.setText(str(self.slider_value))
        self.text_right.setFixedSize(80, 20)
        self.text_right.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.text_right.setStyleSheet("""
                            QLabel {
                                border: 1px solid #646464;
                                background: #43494a;
                            }
                        """)
        slider_btn = QPushButton("Add")
        slider_btn.setStyleSheet("width:50px;height:18px;"
                                 "font-size:12px;background-color: #4c5052;"
                                 "border-radius: 3px;border: 1px solid #5e6060")
        slider_btn.clicked.connect(self.slider_btn_clicked)

        slider_widget_layout.addWidget(self.slider)
        slider_widget_layout.addWidget(self.text_right)
        slider_widget_layout.addWidget(slider_btn)
        slider_widget.setLayout(slider_widget_layout)

        # 整个组件Widget
        table_widget = QWidget()
        table_widget_layout = QHBoxLayout()
        table_widget_layout.setContentsMargins(0, 0, 0, 0)
        table_widget.setLayout(table_widget_layout)

        # 左侧文本行
        self.line_edit_widget = QWidget()
        self.line_edit_widget.setStyleSheet("background:#333333")
        self.line_edit_widget.setMinimumHeight(240)
        self.line_edit_widget_layout = QVBoxLayout()
        self.line_edit_widget_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.line_edit_widget_layout.setContentsMargins(3, 3, 3, 3)
        self.line_edit_widget_layout.setSpacing(2)
        self.line_edit_widget.setLayout(self.line_edit_widget_layout)

        # 右侧操作按钮
        operator_widget = QWidget()
        operator_widget_layout = QVBoxLayout()
        operator_widget.setLayout(operator_widget_layout)
        operator_widget.setFixedWidth(45)
        operator_widget_layout.setContentsMargins(0, 0, 0, 0)
        operator_widget_layout.setAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignTop)

        add_btn = QPushButton()
        add_btn.setIcon(QIcon('../res/icons/increase.png'))
        add_btn.setIconSize(QSize(23, 23))
        add_btn.setFixedSize(35, 35)
        add_btn.setStyleSheet("background:#454545;border-radius:3px 3px")

        remove_btn = QPushButton()
        remove_btn.setIcon(QIcon('../res/icons/decrease.png'))
        remove_btn.setIconSize(QSize(23, 23))
        remove_btn.setFixedSize(35, 35)
        remove_btn.setStyleSheet("background:#454545;border-radius:3px 3px")

        clear_btn = QPushButton()
        clear_btn.setIcon(QIcon('../res/icons/clear.png'))
        clear_btn.setIconSize(QSize(27, 27))
        clear_btn.setFixedSize(35, 35)
        clear_btn.setStyleSheet("background:#454545;border-radius:3px 3px")

        apply_btn = QPushButton()
        apply_btn.setIcon(QIcon('../res/icons/apply.png'))
        apply_btn.setIconSize(QSize(25, 25))
        apply_btn.setFixedSize(35, 35)
        apply_btn.setStyleSheet("background:#454545;border-radius:3px 3px")

        add_shadow(add_btn, 10, 45)
        add_shadow(remove_btn, 10, 45)
        add_shadow(clear_btn, 10, 45)
        add_shadow(apply_btn, 10, 45)

        operator_widget_layout.addWidget(add_btn)
        operator_widget_layout.addWidget(remove_btn)
        operator_widget_layout.addWidget(clear_btn)
        operator_widget_layout.addWidget(apply_btn)

        # 事件绑定
        add_btn.clicked.connect(self.add_line_edit)
        remove_btn.clicked.connect(self.remove_line_edit)
        clear_btn.clicked.connect(self.clear_line_edit)
        apply_btn.clicked.connect(self.apply)

        # 组件组合
        table_widget_layout.addWidget(self.line_edit_widget)
        table_widget_layout.addWidget(operator_widget)

        layout.addWidget(slider_widget)
        layout.addWidget(table_widget)

        self.slider.valueChanged.connect(self.sliderValueChanged)

        signals.frame_loaded.connect(self.on_frame_loaded)



    def on_frame_loaded(self, frame: DataFrame, group_index: int, frame_index: int, group_size: int):
        data = frame.imaging.data
        self.init_slider_range(data)


    def sliderValueChanged(self):
        self.slider_value = self.slider.value()

        temp = math.tan(self.slider_value / 100) / 100
        true_value = math.pow(10, self.exponent) * temp

        self.text_right.setText("{:.7f}".format(true_value))

    def init_slider_range(self, data):
        #data = config.dataset.imaging.data
        max_value = np.max(data)
        min_value = np.min(data)

        self.exponent = math.floor(math.log10(max_value))
        scaled_value = max_value / math.pow(10, self.exponent)

        min_show = int(math.atan(min_value))
        max_show = int(math.atan(scaled_value * 100) * 100)

        self.slider.setMinimum(min_show)
        self.slider.setMaximum(max_show)
        self.slider.setValue(min_show)
        self.slider.setSingleStep(1)

    def slider_btn_clicked(self):

        line_edit = QLineEdit()
        line_edit.setText(self.text_right.text())
        line_edit.setFixedHeight(23)
        line_edit.setStyleSheet("background:#484848;font-size: 15px;border: 0px")
        self.line_edit_widget_layout.addWidget(line_edit)

    def add_line_edit(self):
        line_edit = QLineEdit()
        line_edit.setText("")
        line_edit.setFixedHeight(23)
        line_edit.setStyleSheet("background:#484848;font-size: 15px;border: 0px")
        self.line_edit_widget_layout.addWidget(line_edit)

    def remove_line_edit(self):
        count = self.line_edit_widget_layout.count()
        if count > 0:
            item = self.line_edit_widget_layout.takeAt(count - 1)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)  # 解除父对象关系
                widget.deleteLater()  # 删除小部件

    def clear_line_edit(self):
        while self.line_edit_widget_layout.count() > 0:
            item = self.line_edit_widget_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)  # 解除父对象关系
                widget.deleteLater()  # 删除小部件
        signals.contour_clicked.emit(0)

    def apply(self):
        texts = []
        # 遍历所有子组件
        for widget in self.findChildren(QLineEdit):
            texts.append(widget.text())
        # 打印所有 QLineEdit 的文本
        values = []
        for i, text in enumerate(texts, start=1):
            values.append(float(text))
        signals.contour_value_changed.emit(values)


class GradientWidget(FeatureItem):
    def __init__(self):
        super().__init__()
        self.fixed_height = 280
        self.label_title.setText('More')
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.setContentsMargins(0, 0, 0, 0)
        self.show_widget.setLayout(layout)
        self.show_widget.setStyleSheet("padding:5px;")

        gradient_label = QLabel("Backscatter Gradient")
        doppler_label = QLabel("Doppler Estimate")

        gradient_widget = QWidget()
        gradient_widget_layout = QVBoxLayout()
        gradient_widget_layout.setContentsMargins(5, 5, 5, 5)
        gradient_widget.setStyleSheet("background-color:#333333")
        gradient_widget.setLayout(gradient_widget_layout)

        doppler_widget = QWidget()
        doppler_widget_layout = QVBoxLayout()
        doppler_widget_layout.setContentsMargins(5, 5, 5, 5)
        doppler_widget.setStyleSheet("background-color:#333333")
        doppler_widget.setLayout(doppler_widget_layout)

        arrow_btn = QCheckBox()
        arrow_btn.setText('Backscatter Gradient')
        arrow_btn.clicked.connect(lambda state: signals.gradient_arrow_clicked.emit(state))
        arrow_btn.setStyleSheet("""
                                    QCheckBox::indicator:unchecked {
                                        background-color: #43494a;
                                        border: 1px solid #6b6b6b;
                                    }
                                    """)

        streamline_btn = QCheckBox()
        streamline_btn.setText('Gradient streamline')
        streamline_btn.clicked.connect(lambda state: signals.gradient_streamline_clicked.emit(state))
        streamline_btn.setStyleSheet("""
                                    QCheckBox::indicator:unchecked {
                                        background-color: #43494a;
                                        border: 1px solid #6b6b6b;
                                    }
                                    """)

        heat_flux_btn = QCheckBox()
        heat_flux_btn.setText('Heat Flux')
        heat_flux_btn.clicked.connect(lambda state: signals.heat_flux_clicked.emit(state))
        heat_flux_btn.setStyleSheet("""QCheckBox::indicator:unchecked {
                                                background-color: #43494a;
                                                border: 1px solid #6b6b6b;
                                            }""")

        velocity_streamline_btn = QCheckBox()
        velocity_streamline_btn.setText('Velocity Streamline')
        velocity_streamline_btn.clicked.connect(lambda state: signals.velocity_streamline_clicked.emit(state))
        velocity_streamline_btn.setStyleSheet("""QCheckBox::indicator:unchecked {
                                                background-color: #43494a;
                                                border: 1px solid #6b6b6b;
                                            }""")

        gradient_widget_layout.addWidget(arrow_btn)
        gradient_widget_layout.addWidget(streamline_btn)
        doppler_widget_layout.addWidget(heat_flux_btn)
        doppler_widget_layout.addWidget(velocity_streamline_btn)

        layout.addWidget(gradient_label)
        layout.addWidget(gradient_widget)
        layout.addWidget(doppler_label)
        layout.addWidget(doppler_widget)



class DataWidget(FeatureItem):
    def __init__(self):
        super().__init__()
        self.fixed_height = 450
        self.label_title.setText('Data')
        self.show_widget_layout = QVBoxLayout()
        self.show_widget_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.show_widget_layout.setContentsMargins(0, 0, 0, 0)
        self.show_widget.setLayout(self.show_widget_layout)

        file_widget = FileWidget()
        cut_widget = CutWidget()
        cut_widget.setFixedHeight(150)

        self.show_widget_layout.addWidget(file_widget)
        self.show_widget_layout.addWidget(cut_widget)


# ------------------------------------------------------------
# 读取文件，显示文件目录，选择文件
# ------------------------------------------------------------
class FileWidget(QWidget):
    # 文件组
    class FileGroup:
        def __init__(self):
            self.file_dir = ''
            self.region_name = ''
            self.file_names = []

    # 所有的文件组
    file_groups = []
    group_ptr = -1
    file_ptr = -1

    def __init__(self):
        super().__init__()

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.setSpacing(0)
        self.setLayout(layout)

        title_widget = QWidget()
        title_widget.setFixedHeight(30)
        layout.addWidget(title_widget)
        title_layout = QHBoxLayout()
        title_layout.setContentsMargins(5, 5, 5, 0)
        title_widget.setLayout(title_layout)

        title = QLabel('File:')
        title.setFont(QFont('Arial', 10))
        title_layout.addWidget(title)
        spacer = QSpacerItem(0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        title_layout.addItem(spacer)

        add_btn = QPushButton('Add')
        add_btn.setFixedSize(75, 25)
        add_btn.setStyleSheet(
            'font-size:12px;background-color: #365880;border-radius: 3px;'
            'border:1px solid #4c708c')
        title_layout.addWidget(add_btn)
        add_btn.clicked.connect(self.add_files)

        self.tree = CustomTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.file_groups = self.file_groups
        layout.addWidget(self.tree)

        # ==============================
        # global slots
        # ==============================
        signals.pick_changed.connect(self.pick_changed)



    # 打开对话框，选择index文件
    def add_files(self):
        # 创建file group
        index_file_path = QFileDialog.getOpenFileName(self, 'Open File', '../data/processed', 'Index File (index.bin)')[0]
        group = self.FileGroup()
        group.file_dir = os.path.dirname(index_file_path)
        group.file_names, group.region_name = reader.read_index(index_file_path)
        self.file_groups.append(group)

        # 添加到tree
        dir_item = QTreeWidgetItem(self.tree, [os.path.basename(group.file_dir)])
        dir_item.setIcon(0, QIcon("../res/icons/folder.png"))
        for file_name in group.file_names:
            file_item = QTreeWidgetItem(dir_item, [file_name])
            file_item.setIcon(0, QIcon("../res/icons/file.png"))

        # 读取该组的第一个文件
        self.file_selected(len(self.file_groups) - 1, 0)


    # 选择文件并读取
    def file_selected(self, group_ptr: int, file_ptr: int):
        if self.group_ptr != group_ptr:
            # 加载region文件
            region_file_path = self.file_groups[group_ptr].file_dir + '/' + self.file_groups[group_ptr].region_name
            regions, marks = reader.read_regions(region_file_path)
            #print(marks.shape)
            signals.load_region.emit(regions, marks)

        # 读取数据帧文件
        frame_file_path = self.file_groups[group_ptr].file_dir + '/' + self.file_groups[group_ptr].file_names[file_ptr]
        frame = reader.read_frame(frame_file_path)
        self.group_ptr = group_ptr
        self.file_ptr = file_ptr
        signals.load_frame.emit(frame, self.group_ptr, self.file_ptr, len(self.file_groups[self.group_ptr].file_names))
        self.tree.highlight_item(self.group_ptr, self.file_ptr)


    # 改变选择的数据帧
    def pick_changed(self, group_index: int, frame_index: int):
        self.file_selected(group_index, frame_index)


class CustomTreeWidget(QTreeWidget):
    file_groups = []

    def __init__(self, parent=None):
        super(CustomTreeWidget, self).__init__(parent)
        #self.file_name_list = []
        self.setSelectionMode(QTreeWidget.SelectionMode.SingleSelection)  # 只允许单项选择
        self.last_highlighted_item = None

        self.setStyleSheet("""
                            QTreeWidget{
                                margin-top:5px;
                                background-color:#333333
                            }
                            QTreeWidget::item:selected:active {
                                background-color: #4b6eaf;
                                color: #bbbbbb;
                            }
                            QTreeWidget::item:selected:!active {
                                background-color: #0d293e;
                                color: #bbbbbb;
                            }
                        """)


    def mouseDoubleClickEvent(self, event):
        item = self.itemAt(event.pos())
        if item:
            self.custom_double_click_event(item)
        # super(CustomTreeWidget, self).mouseDoubleClickEvent(event)

    def custom_double_click_event(self, item):
        # 自定义双击事件的处理逻辑
        dir_name = item.parent().text(0)
        file_name = item.text(0)
        dir_index = -1
        file_index = -1
        for i in range(len(self.file_groups)):
            if dir_name == os.path.basename(self.file_groups[i].file_dir):
                dir_index = i
                break

        for j in range(len(self.file_groups[dir_index].file_names)):
            if file_name == self.file_groups[dir_index].file_names[j]:
                file_index = j
                break

        signals.pick_changed.emit(dir_index, file_index)

        # 高亮当前项
        item.setSelected(True)
        if self.last_highlighted_item and self.last_highlighted_item != item:
            # 取消之前高亮的项
            self.last_highlighted_item.setSelected(False)

        # 更新最后一个高亮的项
        self.last_highlighted_item = item


    def focusOutEvent(self, event):
        # 当失去焦点时，保持高亮状态
        if self.last_highlighted_item:
            self.last_highlighted_item.setSelected(True)
        super(CustomTreeWidget, self).focusOutEvent(event)

    def highlight_item(self, group_index: int, frame_index: int):
        folder = self.topLevelItem(group_index)
        item = folder.child(frame_index)
        # 高亮当前项
        item.setSelected(True)
        if self.last_highlighted_item and self.last_highlighted_item != item:
            # 取消之前高亮的项
            self.last_highlighted_item.setSelected(False)

        # 更新最后一个高亮的项
        self.last_highlighted_item = item



# ------------------------------------------------------------
# 裁剪
# ------------------------------------------------------------
class CutWidget(QWidget):
    # 当前数据的组
    now_group = -1
    # 当前的可选范围
    frame_bounds = [0, 10, 0, 10, 0, 10]

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        self.setLayout(layout)

        title = QLabel('Cut:')
        title.setFont(QFont('Arial', 10))
        layout.addWidget(title)

        self.x_item = CutItem('X')
        self.y_item = CutItem('Y')
        self.z_item = CutItem('Z')

        self.x_item.range_slider.range_changed.connect(self.range_changed)
        self.y_item.range_slider.range_changed.connect(self.range_changed)
        self.z_item.range_slider.range_changed.connect(self.range_changed)

        layout.addWidget(self.x_item)
        layout.addWidget(self.y_item)
        layout.addWidget(self.z_item)

        cut_btn = QPushButton('Cut')
        cut_btn.setFixedSize(70, 25)
        cut_btn.setStyleSheet("font-size:12px;background-color: #4c5052;border-radius: 3px;border: 1px solid #5e6060")
        cut_btn.clicked.connect(self.cut_clicked)

        reset_btn = QPushButton('Reset')
        reset_btn.setFixedSize(70, 25)
        reset_btn.setStyleSheet("font-size:12px;background-color: #4c5052;border-radius: 3px;border: 1px solid #5e6060")
        reset_btn.clicked.connect(self.reset_bounds)

        operator_layout = QHBoxLayout()
        operator_layout.addStretch(1)
        operator_layout.addWidget(cut_btn)
        operator_layout.addWidget(reset_btn)
        operator_layout.setSpacing(10)

        layout.addLayout(operator_layout)

        # --------------------------------------------------
        # global slots
        # --------------------------------------------------
        signals.frame_loaded.connect(self.on_frame_loaded)


    def on_frame_loaded(self, frame: DataFrame, group_index: int, frame_index: int, group_size: int):
        if group_index != self.now_group:
            self.now_group = group_index
            self.frame_bounds = processor.calculate_bounds(frame)
            self.reset_bounds()
        signals.frame_rendering.emit()


    def reset_bounds(self):
        bounds = self.frame_bounds
        self.x_item.range_slider.setRange(bounds[0], bounds[1], bounds[0], bounds[1])
        self.y_item.range_slider.setRange(bounds[2], bounds[3], bounds[2], bounds[3])
        self.z_item.range_slider.setRange(bounds[4], bounds[5], bounds[4], bounds[5])
        signals.bounds_changed.emit(bounds)


    # 点击cut按钮进行裁剪
    def cut_clicked(self):
        x_left, x_right = self.x_item.range_slider.getRange()
        y_left, y_right = self.y_item.range_slider.getRange()
        z_left, z_right = self.z_item.range_slider.getRange()
        bounds = [x_left, x_right, y_left, y_right, z_left, z_right]
        signals.bounds_changed.emit(bounds)


    # 当滑块滑动时
    def range_changed(self):
        x_left, x_right = self.x_item.range_slider.getRange()
        y_left, y_right = self.y_item.range_slider.getRange()
        z_left, z_right = self.z_item.range_slider.getRange()
        bounds = [x_left, x_right, y_left, y_right, z_left, z_right]
        signals.bounds_slider_changed.emit(bounds)



class CutItem(QWidget):
    def __init__(self, name):
        super().__init__()
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.setLayout(layout)
        label = QLabel(name)
        label.setFont(QFont('Arial', 10))
        label.setStyleSheet("font-weight: bold")
        layout.addWidget(label)
        self.range_slider = RangeSlider()
        layout.addWidget(self.range_slider)


class RangeSlider(QWidget):
    range_changed = pyqtSignal()

    def __init__(self, min_value=0, max_value=10, left=0, right=10, mid=5):
        super().__init__()
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.left = left
        self.right = right
        # self.axis = 0  # 0:X  1:Y 2:Z

        # 添加双滑动块 设置滑动块基础信息
        self.slider_left = QSlider(Qt.Orientation.Horizontal)
        self.slider_left.setMinimum(min_value)
        self.slider_left.setMaximum(mid)
        self.slider_left.setValue(self.left)
        self.slider_left.setSingleStep(1)

        self.slider_left.setStyleSheet("""

            QSlider::groove:horizontal {
                background: #DDDDDD;
                height: 4px;
                border-top-left-radius: 2px;  /* 只设置左上角圆角 */
                border-bottom-left-radius: 2px;  /* 只设置左下角圆角 */
                border-top-right-radius: 0px;  /* 右上角不设置圆角 */
                border-bottom-right-radius: 0px;  /* 右下角不设置圆角 */
            }
            QSlider::add-page:horizontal {
                background: #87CEFA;
            }
            QSlider::handle:horizontal {
                background: #5599FF;
                width: 16px;  /* 控制手柄的宽度 */
                height: 10px; /* 控制手柄的高度 */
                border-radius: 5px;  /* 圆形手柄，半径应为宽度/2 */
                margin: -3px 0;

            }
            QSlider::handle:horizontal:hover {
                background: #66ccff;

            }
            QSlider::handle:horizontal:pressed {
                background: #3399ff;
            }
        """)

        self.slider_right = QSlider(Qt.Orientation.Horizontal)
        self.slider_right.setMinimum(mid)
        self.slider_right.setMaximum(max_value)
        self.slider_right.setValue(self.right)
        self.slider_right.setSingleStep(1)
        self.slider_right.setStyleSheet("""

                QSlider::groove:horizontal {
                background: #DDDDDD;
                height: 4px;
                border-top-left-radius: 0px;  /* 左上 */
                border-bottom-left-radius: 0px;  /* 左下 */
                border-top-right-radius: 2px;  /* 右上 */
                border-bottom-right-radius: 2px;  /* 右下 */
            }
             QSlider::sub-page:horizontal {
                background: #87CEFA;

            }

            QSlider::handle:horizontal {
                background: #5599FF;
                width: 16px;  /* 控制手柄的宽度 */
                height: 10px; /* 控制手柄的高度 */
                border-radius: 5px;  /* 圆形手柄，半径应为宽度/2 */
                margin: -3px 0;
            }
            QSlider::handle:horizontal:hover {
                background: #66ccff;
            }
            QSlider::handle:horizontal:pressed {
                background: #3399ff;
            }
                """)

        slider_layout = QHBoxLayout()
        slider_layout.setSpacing(0)
        slider_layout.addWidget(self.slider_left)
        slider_layout.addWidget(self.slider_right)

        # 添加左右数值显示 可以与滑动块的数值相互绑定
        self.text_left = QLineEdit()
        self.text_left.setText(str(self.left))
        self.text_left.setFixedWidth(30)
        self.text_left.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.text_left.setStyleSheet("""
            QLineEdit {
                border: 1px solid #646464;
                background: #43494a;
            }
        """)

        _label = QLabel()
        _label.setText("~")

        self.text_right = QLineEdit()
        self.text_right.setText(str(self.right))
        self.text_right.setFixedWidth(30)
        self.text_right.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.text_right.setStyleSheet("""
                    QLineEdit {
                        border: 1px solid #646464;
                        background: #43494a;
                    }
                """)

        layout.addLayout(slider_layout)
        layout.addWidget(self.text_left)
        layout.addWidget(_label)
        layout.addWidget(self.text_right)

        self.setLayout(layout)
        self.bind()

    def bind(self):
        self.slider_left.valueChanged.connect(self.leftValueChanged)
        self.slider_right.valueChanged.connect(self.rightValueChanged)

    def leftValueChanged(self):
        self.left = self.slider_left.value()
        self.text_left.setText(str(self.left))
        self.range_changed.emit()

    def rightValueChanged(self):
        self.right = self.slider_right.value()
        self.text_right.setText(str(self.right))
        self.range_changed.emit()

    def getRange(self):
        return self.left, self.right

    def setRange(self, left, right, min_val, max_val):
        self.left = left
        self.right = right
        mid = (min_val + max_val) / 2
        self.slider_left.setMinimum(min_val)
        self.slider_left.setMaximum(int(mid))
        self.slider_left.setValue(left)
        self.slider_right.setMinimum(int(mid))
        self.slider_right.setMaximum(max_val)
        self.slider_right.setValue(right)
        self.text_left.setText(str(self.slider_left.value()))
        self.text_right.setText(str(self.slider_right.value()))
