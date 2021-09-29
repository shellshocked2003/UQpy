import numpy as np
from numpy.linalg import svd

from UQpy.dimension_reduction.distances.grassmanian.baseclass.RiemannianDistance import RiemannianDistance


class FubiniStudy(RiemannianDistance):

    def compute_distance(self, point1, point2):
        point1, point2 = RiemannianDistance.check_points(point1, point2)

        l = min(np.shape(point1))
        k = min(np.shape(point2))

        if l != k:
            raise NotImplementedError('UQpy: distance not implemented for manifolds with distinct dimensions.')

        r = np.dot(point1.T, point2)
        (ui, si, vi) = svd(r, k)

        index = np.where(si > 1)
        si[index] = 1.0
        theta = np.arccos(np.diag(si))
        cos_t = np.cos(theta)
        d = np.arccos(np.prod(cos_t))

        return d