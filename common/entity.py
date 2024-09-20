import numpy as np


class Region:
    def __init__(self):
        self.id = 0
        self.count = 0
        self.bounds = [0, 0, 0, 0, 0, 0, 0, 0]


class UniformGrid:
    def __init__(self):
        self.data = np.array([])
        self.bounds = []
        self.spacing = []
        self.dim = 0

    def copy(self):
        cp = UniformGrid()
        cp.data = self.data.copy()
        cp.bounds = self.bounds.copy()
        cp.spacing = self.spacing.copy()
        cp.dim = self.dim
        return cp


class DataFrame:
    def __init__(self):
        self.id = -1
        self.time_str = ''
        self.imaging = UniformGrid()
        self.doppler = UniformGrid()
        self.diffuse = UniformGrid()

    def copy(self):
        cp = DataFrame()
        cp.id = self.id
        cp.time_str = self.time_str
        cp.imaging = self.imaging.copy()
        cp.doppler = self.doppler.copy()
        cp.diffuse = self.diffuse.copy()
        return cp
