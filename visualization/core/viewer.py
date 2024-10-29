# ============================================================
# 数据渲染，展示
# ============================================================

import numpy as np
import scipy
import vtk
import os
import math
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
from vtkmodules.util import numpy_support

from common.entity import UniformGrid, DataFrame
from visualization.core import doppler_processor, processor, reader
from visualization.gui.signal_group import signals


def to_vtk_image(image):
    data = image.data
    bounds = image.bounds
    spacing = image.spacing
    vtk_image = vtk.vtkImageData()
    vtk_image.SetDimensions(data.shape)
    vtk_image.SetSpacing(spacing[0], spacing[1], spacing[2])
    vtk_image.SetOrigin(bounds[0], bounds[2], bounds[4])

    data = data.astype(np.float32)
    data = data.transpose(2, 1, 0)
    vtk_array = numpy_support.numpy_to_vtk(data.ravel(), deep=True, array_type=vtk.VTK_FLOAT)
    vtk_array.SetNumberOfComponents(1)
    vtk_array.SetName("data")
    vtk_image.GetPointData().SetScalars(vtk_array)
    return vtk_image


class ColorBarManager:
    def __init__(self):
        self.bars = {}

    def add_bar(self, lookup_table, name):
        bar = vtk.vtkScalarBarActor()
        bar.SetOrientationToHorizontal()
        bar.SetLookupTable(lookup_table)
        bar.SetTitle(name)
        bar.SetHeight(0.04)
        bar.SetWidth(0.2)
        self.bars[name] = bar
        self.adjust_position()

    def adjust_position(self):
        i = 0
        for bar in self.bars.values():
            bar.SetPosition((0, 0.96 - i*0.06))
            i = i + 1

    def get_bar(self, name):
        return self.bars[name]

    def remove_bar(self, name):
        self.bars.pop(name)
        self.adjust_position()


class ViewerCamera(vtk.vtkInteractorStyleTrackballCamera):
    def __init__(self):
        super().__init__()
        self.locked = True
        self.save_dir = np.array([0, -1])

        self.AddObserver(vtk.vtkCommand.LeftButtonPressEvent, self.new_left_button_down)
        self.AddObserver(vtk.vtkCommand.LeftButtonReleaseEvent, self.new_left_button_up)
        self.AddObserver(vtk.vtkCommand.MouseMoveEvent, self.new_mouse_move)

    def new_left_button_down(self, obj, event):
        self.OnLeftButtonDown()
        self.locked = False

    def new_left_button_up(self, obj, event):
        self.OnLeftButtonUp()
        self.locked = True

    def new_mouse_move(self, obj, event):
        self.OnMouseMove()
        render = self.GetInteractor().GetRenderWindow().GetRenderers().GetFirstRenderer()
        pos = render.GetActiveCamera().GetPosition()
        focal = render.GetActiveCamera().GetFocalPoint()
        direction = np.array([pos[0] - focal[0], pos[1] - focal[1]])

        if not self.locked and np.linalg.norm(direction) > 0:
            cos_angle = np.dot(direction, self.save_dir) / (np.linalg.norm(direction) * np.linalg.norm(self.save_dir))
            angle = math.acos(min(cos_angle, 1.0))
            sign = np.sign(np.cross(direction, self.save_dir))
            self.save_dir = direction

            #print('angle', sign * angle * 180 / math.pi)
            signals.camera_rotated.emit(sign * angle * 180 / math.pi)


class Viewer:
    # ------------------------------------------------------------
    # data
    # ------------------------------------------------------------
    regions = []
    marks = np.ndarray
    frame = DataFrame()
    bounds = []

    # color bars
    color_bars = ColorBarManager()

    # ------------------------------------------------------------
    # vtk
    # ------------------------------------------------------------
    interactor = None
    renderer = None

    # ------------------------------------------------------------
    # Volume Rendering Parameters
    # ------------------------------------------------------------
    opacity = 0.0
    colormap_name = 'default'

    # ------------------------------------------------------------
    # initialization
    # ------------------------------------------------------------
    def __init__(self):
        ...

    def create_interactor(self):
        self.interactor = QVTKRenderWindowInteractor()
        self.interactor.SetInteractorStyle(ViewerCamera())
        self.renderer = vtk.vtkRenderer()
        self.renderer.SetBackground(0.65, 0.65, 0.65)
        self.renderer.SetBackground2(0.3, 0.3, 0.3)
        self.renderer.SetGradientBackground(True)
        self.interactor.GetRenderWindow().AddRenderer(self.renderer)
        self.renderer.ResetCamera()
        self.interactor.Initialize()
        return self.interactor

    def create_light(self):
        light = vtk.vtkLight()
        light.SetPosition(0, 0, 100)
        light.SetFocalPoint(-100, 0, 0)
        light.SetColor(1.0, 1.0, 1.0)
        light.SetIntensity(0.9)
        self.renderer.AddLight(light)


    # ------------------------------------------------------------
    # outline cube
    # ------------------------------------------------------------
    outline_actor = None
    outline_selected_flag = False

    def draw_outline(self, bounds: list):
        if not self.outline_selected_flag:
            cube = vtk.vtkCubeSource()
            cube.SetBounds(tuple(bounds))
            outline = vtk.vtkOutlineFilter()
            outline.SetInputConnection(cube.GetOutputPort())

            mapper = vtk.vtkPolyDataMapper()
            mapper.SetInputConnection(outline.GetOutputPort())
            self.outline_actor = vtk.vtkActor()
            self.outline_actor.SetMapper(mapper)
            self.outline_actor.GetProperty().SetColor(0.0, 1.0, 0.0)
            self.outline_actor.GetProperty().SetLineWidth(3.0)
            self.renderer.AddActor(self.outline_actor)

            self.outline_selected_flag = True

    def remove_outline(self):
        if self.outline_selected_flag:
            self.renderer.RemoveActor(self.outline_actor)
            self.outline_selected_flag = False

    # ------------------------------------------------------------
    # axis
    # ------------------------------------------------------------
    axis_actor = None
    axis_selected_flag = False
    def draw_axis(self):
        if not self.axis_selected_flag:
            bounds = self.bounds
            self.axis_actor = vtk.vtkCubeAxesActor()
            self.axis_actor.SetCamera(self.renderer.GetActiveCamera())
            self.axis_actor.SetBounds(bounds)
            self.axis_actor.SetXAxisRange(bounds[0], bounds[1])
            self.axis_actor.SetYAxisRange(bounds[2], bounds[3])
            self.axis_actor.SetZAxisRange(bounds[4], bounds[5])
            self.axis_actor.GetXAxesLinesProperty().SetLineWidth(1.5)
            self.axis_actor.GetYAxesLinesProperty().SetLineWidth(1.5)
            self.axis_actor.GetZAxesLinesProperty().SetLineWidth(1.5)
            self.axis_actor.SetVisibility(True)
            # self.axis_actor.SetFlyMode(3)
            self.axis_actor.SetFlyMode(0)
            # self.axis_actor.SetXTitle('Easting of COVIS ( m )')
            # self.axis_actor.SetYTitle('Northing of COVIS ( m )')
            # self.axis_actor.SetZTitle('Height above COVIS base ( m )')
            self.axis_actor.SetXTitle('X-Axis (m)')
            self.axis_actor.SetYTitle('Y-Axis (m)')
            self.axis_actor.SetZTitle('Z-Axis (m)')
            self.renderer.AddActor(self.axis_actor)
            self.axis_selected_flag = True

    def remove_axis(self):
        if self.axis_selected_flag:
            self.renderer.RemoveActor(self.axis_actor)
            self.axis_actor = None
            self.axis_selected_flag = False

    # ------------------------------------------------------------
    # seabed
    # ------------------------------------------------------------
    seabed_data = UniformGrid()
    seabed_poly = vtk.vtkPolyData()
    seabed_actor = None
    seabed_selected_flag = False

    def draw_seabed(self, deepest=-8):
        if not self.seabed_selected_flag:
            grid = processor.cut_uniform(self.seabed_data, self.bounds)
            data = grid.data
            data[data < deepest] = deepest
            spacing = grid.spacing
            bounds = grid.bounds

            points = vtk.vtkPoints()
            points.Allocate(data.ravel().shape[0])
            for i in range(data.shape[0]):
                for j in range(data.shape[1]):
                    points.InsertNextPoint(i * spacing[0] + bounds[0], j * spacing[1] + bounds[2], data[i][j])

            self.seabed_poly.SetPoints(points)
            delaunay = vtk.vtkDelaunay2D()
            delaunay.SetInputData(self.seabed_poly)
            delaunay.Update()

            subdivision_filter = vtk.vtkLoopSubdivisionFilter()
            subdivision_filter.SetInputConnection(delaunay.GetOutputPort())
            subdivision_filter.SetNumberOfSubdivisions(2)

            smooth_filter = vtk.vtkSmoothPolyDataFilter()
            smooth_filter.SetInputConnection(subdivision_filter.GetOutputPort())
            smooth_filter.SetNumberOfIterations(150)
            smooth_filter.Update()

            texture_reader = vtk.vtkJPEGReader()
            texture_reader.SetFileName('../res/texture/rock2.jpg')
            texture = vtk.vtkTexture()
            texture.SetInputConnection(texture_reader.GetOutputPort())
            texture_map = vtk.vtkTextureMapToPlane()
            texture_map.SetInputConnection(smooth_filter.GetOutputPort())

            mapper = vtk.vtkPolyDataMapper()
            mapper.SetInputConnection(texture_map.GetOutputPort())

            self.seabed_actor = vtk.vtkActor()
            self.seabed_actor.SetMapper(mapper)
            self.seabed_actor.SetTexture(texture)
            self.seabed_actor.GetProperty().SetColor(0.7, 0.85, 0.9)
            self.renderer.AddActor(self.seabed_actor)
            self.seabed_selected_flag = True

    def remove_seabed(self):
        if self.seabed_selected_flag:
            self.renderer.RemoveActor(self.seabed_actor)
            self.seabed_actor = None
            self.seabed_selected_flag = False


    # ------------------------------------------------------------
    # diffuse flow
    # ------------------------------------------------------------
    diffuse_selected_flag = False
    def draw_diffuse(self):
        if not self.diffuse_selected_flag:
            diffuse = processor.cut_uniform(self.frame.diffuse, self.bounds)
            scalars = vtk.vtkDoubleArray()
            for i in range(diffuse.data.shape[0]):
                for j in range(diffuse.data.shape[1]):
                    scalars.InsertNextValue(diffuse.data[i][j])
            self.seabed_poly.GetPointData().SetScalars(scalars)
            lookup_table = vtk.vtkColorTransferFunction()
            lookup_table.AddRGBPoint(scalars.GetRange()[0], 0.7, 0.85, 0.9)
            lookup_table.AddRGBPoint(scalars.GetRange()[1] / 2, 0.1, 0.7, 0.3)
            lookup_table.AddRGBPoint(scalars.GetRange()[1], 0.8, 0.1, 0.1)
            lookup_table.Build()
            self.seabed_actor.GetMapper().SetScalarRange(scalars.GetRange())
            self.seabed_actor.GetMapper().SetLookupTable(lookup_table)
            self.seabed_actor.GetProperty().SetColor(0.0, 0.0, 0.0)
            self.diffuse_selected_flag = True

            self.color_bars.add_bar(lookup_table, 'diffuse')
            self.renderer.AddActor(self.color_bars.get_bar('diffuse'))


    def remove_diffuse(self):
        if self.diffuse_selected_flag:
            diffuse = processor.cut_uniform(self.frame.diffuse, self.bounds)
            scalars = vtk.vtkDoubleArray()
            for i in range(diffuse.data.shape[0]):
                for j in range(diffuse.data.shape[1]):
                    scalars.InsertNextValue(0)
            self.seabed_poly.GetPointData().SetScalars(scalars)
            self.seabed_actor.GetProperty().SetColor(0.7, 0.85, 0.9)
            self.diffuse_selected_flag = False

            self.renderer.RemoveActor(self.color_bars.get_bar('diffuse'))
            self.color_bars.remove_bar('diffuse')


    # ------------------------------------------------------------
    # selected regions
    # ------------------------------------------------------------
    selected_regions = []

    def add_selected_region(self, region_id):
        self.selected_regions.append(region_id)

        if self.volume_selected_flag:
            self.draw_volume(region_id)
        if self.contour_selected_flag:
            self.draw_contour(region_id)
        if self.centerline_selected_flag:
            self.draw_centerline(region_id)
        if self.gradient_arrow_selected_flag:
            self.draw_gradient_arrow(region_id)
        if self.gradient_streamline_selected_flag:
            self.draw_gradient_streamline(region_id)
        if self.heat_flux_selected_flag:
            self.draw_heat_flux(region_id)
        if self.velocity_streamline_selected_flag:
            self.draw_velocity_streamline(region_id)


    def remove_selected_region(self, region_id):
        self.selected_regions.remove(region_id)

        if self.volume_selected_flag:
            self.remove_volume(region_id)
        if self.contour_selected_flag:
            self.remove_contour(region_id)
        if self.centerline_selected_flag:
            self.remove_centerline(region_id)
        if self.gradient_arrow_selected_flag:
            self.remove_gradient_arrow(region_id)
        if self.gradient_streamline_selected_flag:
            self.remove_gradient_streamline(region_id)
        if self.heat_flux_selected_flag:
            self.remove_heat_flux(region_id)
        if self.velocity_streamline_selected_flag:
            self.remove_velocity_streamline(region_id)


    # 计算region区域
    def imaging_bounds_cut(self, region_id):
        region_bounds = [0, 0, 0, 0, 0, 0]
        for region in self.regions:
            if region.id == region_id:
                region_bounds = region.bounds[2:]
                break
        spacing = self.frame.imaging.spacing
        for i in range(len(region_bounds)):
            region_bounds[i] = region_bounds[i] * spacing[int(i/2)] + self.frame.imaging.bounds[int(i/2) * 2]
        region_bounds[0] = max(region_bounds[0], self.bounds[0])
        region_bounds[1] = min(region_bounds[1], self.bounds[1])
        region_bounds[2] = max(region_bounds[2], self.bounds[2])
        region_bounds[3] = min(region_bounds[3], self.bounds[3])
        region_bounds[4] = max(region_bounds[4], self.bounds[4])
        region_bounds[5] = min(region_bounds[5], self.bounds[5])
        region_grid = processor.cut_uniform(self.frame.imaging, region_bounds)
        mark_grid = self.frame.imaging.copy()
        mark_grid.data = self.marks[self.frame.id]
        region_marks = processor.cut_uniform(mark_grid, region_bounds).data
        region_grid.data[region_marks != region_id] = 1e-9
        return region_grid

    def doppler_bounds_cut(self, imaging_cut: UniformGrid, doppler: UniformGrid):
        doppler_cut = imaging_cut.copy()
        cut_bounds = [0, 0, 0, 0, 0, 0]
        for i in range(6):
            cut_bounds[i] = int((imaging_cut.bounds[i] - doppler.bounds[int(i / 2) * 2]) / imaging_cut.spacing[int(i / 2)])
        doppler_cut.data = doppler.data[cut_bounds[0]:cut_bounds[1] + 1, cut_bounds[2]:cut_bounds[3] + 1, cut_bounds[4]:cut_bounds[5] + 1]
        doppler_cut.data[imaging_cut.data <= 1e-9] = 1e-9
        return doppler_cut


    # ------------------------------------------------------------
    # plumes direct volume rendering
    # ------------------------------------------------------------
    volume_set = {}
    volume_selected_flag = False

    def draw_volume(self, region_id):
        strid = str(region_id)

        if strid not in self.volume_set:
            image = self.imaging_bounds_cut(region_id)
            image.data[image.data < 1e-6] = 1e-6
            image.data = np.log10(image.data)
            image.data = image.data + 6

            # to vtk file
            vtk_image = to_vtk_image(image)

            # writer = vtk.vtkXMLImageDataWriter()
            # writer.SetInputData(vtk_image)
            # writer.SetFileName(os.path.join('1.vtk'))
            # writer.Write()

            # colormap and opacity function
            range_v = vtk_image.GetScalarRange()
            plumes_color_function = vtk.vtkColorTransferFunction()
            if self.colormap_name == 'default':
                ds = (range_v[1] - range_v[0]) / 4
                plumes_color_function.AddRGBPoint(range_v[0], 1.0, 1.0, 1.0)
                plumes_color_function.AddRGBPoint(range_v[0] + 2*ds/4, 0.9, 0.9, 0.6)
                plumes_color_function.AddRGBPoint(range_v[0] + 3*ds/4, 0.9, 0.9, 0.4)
                plumes_color_function.AddRGBPoint(range_v[1], 1.0, 1.0, 0.0)
            else:
                colormaps = os.listdir('../res/colormap')
                for cmap in colormaps:
                    cmap0 = os.path.splitext(cmap)[0]
                    if self.colormap_name == cmap0:
                        colormap = reader.load_colormap('../res/colormap/' + cmap)
                        ds = (range_v[1] - range_v[0]) / len(colormap)
                        for i in range(len(colormap)):
                            color = colormap[i]
                            plumes_color_function.AddRGBPoint(range_v[0] + ds*i, color[0], color[1], color[2])

            plumes_opacity_function = vtk.vtkPiecewiseFunction()
            plumes_opacity_function.AddPoint(range_v[0], 0)
            plumes_opacity_function.AddPoint(range_v[1], self.opacity)


            # rendering
            volume_mapper = vtk.vtkGPUVolumeRayCastMapper()
            volume_mapper.SetInputData(vtk_image)
            volume_mapper.SetAutoAdjustSampleDistances(False)
            volume_mapper.SetSampleDistance(0.05)

            volume_property = vtk.vtkVolumeProperty()
            volume_property.SetColor(plumes_color_function)
            volume_property.SetScalarOpacity(plumes_opacity_function)
            volume_property.SetInterpolationTypeToLinear()

            volume_actor = vtk.vtkVolume()
            volume_actor.SetMapper(volume_mapper)
            volume_actor.SetProperty(volume_property)

            if len(self.volume_set) == 0:
                self.color_bars.add_bar(plumes_color_function, 'plume')
                self.renderer.AddActor(self.color_bars.get_bar('plume'))

            self.renderer.AddActor(volume_actor)
            self.volume_set[strid] = volume_actor

    def remove_volume(self, region_id):
        strid = str(region_id)

        if strid in self.volume_set:
            self.renderer.RemoveActor(self.volume_set[strid])
            self.volume_set.pop(strid)
            if len(self.volume_set) == 0:
                self.renderer.RemoveActor(self.color_bars.get_bar('plume'))
                self.color_bars.remove_bar('plume')


    def volume_selected(self):
        self.volume_selected_flag = True
        for strid in self.selected_regions:
            self.draw_volume(int(strid))

    def volume_unselected(self):
        self.volume_selected_flag = False
        for strid in self.selected_regions:
            self.remove_volume(int(strid))


    # ------------------------------------------------------------
    # plumes iso-surface
    # ------------------------------------------------------------
    contour_set = {}
    contour_values = []
    contour_selected_flag = False

    def draw_contour(self, region_id):
        strid = str(region_id)
        if strid not in self.contour_set:
            region_grid = self.imaging_bounds_cut(region_id)
            vtk_image = to_vtk_image(region_grid)

            contour = vtk.vtkContourFilter()
            contour.SetInputData(vtk_image)
            contour_values = self.contour_values.copy()
            contour_values.sort()
            lookup_table = vtk.vtkLookupTable()
            lookup_table.SetNumberOfColors(len(contour_values))

            len_v = len(contour_values)
            x = [0, 1, 2]
            r = [131, 86, 0]
            g = [168, 115, 0]
            b = [230, 200, 255]
            a = [0.2, 0.15, 0.1]
            r_func = scipy.interpolate.interp1d(x, r)
            g_func = scipy.interpolate.interp1d(x, g)
            b_func = scipy.interpolate.interp1d(x, b)
            a_func = scipy.interpolate.interp1d(x, a)

            for i in range(len_v):
                x_value = i * (len(x) - 1) / len_v
                contour.SetValue(i, contour_values[i])
                lookup_table.SetTableValue(i, (
                r_func(x_value) / 255, g_func(x_value) / 255, b_func(x_value) / 255, a_func(x_value)))

            lookup_table.Build()

            if len(self.contour_set) == 0:
                self.color_bars.add_bar(lookup_table, 'contour')
                self.renderer.AddActor(self.color_bars.get_bar('contour'))

            mapper = vtk.vtkPolyDataMapper()
            mapper.SetInputConnection(contour.GetOutputPort())
            mapper.SetScalarRange((contour_values[0], contour_values[-1]))
            mapper.SetLookupTable(lookup_table)
            contour_actor = vtk.vtkActor()
            contour_actor.SetMapper(mapper)
            contour_actor.GetProperty().SetColor(1.0, 1.0, 1.0)
            self.renderer.AddActor(contour_actor)
            self.contour_set[strid] = contour_actor

    def remove_contour(self, region_id):
        strid = str(region_id)
        if strid in self.contour_set:
            self.renderer.RemoveActor(self.contour_set[strid])
            self.contour_set.pop(strid)
            if len(self.contour_set) == 0:
                self.renderer.RemoveActor(self.color_bars.get_bar('contour'))
                self.color_bars.remove_bar('contour')

    def contour_selected(self):
        for region_id in self.selected_regions:
            self.draw_contour(region_id)
        self.contour_selected_flag = True

    def contour_unselected(self):
        for region_id in self.selected_regions:
            self.remove_contour(region_id)
        self.contour_selected_flag = False

    def contour_value_changed(self, values):
        self.contour_values = values


    # --------------------------------------------------
    # centerline
    # --------------------------------------------------
    centerline_set = {}
    centerline_selected_flag = False
    centerline_points = {}
    centerline_curvatures = {}

    def calculate_centerline(self, region_id):
        region_grid = self.imaging_bounds_cut(region_id)
        points = processor.calculate_centerline_points(region_grid)
        curve_points, params = processor.poly_curve_fit(points)
        return curve_points, params


    def draw_centerline(self, region_id):
        strid = str(region_id)
        if strid not in self.centerline_set:
            points, params = self.calculate_centerline(region_id)

            vtk_points = vtk.vtkPoints()
            K = processor.calculate_curvature(points, params)
            scalars = vtk.vtkDoubleArray()
            scalars.SetNumberOfComponents(1)
            line = vtk.vtkCellArray()
            line.InsertNextCell(len(points))

            self.centerline_points[strid] = points
            self.centerline_curvatures[strid] = K

            for i in range(len(points)):
                vtk_points.InsertNextPoint(points[i])
                scalars.InsertNextValue(K[i])
                line.InsertCellPoint(i)

            poly = vtk.vtkPolyData()
            poly.SetPoints(vtk_points)
            poly.SetLines(line)
            poly.GetPointData().SetScalars(scalars)

            tube = vtk.vtkTubeFilter()
            tube.SetInputData(poly)
            tube.SetRadius(0.1)

            lookup_table = vtk.vtkLookupTable()
            lookup_table.SetTableRange(scalars.GetRange())
            lookup_table.SetNumberOfColors(256)
            lookup_table.SetHueRange(0.25, 0.45)
            lookup_table.SetValueRange(0.5, 0.3)
            lookup_table.Build()

            if len(self.centerline_set) == 0:
                self.color_bars.add_bar(lookup_table, 'centerline')
                self.renderer.AddActor(self.color_bars.get_bar('centerline'))

            mapper = vtk.vtkPolyDataMapper()
            mapper.SetInputConnection(tube.GetOutputPort())
            mapper.SetScalarRange(scalars.GetRange())
            mapper.SetLookupTable(lookup_table)
            actor = vtk.vtkActor()
            actor.SetMapper(mapper)
            actor.GetProperty().SetLineWidth(2)
            actor.GetProperty().SetColor((1.0, 0.0, 0.0))
            self.renderer.AddActor(actor)
            self.centerline_set[strid] = actor


    def remove_centerline(self, region_id):
        strid = str(region_id)
        if strid in self.centerline_set:
            self.renderer.RemoveActor(self.centerline_set[strid])
            self.centerline_set.pop(strid)
            self.centerline_points.pop(strid)
            self.centerline_curvatures.pop(strid)
            if len(self.centerline_set) == 0:
                self.renderer.RemoveActor(self.color_bars.get_bar('centerline'))
                self.color_bars.remove_bar('centerline')


    def centerline_selected(self):
        for region_id in self.selected_regions:
            self.draw_centerline(region_id)
        self.centerline_selected_flag = True


    def centerline_unselected(self):
        for region_id in self.selected_regions:
            self.remove_centerline(region_id)
        self.centerline_selected_flag = False



    # --------------------------------------------------
    # gradient arrow
    # --------------------------------------------------
    gradient_arrow_set = {}
    gradient_arrow_selected_flag = False

    def draw_gradient_arrow(self, region_id):
        strid = str(region_id)
        if strid not in self.gradient_arrow_set:
            region_grid = self.imaging_bounds_cut(region_id)
            G = np.gradient(region_grid.data)
            G = [-G[0], -G[1], -G[2]]
            points = vtk.vtkPoints()
            directions = vtk.vtkDoubleArray()
            directions.SetNumberOfComponents(3)

            bounds = region_grid.bounds
            spacing = region_grid.spacing
            for i in range(region_grid.data.shape[0]):
                for j in range(region_grid.data.shape[1]):
                    for k in range(region_grid.data.shape[2]):
                        if region_grid.data[i, j, k] > 1e-9:
                            points.InsertNextPoint(i * spacing[0] + bounds[0], j * spacing[1] + bounds[2],
                                                k * spacing[2] + bounds[4])
                            directions.InsertNextTuple3(G[0][i][j][k], G[1][i][j][k], G[2][i][j][k])

            poly_data = vtk.vtkPolyData()
            poly_data.SetPoints(points)
            poly_data.GetPointData().SetVectors(directions)

            mask = vtk.vtkMaskPoints()
            mask.SetInputData(poly_data)
            mask.SetOnRatio(5)
            mask.RandomModeOn()
            mask.Update()

            cone = vtk.vtkConeSource()
            cone.SetHeight(1.0)
            cone.SetRadius(0.2)
            cone.Update()

            glyph = vtk.vtkGlyph3D()
            glyph.SetInputData(mask.GetOutput())
            glyph.SetSourceData(cone.GetOutput())
            glyph.SetVectorModeToUseVector()
            glyph.SetScaleModeToDataScalingOff()
            glyph.SetScaleFactor(0.3)
            glyph.Update()

            mapper = vtk.vtkPolyDataMapper()
            mapper.SetInputConnection(glyph.GetOutputPort())
            gradient_actor = vtk.vtkActor()
            gradient_actor.SetMapper(mapper)
            gradient_actor.GetProperty().SetColor(0.0, 0.0, 1.0)
            self.renderer.AddActor(gradient_actor)
            self.gradient_arrow_set[strid] = gradient_actor

    def remove_gradient_arrow(self, region_id):
        strid = str(region_id)
        if strid in self.gradient_arrow_set:
            self.renderer.RemoveActor(self.gradient_arrow_set[strid])
            self.gradient_arrow_set.pop(strid)

    def gradient_arrow_selected(self):
        for region_id in self.selected_regions:
            self.draw_gradient_arrow(region_id)
        self.gradient_arrow_selected_flag = True

    def gradient_arrow_unselected(self):
        for region_id in self.selected_regions:
            self.remove_gradient_arrow(region_id)
        self.gradient_arrow_selected_flag = False


    # --------------------------------------------------
    # gradient streamline
    # --------------------------------------------------
    gradient_streamline_set = {}
    gradient_streamline_selected_flag = False

    def draw_gradient_streamline(self, region_id):
        strid = str(region_id)
        if strid not in self.gradient_streamline_set:
            region_grid = self.imaging_bounds_cut(region_id)

            G = -np.array(np.gradient(region_grid.data))
            G = G.transpose(1, 2, 3, 0)

            vrk_image = vtk.vtkImageData()
            vrk_image.SetDimensions(region_grid.data.shape[0], region_grid.data.shape[1], region_grid.data.shape[2])
            vrk_image.SetSpacing(region_grid.spacing[0], region_grid.spacing[1], region_grid.spacing[2])
            vrk_image.SetOrigin(region_grid.bounds[0], region_grid.bounds[2], region_grid.bounds[4])

            vtk_image = doppler_processor.build_image_grid(
                array_dict={'v': region_grid.data, 'G': G}, bounds=region_grid.bounds, spacing=region_grid.spacing
            )
            vtk_image.GetPointData().SetActiveVectors("G")
            vtk_image.GetPointData().SetActiveScalars("v")

            centerline_points = processor.calculate_centerline_points(region_grid)
            centerline_points, _ = processor.poly_curve_fit(centerline_points)

            points = vtk.vtkPoints()
            for i in range(len(centerline_points)):
                points.InsertNextPoint(centerline_points[i])
            line = vtk.vtkLineSource()
            line.SetPoints(points)
            tube = vtk.vtkTubeFilter()
            tube.SetInputConnection(line.GetOutputPort())
            tube.SetRadius(0.2)
            tube.SetNumberOfSides(20)
            tube.Update()

            streamers = vtk.vtkStreamTracer()
            runge_kutta4 = vtk.vtkRungeKutta4()

            streamers.SetIntegrator(runge_kutta4)
            streamers.SetInputData(vtk_image)
            streamers.SetSourceConnection(tube.GetOutputPort())

            streamers.SetMaximumPropagation(1000)
            streamers.SetMinimumIntegrationStep(0.01)
            streamers.SetMaximumIntegrationStep(0.5)
            streamers.SetInitialIntegrationStep(0.2)
            streamers.Update()

            tube2 = vtk.vtkTubeFilter()
            tube2.SetInputConnection(streamers.GetOutputPort())
            tube2.SetRadius(0.02)

            lookup_table = vtk.vtkLookupTable()
            lookup_table.SetHueRange(0.33, 0)
            lookup_table.SetAlphaRange(0.2, 1.0)
            lookup_table.Build()

            if len(self.gradient_streamline_set) == 0:
                self.color_bars.add_bar(lookup_table, 'gradient')
                self.renderer.AddActor(self.color_bars.get_bar('gradient'))

            mapper = vtk.vtkPolyDataMapper()
            mapper.SetInputConnection(tube2.GetOutputPort())
            mapper.SetScalarRange(vtk_image.GetPointData().GetScalars().GetRange())
            mapper.SetLookupTable(lookup_table)
            actor = vtk.vtkActor()
            actor.SetMapper(mapper)
            self.renderer.AddActor(actor)
            self.gradient_streamline_set[strid] = actor

    def remove_gradient_streamline(self, region_id):
        strid = str(region_id)
        if strid in self.gradient_streamline_set:
            self.renderer.RemoveActor(self.gradient_streamline_set[strid])
            self.gradient_streamline_set.pop(strid)
            if len(self.gradient_streamline_set) == 0:
                self.renderer.RemoveActor(self.color_bars.get_bar('gradient'))
                self.color_bars.remove_bar('gradient')


    def gradient_streamline_selected(self):
        for region_id in self.selected_regions:
            self.draw_gradient_streamline(region_id)
        self.gradient_streamline_selected_flag = True

    def gradient_streamline_unselected(self):
        for region_id in self.selected_regions:
            self.remove_gradient_streamline(region_id)
        self.gradient_streamline_selected_flag = False





    # --------------------------------------------------
    # heat flux
    # --------------------------------------------------
    heat_flux_set = {}
    heat_flux_selected_flag = False

    def draw_heat_flux(self, region_id):
        strid = str(region_id)
        if strid not in self.heat_flux_set:
            imaging_cut = self.imaging_bounds_cut(region_id)
            doppler_cut = self.doppler_bounds_cut(imaging_cut, self.frame.doppler)

            v_field, centerline = doppler_processor.get_velocity_field(imaging_cut, doppler_cut)
            H, H_field = doppler_processor.get_heat_flux_field(v_field, centerline)

            H_field = scipy.ndimage.gaussian_filter(H_field, sigma=1.1)
            H_field[H_field <= 0] = 1e-9

            heat_flux = doppler_cut.copy()
            heat_flux.data = H_field

            # to vtk file
            vtk_heat_flux = to_vtk_image(heat_flux)

            # color and opacity function
            range_v = vtk_heat_flux.GetScalarRange()
            log_v = [np.log10(range_v[0]), np.log10(range_v[1])]
            log_dis = log_v[1] - log_v[0]

            color_func = vtk.vtkColorTransferFunction()
            color_func.UsingLogScale()
            color_func.AddRGBPoint(2e-9, 0.0, 0.0, 0.5)
            color_func.AddRGBPoint(np.power(10, log_v[0] + 0.9 * log_dis), 0.0, 0.0, 1.0)
            color_func.AddRGBPoint(np.power(10, log_v[0] + 0.94 * log_dis), 0.0, 1.0, 0.0)
            color_func.AddRGBPoint(np.power(10, log_v[0] + 0.95 * log_dis), 1.0, 1.0, 0.0)
            color_func.AddRGBPoint(np.power(10, log_v[0] + 0.96 * log_dis), 1.0, 0.0, 0.0)

            opacity_func = vtk.vtkPiecewiseFunction()
            opacity_func.UseLogScaleOn()
            opacity_func.AddPoint(np.power(10, log_v[0] + 0.88 * log_dis), 0)
            opacity_func.AddPoint(range_v[1], 0.8)

            if len(self.heat_flux_set) == 0:
                self.color_bars.add_bar(color_func, 'heat flux')
                self.renderer.AddActor(self.color_bars.get_bar('heat flux'))

            # rendering
            volume_mapper = vtk.vtkGPUVolumeRayCastMapper()
            volume_mapper.SetInputData(vtk_heat_flux)
            volume_mapper.SetAutoAdjustSampleDistances(False)
            volume_mapper.SetSampleDistance(0.05)

            volume_property = vtk.vtkVolumeProperty()
            volume_property.SetColor(color_func)
            volume_property.SetScalarOpacity(opacity_func)
            volume_property.SetInterpolationTypeToLinear()
            volume_property.ShadeOn()
            volume_property.SetAmbient(0.3)
            volume_property.SetDiffuse(0.7)
            volume_property.SetSpecular(0.0)

            heat_flux_actor = vtk.vtkVolume()
            heat_flux_actor.SetMapper(volume_mapper)
            heat_flux_actor.SetProperty(volume_property)

            self.renderer.AddActor(heat_flux_actor)
            self.heat_flux_set[strid] = heat_flux_actor

    def remove_heat_flux(self, region_id):
        strid = str(region_id)
        if strid in self.heat_flux_set:
            self.renderer.RemoveActor(self.heat_flux_set[strid])
            self.heat_flux_set.pop(strid)
            if len(self.heat_flux_set) == 0:
                self.renderer.RemoveActor(self.color_bars.get_bar('heat flux'))
                self.color_bars.remove_bar('heat flux')

    def heat_flux_selected(self):
        for region_id in self.selected_regions:
            self.draw_heat_flux(region_id)
        self.heat_flux_selected_flag = True

    def heat_flux_unselected(self):
        for region_id in self.selected_regions:
            self.remove_heat_flux(region_id)
        self.heat_flux_selected_flag = False




    # --------------------------------------------------
    # velocity streamline
    # --------------------------------------------------
    velocity_streamline_set = {}
    velocity_streamline_selected_flag = False

    def draw_velocity_streamline(self, region_id):
        strid = str(region_id)
        if strid not in self.velocity_streamline_set:
            imaging_cut = self.imaging_bounds_cut(region_id)
            doppler_cut = self.doppler_bounds_cut(imaging_cut, self.frame.doppler)

            v_field, centerline = doppler_processor.get_velocity_field(imaging_cut, doppler_cut)

            v_value = np.sqrt(np.power(v_field[:,:,:,0], 2) + np.power(v_field[:,:,:,1], 2) + np.power(v_field[:,:,:,2], 2))


            velocity_image = doppler_processor.build_image_grid(
                array_dict={'v': v_field, 'v_value': v_value}, bounds=doppler_cut.bounds, spacing=doppler_cut.spacing
            )
            velocity_image.GetPointData().SetActiveVectors("v")
            velocity_image.GetPointData().SetActiveScalars("v_value")

            combine = vtk.vtkAppendPolyData()

            for i in range(len(centerline['center_points'])):
                if i % 4 == 0:
                    seeds = vtk.vtkPointSource()
                    seeds.SetCenter(centerline['center_points'][i])
                    seeds.SetRadius(1)
                    seeds.SetNumberOfPoints(100)
                    combine.AddInputConnection(seeds.GetOutputPort())
            combine.Update()

            clean = vtk.vtkCleanPolyData()
            clean.SetInputConnection(combine.GetOutputPort())
            clean.Update()

            streamers = vtk.vtkStreamTracer()
            runge_kutta4 = vtk.vtkRungeKutta4()

            streamers.SetIntegrator(runge_kutta4)
            streamers.SetInputData(velocity_image)
            streamers.SetSourceConnection(clean.GetOutputPort())

            streamers.SetMaximumPropagation(1000)
            streamers.SetMinimumIntegrationStep(0.01)
            streamers.SetMaximumIntegrationStep(0.5)
            streamers.SetInitialIntegrationStep(0.2)
            streamers.Update()

            stream_tube = vtk.vtkTubeFilter()
            stream_tube.SetInputConnection(streamers.GetOutputPort())
            stream_tube.SetRadius(0.01)
            stream_tube.SetNumberOfSides(12)

            lookup_table = vtk.vtkLookupTable()
            lookup_table.SetHueRange(0.33, 0.0)
            lookup_table.SetAlphaRange(0.0, 0.8)

            if len(self.velocity_streamline_set) == 0:
                self.color_bars.add_bar(lookup_table, 'velocity')
                self.renderer.AddActor(self.color_bars.get_bar('velocity'))

            mapper = vtk.vtkPolyDataMapper()
            mapper.SetInputConnection(stream_tube.GetOutputPort())
            mapper.SetScalarRange(velocity_image.GetPointData().GetScalars().GetRange())
            mapper.SetLookupTable(lookup_table)

            actor = vtk.vtkActor()
            actor.SetMapper(mapper)
            self.renderer.AddActor(actor)
            self.velocity_streamline_set[strid] = actor

    def remove_velocity_streamline(self, region_id):
        strid = str(region_id)
        if strid in self.velocity_streamline_set:
            self.renderer.RemoveActor(self.velocity_streamline_set[strid])
            self.velocity_streamline_set.pop(strid)
            if len(self.velocity_streamline_set) == 0:
                self.renderer.RemoveActor(self.color_bars.get_bar('velocity'))
                self.color_bars.remove_bar('velocity')

    def velocity_streamline_selected(self):
        for region_id in self.selected_regions:
            self.draw_velocity_streamline(region_id)
        self.velocity_streamline_selected_flag = True

    def velocity_streamline_unselected(self):
        for region_id in self.selected_regions:
            self.remove_velocity_streamline(region_id)
        self.velocity_streamline_selected_flag = False




    # ------------------------------------------------------------
    # ------------------------------------------------------------
    # ------------------------------------------------------------

    def refresh(self):
        self.interactor.GetRenderWindow().Render()

