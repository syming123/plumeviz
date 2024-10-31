# ================================================================================
# A new version minimap which can allow users to select region of interest.
# ================================================================================

from PyQt6.QtWidgets import QWidget, QVBoxLayout
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
import vtk
import numpy as np
import time, os

from common.entity import UniformGrid, DataFrame
from visualization.gui.signal_group import signals
from visualization.core import processor


class MinimapCamera(vtk.vtkInteractorStyleTrackballCamera):
    callback = None
    def __init__(self):
        super().__init__()

        self.AddObserver(vtk.vtkCommand.LeftButtonPressEvent, self.on_left_button_press)
        self.AddObserver(vtk.vtkCommand.RightButtonPressEvent, self.removed_events)


    def on_left_button_press(self, obj, event):
        pixel = self.GetInteractor().GetEventPosition()
        self.GetInteractor().GetPicker().Pick(pixel[0], pixel[1], 0, self.GetInteractor().GetRenderWindow().GetRenderers().GetFirstRenderer())
        self.callback(self.GetInteractor().GetPicker().GetPickPosition())

    def removed_events(self, obj, event):
        ...

    def set_callback(self, callback):
        self.callback = callback



class Minimap(QWidget):
    regions = []
    marks = np.ndarray
    mark_slice = np.ndarray
    seafloor = UniformGrid()
    frame = DataFrame()
    frame_index = 0
    region_actors = {}
    plane_actors = {}
    selected_region = []
    bounds = [-1000, 1000, -1000, 1000, -1000, 1000]

    def __init__(self):
        super().__init__()

        self.renderer = vtk.vtkRenderer()
        self.renderer.SetBackground(0.0, 0.16, 0.30)
        self.renderer.SetBackground2(0.0, 0.08, 0.16)
        self.renderer.SetGradientBackground(True)
        self.renderer.ResetCamera()
        camera = MinimapCamera()
        camera.SetDefaultRenderer(self.renderer)
        camera.set_callback(self.pick_region)
        self.interactor = QVTKRenderWindowInteractor()
        self.interactor.GetRenderWindow().AddRenderer(self.renderer)
        self.interactor.SetInteractorStyle(camera)
        self.interactor.Initialize()

        self.renderer.GetActiveCamera().ParallelProjectionOn()
        camera_pos = self.renderer.GetActiveCamera().GetPosition()
        self.renderer.GetActiveCamera().SetPosition(camera_pos[0], camera_pos[1], 200)
        self.renderer.GetActiveCamera().SetParallelScale(35)

        layout = QVBoxLayout()
        self.setLayout(layout)
        layout.addWidget(self.interactor)

        self.selected_color = vtk.vtkColorTransferFunction()
        self.selected_color.AddRGBPoint(0, 1.0, 0.0, 0.0)
        self.selected_color.AddRGBPoint(1, 1.0, 0.0, 0.0)
        self.unselected_color = vtk.vtkColorTransferFunction()
        self.unselected_color.AddRGBPoint(0, 0.5, 0.5, 0.5)
        self.unselected_color.AddRGBPoint(1, 0.5, 0.5, 0.5)

        plane = vtk.vtkPlaneSource()
        plane.SetOrigin(0, 0, 0)
        plane.SetPoint1(-1.0, 0.0, 0.0)
        plane.SetPoint2(0.0, 1.0, 0.0)
        plane.SetNormal(0.0, 0.0, 1.0)

        texture_reader = vtk.vtkPNGReader()
        texture_reader.SetFileName('../res/icons/north.png')
        texture = vtk.vtkTexture()
        texture.SetInputConnection(texture_reader.GetOutputPort())
        texture_map = vtk.vtkTextureMapToPlane()
        texture_map.SetInputConnection(plane.GetOutputPort())

        plane_mapper = vtk.vtkPolyDataMapper()
        plane_mapper.SetInputConnection(texture_map.GetOutputPort())
        plane_actor = vtk.vtkActor()
        plane_actor.SetMapper(plane_mapper)
        plane_actor.SetTexture(texture)
        plane_actor.RotateZ(-90)

        self.ori_widget = vtk.vtkOrientationMarkerWidget()
        self.ori_widget.SetOutlineColor(1.0, 1.0, 1.0)
        self.ori_widget.SetOrientationMarker(plane_actor)
        self.ori_widget.SetInteractor(self.interactor)
        self.ori_widget.SetViewport(0.8, 0.8, 0.95, 0.95)
        self.ori_widget.SetEnabled(1)
        self.ori_widget.InteractiveOff()

        self.seafloor_actor = None

        # global slots
        signals.bounds_changed.connect(self.on_bounds_changed)
        signals.seabed_loaded.connect(self.load_seafloor)
        signals.load_region.connect(self.load_region)
        signals.load_frame.connect(self.load_frame)
        signals.camera_rotated.connect(self.rotate)



    def on_bounds_changed(self, bounds):
        self.bounds = bounds
        self.draw_seafloor()
        self.draw_frame()


    def load_seafloor(self, seafloor: UniformGrid):
        self.seafloor = seafloor

    def draw_seafloor(self):
        vtk_image = processor.to_vtk_image2d(processor.cut_uniform(self.seafloor, self.bounds))
        data_range = vtk_image.GetScalarRange()

        contour = vtk.vtkContourFilter()
        contour.SetInputData(vtk_image)
        contour.GenerateValues(8, data_range[0], data_range[1])
        contour.Update()

        color_func = vtk.vtkColorTransferFunction()
        color_func.AddRGBPoint(data_range[0],0.0, 0.0, 1.0)
        color_func.AddRGBPoint(data_range[1], 0.6, 0.6, 1.0)

        contour_mapper = vtk.vtkPolyDataMapper()
        contour_mapper.SetInputConnection(contour.GetOutputPort())
        contour_mapper.SetLookupTable(color_func)
        self.renderer.RemoveActor(self.seafloor_actor)
        if self.seafloor_actor is not None:
            self.renderer.RemoveActor(self.seafloor_actor)
        self.seafloor_actor = vtk.vtkActor()
        self.seafloor_actor.SetMapper(contour_mapper)
        self.renderer.AddActor(self.seafloor_actor)


    def load_region(self, regions: list, marks: np.ndarray):
        self.regions = regions
        self.marks = marks


    def load_frame(self, frame: DataFrame, group_index: int, frame_index: int, group_size: int):
        self.frame = frame
        self.frame_index = frame_index
        self.draw_frame()


    def draw_frame(self):
        imaging = self.frame.imaging.copy()

        # remove all plume regions and labels
        for act in self.region_actors.values():
            self.renderer.RemoveActor(act)
        for act in self.plane_actors.values():
            self.renderer.RemoveActor(act)

        mark = self.marks[self.frame_index]
        self.mark_slice = np.max(mark, axis=2)
        for region in self.regions:
            region_grid = UniformGrid()
            region_grid.bounds = region.bounds[2:]
            for i in range(6):
                region_grid.bounds[i] = region_grid.bounds[i] * imaging.spacing[int(i/2)] + imaging.bounds[int(i/2) * 2]

            if (region_grid.bounds[0] > self.bounds[1] or region_grid.bounds[1] < self.bounds[0]
                    or region_grid.bounds[2] > self.bounds[3] or region_grid.bounds[3] < self.bounds[2]):
                continue

            region_grid.spacing = imaging.spacing
            region_grid.dim = 3

            region_marks = mark[region.bounds[2]:region.bounds[3], region.bounds[4]:region.bounds[5], region.bounds[6]:region.bounds[7]]
            region_marks[region_marks != region.id] = 0
            region_grid.data = region_marks

            vtk_region = processor.to_vtk_image3d(region_grid)
            contour = vtk.vtkContourFilter()
            contour.SetInputData(vtk_region)
            contour.SetValue(0, region.id)

            mapper = vtk.vtkPolyDataMapper()
            mapper.SetInputConnection(contour.GetOutputPort())
            if region.id not in self.selected_region:
                mapper.SetLookupTable(self.unselected_color)
            else:
                mapper.SetLookupTable(self.selected_color)
            region_actor = vtk.vtkActor()
            region_actor.SetMapper(mapper)


            center = [(region_grid.bounds[0] + region_grid.bounds[1])/2, (region_grid.bounds[2] + region_grid.bounds[3])/2]
            plane = vtk.vtkPlaneSource()
            plane.SetOrigin(-2.5, -5, 100.0)
            plane.SetPoint1(-2.5, 5, 100.0)
            plane.SetPoint2(2.5, -5, 100.0)
            plane.SetNormal(0.0, 0.0, 1.0)

            texture_reader = vtk.vtkPNGReader()
            texture_reader.SetFileName('../res/icons/locate2.png')
            texture = vtk.vtkTexture()
            texture.SetInputConnection(texture_reader.GetOutputPort())
            texture_map = vtk.vtkTextureMapToPlane()
            texture_map.SetInputConnection(plane.GetOutputPort())

            plane_mapper = vtk.vtkPolyDataMapper()
            plane_mapper.SetInputConnection(texture_map.GetOutputPort())
            plane_actor = vtk.vtkActor()
            plane_actor.SetMapper(plane_mapper)
            plane_actor.SetTexture(texture)

            trans = vtk.vtkTransform()
            trans.Translate(center[0], center[1], 0)
            plane_actor.SetUserTransform(trans)

            self.region_actors[str(region.id)] = region_actor
            self.plane_actors[str(region.id)] = plane_actor
            self.renderer.AddActor(region_actor)
            self.renderer.AddActor(plane_actor)
        self.refresh()


    def rotate(self, angle):
        self.renderer.GetActiveCamera().Roll(angle)
        for act in self.plane_actors.values():
            trans = act.GetUserTransform()
            trans.RotateZ(-angle)
        self.refresh()


    def pick_region(self, pos):
        eps = 1e-6
        if pos[0]**2 + pos[1]**2 + pos[2]**2 < eps:
            return
        [x, y] = pos[:2]
        x = (x - self.frame.imaging.bounds[0])/self.frame.imaging.spacing[0]
        y = (y - self.frame.imaging.bounds[2])/self.frame.imaging.spacing[1]
        select_id = self.mark_slice[int(x)][int(y)]

        if str(select_id) not in self.region_actors:
            return
        if select_id not in self.selected_region:
            self.selected_region.append(select_id)
            signals.add_region.emit(select_id)
            self.region_actors[str(select_id)].GetMapper().SetLookupTable(self.selected_color)
            self.refresh()
        else:
            self.selected_region.remove(select_id)
            signals.remove_region.emit(select_id)
            self.region_actors[str(select_id)].GetMapper().SetLookupTable(self.unselected_color)
            self.refresh()



    def refresh(self):
        self.interactor.GetRenderWindow().Render()


    def closeEvent(self, a0):
        super().closeEvent(a0)
        self.interactor.Finalize()
