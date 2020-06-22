# UQpy is distributed under the MIT license.
#
# Copyright (C) 2018  -- Michael D. Shields
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
# documentation files (the "Software"), to deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit
# persons to whom the Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the
# Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE
# WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NON-INFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
# COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
# OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import sys
import numpy as np
import scipy.stats as stats
from UQpy.RunModel import RunModel


def svd(matrix, rank=None, tol=None):
    """
    Compute the singular value decomposition (SVD) of a matrix.

    **Inputs:**

    * **matrix** (`ndarray`):
        Matrix of ``shape=(m, n)`` to perform the factorization using thin SVD

    * **tol** (`float`):
        Tolerance to estimate the rank of the matrix.

        Default: Machine precision

    * **iterations** (`rank`):
        Number of eigenvalues to keep.

        Default: None

    **Output/Returns:**

    * **u** (`ndarray`):
        Matrix of left eigenvectors of ``shape=(m, rank)``.

    * **v** (`ndarray`):
        Matrix of right eigenvectors of ``shape=(rank, n)``.

    * **s** (`ndarray`):
        Matrix of eigenvalues ``shape=(rank, rank)``.

    """
    ui, si, vi = np.linalg.svd(matrix, full_matrices=True, hermitian=False)
    si = np.diag(si)
    vi = vi.T
    if rank is None:
        if tol is not None:
            rank = np.linalg.matrix_rank(si, tol=tol)
        else:
            rank = np.linalg.matrix_rank(si)
        u = ui[:, :rank]
        s = si[:rank, :rank]
        v = vi[:, :rank]
    else:
        u = ui[:, :rank]
        s = si[:rank, :rank]
        v = vi[:, :rank]

    return u, s, v


def nearest_psd(input_matrix, iterations=10):
    """
    A function to compute the nearest positive semi-definite matrix of a given matrix [1]_.

    **References**

    .. [1] Houduo Qi, Defeng Sun, A Quadratically Convergent Newton Method for Computing the Nearest Correlation
        Matrix, SIAM Journal on Matrix Analysis and Applications 28(2):360-385, 2006.

    **Inputs:**

    * **input_matrix** (`ndarray`):
        Matrix to find the nearest PD.

    * **iterations** (`int`):
        Number of iterations to perform.

        Default: 10

    **Output/Returns:**

    * **psd_matrix** (`ndarray`):
        Nearest PSD matrix to input_matrix.

    """

    n = input_matrix.shape[0]
    w = np.identity(n)
    # w is the matrix used for the norm (assumed to be Identity matrix here)
    # the algorithm should work for any diagonal W
    delta_s = 0
    psd_matrix = input_matrix.copy()
    for k in range(iterations):

        r_k = psd_matrix - delta_s
        x_k = _get_ps(r_k, w=w)
        delta_s = x_k - r_k
        psd_matrix = _get_pu(x_k, w=w)

    return psd_matrix


def nearest_pd(input_matrix):
    """
    This is a method to find the nearest positive-definite matrix to input ([1]_, [2]_).

    **References**

    .. [1] N.J. Higham, "Computing a nearest symmetric positive semidefinite matrix" (1988),
        https://doi.org/10.1016/0024-3795(88)90223-6.

    .. [2] https://www.mathworks.com/matlabcentral/fileexchange/42885-nearestspd

    **Inputs:**

    * **input_matrix** (`ndarray`):
        Matrix to find the nearest PD.

    **Output/Returns:**

    * **pd_matrix** (`ndarray`):
        Nearest PD matrix to input_matrix.

    """

    b = (input_matrix + input_matrix.T) / 2
    _, s, v = np.linalg.svd(b)

    h = np.dot(v.T, np.dot(np.diag(s), v))

    a2 = (b + h) / 2

    pd_matrix = (a2 + a2.T) / 2

    if _is_pd(pd_matrix):
        return pd_matrix

    spacing = np.spacing(np.linalg.norm(pd_matrix))
    k = 1
    while not _is_pd(pd_matrix):
        min_eig = np.min(np.real(np.linalg.eigvals(pd_matrix)))
        pd_matrix += np.eye(input_matrix.shape[0]) * (-min_eig * k**2 + spacing)
        k += 1

    return pd_matrix


def _is_pd(input_matrix):
    try:
        _ = np.linalg.cholesky(input_matrix)
        return True
    except np.linalg.LinAlgError:
        return False

# TODO: Add Documentation (if public)
def run_parallel_python(model_script, model_object_name, sample, dict_kwargs=None):
    """
    Execute the python model in parallel
    :param sample: One sample point where the model has to be evaluated
    :return:
    """

    exec('from ' + model_script[:-3] + ' import ' + model_object_name)
    # if kwargs is not None:
    #     par_res = eval(model_object_name + '(sample, kwargs)')
    # else:
    if dict_kwargs is None:
        par_res = eval(model_object_name + '(sample)')
    else:
        par_res = eval(model_object_name + '(sample, **dict_kwargs)')
    # par_res = parallel_output
    # if self.model_is_class:
    #     par_res = parallel_output.qoi
    # else:
    #     par_res = parallel_output

    return par_res

# TODO: Check if still in use - Add Documentation (if public)
# def compute_Voronoi_volume(vertices):
#
#     from scipy.spatial import Delaunay
#
#     d = Delaunay(vertices)
#     d_vol = np.zeros(np.size(vertices, 0))
#     for i in range(d.nsimplex):
#         d_verts = vertices[d.simplices[i]]
#         d_vol[i] = compute_Delaunay_volume(d_verts)
#
#     volume = np.sum(d_vol)
#     return volume

def gradient(runmodel_object=None, point=None, order='first', df_step=None):
    """
    This method estimates the gradients (1st, 2nd, mixed) of a function using a finite difference scheme in the
    standard normal space. First order gradients are calculated using central finite differences.

    **Inputs:**

    * **runmodel_object** (``RunModel`` object or a `callable` ):
        The numerical model. It should be of type `RunModel` (see ``RunModel`` class) or a `callable`.

    * **point** (`ndarray`):
        The point to evaluate the gradient with shape ``point``.shape=(1, dimension)

    * **order** (`str`):
        Order of the gradient. Available options: 'first', 'second', 'mixed'.

        Default: 'First'.

    * **df_step** (`float`):
        Finite difference step.

        Default: 0.001.

    **Output/Returns:**

    * **du_dj** (`ndarray`):
        Vector of first-order gradients (if order = 'first').

    * **d2u_dj** (`ndarray`):
        Vector of second-order gradients (if order = 'second').

    * **d2u_dij** (`ndarray`):
        Vector of mixed gradients (if order = 'mixed').

    """
    point = np.atleast_2d(point)

    dimension = point.shape[1]

    if df_step is None:
        df_step = [0.001] * dimension
    elif isinstance(df_step, float):
        df_step = [df_step] * dimension
    elif isinstance(df_step, list):
        if len(df_step) == 1:
            df_step = [df_step[0]] * dimension

    if not callable(runmodel_object) and not isinstance(runmodel_object, RunModel):
        raise RuntimeError('A RunModel object or callable function must be provided as model.')

    def func(m):
        def func_eval(x):
            if isinstance(m, RunModel):
                m.run(samples=x, append_samples=False)
                return np.array(m.qoi_list).flatten()
            else:
                return m(x).flatten()

        return func_eval

    f_eval = func(m=runmodel_object)

    if order.lower() == 'first':
        du_dj = np.zeros([point.shape[0], dimension])

        for ii in range(dimension):
            eps_i = df_step[ii]
            u_i1_j = point.copy()
            u_i1_j[:, ii] = u_i1_j[:, ii] + eps_i
            u_1i_j = point.copy()
            u_1i_j[:, ii] = u_1i_j[:, ii] - eps_i

            qoi_plus = f_eval(u_i1_j)
            qoi_minus = f_eval(u_1i_j)

            du_dj[:, ii] = ((qoi_plus - qoi_minus) / (2 * eps_i))

        return du_dj

    elif order.lower() == 'second':
        # print('Calculating second order derivatives..')
        d2u_dj = np.zeros([point.shape[0], dimension])
        for ii in range(dimension):
            u_i1_j = point.copy()
            u_i1_j[:, ii] = u_i1_j[:, ii] + df_step[ii]
            u_1i_j = point.copy()
            u_1i_j[:, ii] = u_1i_j[:, ii] - df_step[ii]

            qoi_plus = f_eval(u_i1_j)
            qoi = f_eval(point)
            qoi_minus = f_eval(u_1i_j)

            d2u_dj[:, ii] = ((qoi_plus - 2 * qoi + qoi_minus) / (df_step[ii] * df_step[ii]))

        return d2u_dj

    elif order.lower() == 'mixed':

        import itertools
        range_ = list(range(dimension))
        d2u_dij = np.zeros([point.shape[0], int(dimension * (dimension - 1) / 2)])
        count = 0
        for i in itertools.combinations(range_, 2):
            u_i1_j1 = point.copy()
            u_i1_1j = point.copy()
            u_1i_j1 = point.copy()
            u_1i_1j = point.copy()

            eps_i1_0 = df_step[i[0]]
            eps_i1_1 = df_step[i[1]]

            u_i1_j1[:, i[0]] += eps_i1_0
            u_i1_j1[:, i[1]] += eps_i1_1

            u_i1_1j[:, i[0]] += eps_i1_0
            u_i1_1j[:, i[1]] -= eps_i1_1

            u_1i_j1[:, i[0]] -= eps_i1_0
            u_1i_j1[:, i[1]] += eps_i1_1

            u_1i_1j[:, i[0]] -= eps_i1_0
            u_1i_1j[:, i[1]] -= eps_i1_1

            print('hi')
            qoi_0 = f_eval(u_i1_j1)
            qoi_1 = f_eval(u_i1_1j)
            qoi_2 = f_eval(u_1i_j1)
            qoi_3 = f_eval(u_1i_1j)

            d2u_dij[:, count] = ((qoi_0 + qoi_3 - qoi_1 - qoi_2) / (4 * eps_i1_0 * eps_i1_1))

            count += 1
        return d2u_dij


def voronoi_unit_hypercube(samples):
    """
    This function mirror the samples in both low and high directions for each dimension and estimate the voronoi
    regions for each sample.

    **Inputs:**

    * **samples** (`ndarray`):
        Coordinates of points to construct a convex hull from ``samples.shape=(1, dimension)

    **Output/Returns:**

    * **vor** (`scipy.spatial.Voronoi` object):
        Voronoi diagram in N dimension.
    """

    from scipy.spatial import Voronoi

    # Mirror the samples in both low and high directions for each dimension
    samples_center = samples
    dimension = samples.shape[1]
    for i in range(dimension):
        samples_del = np.delete(samples_center, i, 1)
        if i == 0:
            points_temp1 = np.hstack([np.atleast_2d(-samples_center[:,i]).T, samples_del])
            points_temp2 = np.hstack([np.atleast_2d(2-samples_center[:,i]).T, samples_del])
        elif i == dimension-1:
            points_temp1 = np.hstack([samples_del, np.atleast_2d(-samples_center[:, i]).T])
            points_temp2 = np.hstack([samples_del, np.atleast_2d(2 - samples_center[:, i]).T])
        else:
            points_temp1 = np.hstack([samples_del[:,:i], np.atleast_2d(-samples_center[:, i]).T, samples_del[:,i:]])
            points_temp2 = np.hstack([samples_del[:,:i], np.atleast_2d(2 - samples_center[:, i]).T, samples_del[:,i:]])
        samples = np.append(samples, points_temp1, axis=0)
        samples = np.append(samples, points_temp2, axis=0)

    vor = Voronoi(samples, incremental=True)
    vor.regions: list = vor.regions
    vor.point_region: list = vor.point_region

    regions = [None]*samples_center.shape[0]

    for i in range(samples_center.shape[0]):
        regions[i] = vor.regions[vor.point_region[i]]

    vor.bounded_points = samples_center
    vor.bounded_regions = regions

    return vor

# TODO: Check if still in use - Add Documentation (if public)
def compute_voronoi_centroid_volume(vertices):
    """
    This function computes the centroid and volume of voronoi cells created using vertices.

    **Inputs:**

    * **vertices** (`ndarray`):
        Coordinates of points to construct a voronoi diagram.

    **Output/Returns:**

    * **centroid** (`numpy.ndarray`):
        Centroid of Voronoi cells.

    * **volume** (`numpy.ndarray`):
        Volume of Voronoi cells.
    """

    from scipy.spatial import Delaunay, ConvexHull

    tess = Delaunay(vertices)
    tess.nsimplex: int = tess.nsimplex
    tess.simplices: np.ndarray = tess.simplices
    dimension = np.shape(vertices)[1]

    w = np.zeros((tess.nsimplex, 1))
    cent = np.zeros((tess.nsimplex, dimension))
    for i in range(tess.nsimplex):
        ch = ConvexHull(tess.points[tess.simplices[i]])
        ch.volume: float = ch.volume
        w[i] = ch.volume
        cent[i, :] = np.mean(tess.points[tess.simplices[i]], axis=0)

    volume = np.sum(w)
    centroid = np.matmul(np.divide(w, volume).T, cent)

    return centroid, volume

# TODO: Check if still in use - Add Documentation (if public)
def compute_delaunay_centroid_volume(vertices):
    """
    This function computes the centroid and volume of Delaunay triangulation created using vertices.

    **Inputs:**

    * **vertices** (`ndarray`):
        Coordinates of points to construct a Convex Hull.

    **Output/Returns:**

    * **centroid** (`numpy.ndarray`):
        Centroid of Voronoi cells.

    * **volume** (`numpy.ndarray`):
        Volume of Voronoi cells.
    """

    from scipy.spatial import ConvexHull

    ch = ConvexHull(vertices)
    volume = ch.volume
    ch.volume: float = ch.volume
    centroid = np.mean(vertices, axis=0)

    return centroid, volume


def _bi_variate_normal_pdf(x1, x2, rho):
   return (1 / (2 * np.pi * np.sqrt(1-rho**2)) *
           np.exp(-1/(2*(1-rho**2)) *
                  (x1**2 - 2 * rho * x1 * x2 + x2**2)))


# TODO: Add Documentation (if public)
def estimate_psd(samples, nt, t):

    """
        Description: A function to estimate the Power Spectrum of a stochastic process given an ensemble of samples

        Input:
            :param samples: Samples of the stochastic process
            :param nt: Number of time discretisations in the time domain
            :param t: Total simulation time

        Output:
            :return: Power Spectrum
            :rtype: ndarray

    """

    sample_size = nt
    sample_max_time = t
    dt = t / (nt - 1)
    x_w = np.fft.fft(samples, sample_size, axis=1)
    x_w = x_w[:, 0: int(sample_size / 2)]
    m_ps = np.mean(np.absolute(x_w) ** 2 * sample_max_time / sample_size ** 2, axis=0)
    num = int(t / (2 * dt))

    return np.linspace(0, (1 / (2 * dt) - 1 / t), num), m_ps

def _get_a_plus(a):
    eig_val, eig_vec = np.linalg.eig(a)
    q = np.array(eig_vec)
    x_diagonal = np.array(np.diag(np.maximum(eig_val, 0)))

    return q * x_diagonal * q.T


def _get_ps(a, w=None):
    w05 = np.array(w ** .5)

    return w05.I * _get_a_plus(w05 * a * w05) * w05.I


def _get_pu(a, w=None):
    a_ret = np.array(a.copy())
    a_ret[w > 0] = np.array(w)[w > 0]
    return np.array(a_ret)


# TODO: Check if still in use - Add Documentation (if public)
def check_arguments(argv, min_num_matrix, ortho):
    
    """
    Check input arguments for consistency.

    Check the input matrices for consistency given the minimum number of matrices (min_num_matrix) 
    and the boolean varible (ortho) to test the orthogonality.

    **Input:**

    :param argv: Matrices to be tested.
    :type  argv: list of arguments

    :param min_num_matrix: Minimum number of matrices.
    :type  min_num_matrix: int
    
    :param ortho: boolean varible to test the orthogonality.
    :type  ortho: bool

    **Output/Returns:**

    :param inputs: Return the input matrices.
    :type  inputs: numpy array

    :param nargs: Number of matrices.
    :type  nargs: numpy array
    """
        
    # Check the minimum number of matrices involved in the operations
    if type(min_num_matrix) != int:
        raise ValueError('The minimum number of matrices MUST be an integer number!')
    elif min_num_matrix < 1:
        raise ValueError('Number of arguments MUST be larger than or equal to one!')

    # Check if the variable controlling the orthogonalization is boolean
    if type(ortho) != bool:
        raise ValueError('The last argument MUST be a boolean!')

    nargv = len(argv)

    # If the number of provided inputs are zero exit the code
    if nargv == 0:
        raise ValueError('Missing input arguments!')

    # Else if the number of arguments is equal to 1 
    elif nargv == 1:

        # Check if the number of expected matrices are higher than or equal to 2
        args = argv[0]
        nargs = len(args)
      
        if np.shape(args)[0] == 1 or len(np.shape(args)) == 2:
            nargs = 1
        # if it is lower than two exit the code, otherwise store them in a list
        if nargs < min_num_matrix:
            raise ValueError('The number of points must be higher than:', min_num_matrix)

        else:
            inputs = []
            if nargs == 1:
                inputs = [args]
            else:

                # Loop over all elements
                for i in range(nargs):                  
                    # Verify the type of the input variables and store in a list
                    inputs.append(test_type(args[i], ortho))

    else:

        nargs = nargv
        # Each argument MUST be a matrix
        inputs = []
        for i in range(nargv):
            # Verify the type of the input variables and store in a list
            inputs.append(test_type(argv[i], ortho))

    return inputs, nargs

# TODO: Check if still in use - Add Documentation (if public)
def test_type(X, ortho):
    
    """
    Test the datatype of X.

    Check if the datatype of the matrix X is consistent.

    **Input:**

    :param X: Matrices to be tested.
    :type  X: list or numpy array
    
    :param ortho: boolean varible to test the orthogonality.
    :type  ortho: bool

    **Output/Returns:**

    :param Y: Tested and adjusted matrices.
    :type  Y: numpy array
    """
        
    if not isinstance(X, (list, np.ndarray)):
        raise TypeError('Elements of input arguments should be provided either as list or array')
    elif type(X) == list:
        Y = np.array(X)
    else:
        Y = X

    if ortho:
        Ytest = np.dot(Y.T, Y)
        if not np.array_equal(Ytest, np.identity(np.shape(Ytest)[0])):
            Y, unused = np.linalg.qr(Y)

    return Y


# TODO: Check if still in use - Add Documentation (if public)
def _nn_coord(x, k):
    
    """
    Select k elements close to x.

    Select k elements close to x to be used to construct a sparse kernel
    matrix to be used in the diffusion maps.

    **Input:**

    :param x: Matrices to be tested.
    :type  x: list or numpy array
    
    :param k: Number of points close to x.
    :type  k: int

    **Output/Returns:**

    :param idx: Indices of the closer points.
    :type  idx: int
    """
        
    if isinstance(x, list):
        x = np.array(x)
        
    dim = np.shape(x)
    
    if len(dim) is not 1:
        raise ValueError('k MUST be a vector.')
    
    if not isinstance(k, int):
        raise TypeError('k MUST be integer.')

    if k<1:
        raise ValueError('k MUST be larger than or equal to 1.')
    
    #idx = x.argsort()[::-1][:k]
    idx = x.argsort()[:len(x)-k]
    #idx = idx[0:k]
    #idx = idx[k+1:]
    return idx

# TODO: Add Documentation (if public)
def correlation_distortion(dist_object, rho):
    if rho == 1.0:
        rho = 0.999
    n = 1024
    zmax = 8
    zmin = -zmax
    points, weights = np.polynomial.legendre.leggauss(n)
    points = - (0.5 * (points + 1) * (zmax - zmin) + zmin)
    weights = weights * (0.5 * (zmax - zmin))

    xi = np.tile(points, [n, 1])
    xi = xi.flatten(order='F')
    eta = np.tile(points, n)

    first = np.tile(weights, n)
    first = np.reshape(first, [n, n])
    second = np.transpose(first)

    weights2d = first * second
    w2d = weights2d.flatten()
    tmp_f_xi = dist_object.icdf(stats.norm.cdf(xi[:, np.newaxis]))
    tmp_f_eta = dist_object.icdf(stats.norm.cdf(eta[:, np.newaxis]))
    coef = tmp_f_xi * tmp_f_eta * w2d
    phi2 = _bi_variate_normal_pdf(xi, eta, rho)
    rho_non = np.sum(coef * phi2)
    rho_non = (rho_non - dist_object.moments(moments2return='m') ** 2) / dist_object.moments(moments2return='v')
    return rho_non
