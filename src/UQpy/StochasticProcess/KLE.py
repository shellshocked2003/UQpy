import numpy as np
from scipy.linalg import sqrtm

from UQpy.Utilities import *


########################################################################################################################
########################################################################################################################
#                                       Karhunen-Loeve Expansion
########################################################################################################################

class KLE:
    """
    A class to simulate stochastic processes from a given auto-correlation function based on the Karhunen-Loeve
    Expansion

    **Input:**

    * **nsamples** (`int`):
        Number of samples of the stochastic process to be simulated.

        The ``run`` method is automatically called if `nsamples` is provided. If `nsamples` is not provided, then the
        ``KLE`` object is created but samples are not generated.

    * **correlation_function** (`list or numpy.ndarray`):
        The correlation function of the stochastic process of size (`number_time_intervals`, `number_time_intervals`)

    * **time_interval** (`float`):
        The length of time discretization.

    * **threshold** (`int`):
        The threshold number of eigenvalues to be used in the expansion.

    * **random_state** (None or `int` or ``numpy.random.RandomState`` object):
        Random seed used to initialize the pseudo-random number generator. Default is None.

        If an integer is provided, this sets the seed for an object of ``numpy.random.RandomState``. Otherwise, the
        object itself can be passed directly.

    * **verbose** (Boolean):
        A boolean declaring whether to write text to the terminal.

    **Attributes:**

    * **samples** (`ndarray`):
        Array of generated samples.

    * **xi** (`ndarray`):
        The independent gaussian random variables used in the expansion.

    **Methods**
    """

    # TODO: Test this for non-stationary processes.

    def __init__(self, nsamples, correlation_function, time_interval, threshold=None, random_state=None, verbose=False):
        self.correlation_function = correlation_function
        self.time_interval = time_interval
        if threshold:
            self.number_eigen_values = threshold
        else:
            self.number_eigen_values = len(self.correlation_function[0])

        self.random_state = random_state
        if isinstance(self.random_state, int):
            np.random.seed(self.random_state)
        elif not isinstance(self.random_state, (type(None), np.random.RandomState)):
            raise TypeError('UQpy: random_state must be None, an int or an np.random.RandomState object.')

        self.verbose = verbose
        self.nsamples = nsamples

        self.samples = None
        self.xi = None

        if self.nsamples is not None:
            self.run(nsamples=self.nsamples)

    def _simulate(self, xi):
        lam, phi = np.linalg.eig(self.correlation_function)
        lam = lam[:self.number_eigen_values]
        lam = np.diag(lam)
        lam = lam.astype(np.float64)
        samples = np.dot(phi[:, :self.number_eigen_values], np.dot(sqrtm(lam), xi))
        samples = np.real(samples)
        samples = samples.T
        samples = samples[:, np.newaxis]
        return samples

    def run(self, nsamples):
        """
        Execute the random sampling in the ``KLE`` class.

        The ``run`` method is the function that performs random sampling in the ``KLE`` class. If `nsamples` is
        provided when the ``KLE`` object is defined, the ``run`` method is automatically called. The user may also call
        the ``run`` method directly to generate samples. The ``run`` method of the ``KLE`` class can be invoked many
        times and each time the generated samples are appended to the existing samples.

        ** Input:**

        * **nsamples** (`int`):
            Number of samples of the stochastic process to be simulated.

            If the ``run`` method is invoked multiple times, the newly generated samples will be appended to the
            existing samples.

        **Output/Returns:**

            The ``run`` method has no returns, although it creates and/or appends the `samples` attribute of the
            ``KLE`` class.

        """

        if nsamples is None:
            raise ValueError('UQpy: Stochastic Process: Number of samples must be defined.')
        if not isinstance(nsamples, int):
            raise ValueError('UQpy: Stochastic Process: nsamples should be an integer.')

        if self.verbose:
            print('UQpy: Stochastic Process: Running Karhunen Loeve Expansion.')

        if self.verbose:
            print('UQpy: Stochastic Process: Starting simulation of Stochastic Processes.')
        xi = np.random.normal(size=(self.number_eigen_values, self.nsamples))
        samples = self._simulate(xi)

        if self.samples is None:
            self.samples = samples
            self.xi = xi
        else:
            self.samples = np.concatenate((self.samples, samples), axis=0)
            self.xi = np.concatenate((self.xi, xi), axis=0)

        if self.verbose:
            print('UQpy: Stochastic Process: Karhunen-Loeve Expansion Complete.')


class KLE_Two_Dimension:

    def __init__(self, nsamples, correlation_function, time_interval, thresholds=None):
        self.nsamples = nsamples
        self.correlation_function = correlation_function
        self.time_interval = time_interval
        self.thresholds = thresholds
        self.samples = 0
        self.xi = None

        self._precompute_one_dimensional_correlation_function()

        if self.nsamples is not None:
            self.run(nsamples=self.nsamples)

        self.samples = np.reshape(self.samples,
                                  [self.samples.shape[0], 1, self.samples.shape[1], self.samples.shape[2]])

    def _precompute_one_dimensional_correlation_function(self):
        self.quasi_correlation_function = np.diagonal(self.correlation_function, axis1=0, axis2=1)
        self.quasi_correlation_function = np.einsum('ij... -> ...ij', self.quasi_correlation_function)
        self.w, self.v = np.linalg.eig(self.quasi_correlation_function)
        if np.norm(np.imag(self.w)) > 0:
            print('Complex in the eigenvalues, check the positive definiteness')
        self.w = np.real(self.w)
        self.v = np.real(self.v)
        if self.thresholds is not None:
            self.w = self.w[:, :self.thresholds[1]]
            self.v = self.v[:, :, :self.thresholds[1]]
        self.one_dimensional_correlation_function = np.einsum('uvxy, uxn, vyn, un, vn -> nuv',
                                                              self.correlation_function, self.v, self.v,
                                                              1 / np.sqrt(self.w), 1 / np.sqrt(self.w))

    def run(self, nsamples):
        for i in range(self.one_dimensional_correlation_function.shape[0]):
            if self.thresholds is not None:
                self.samples += np.einsum('x, xt, nx -> nxt', np.sqrt(self.w[:, i]), self.v[:, :, i],
                                          KLE(nsamples=nsamples,
                                              correlation_function=self.one_dimensional_correlation_function[i],
                                              time_interval=self.time_interval, threshold=self.thresholds[0]).samples[:,
                                          0, :])
            else:
                self.samples += np.einsum('x, xt, nx -> nxt', np.sqrt(self.w[:, i]), self.v[:, :, i],
                                          KLE(nsamples=nsamples,
                                              correlation_function=self.one_dimensional_correlation_function[i],
                                              time_interval=self.time_interval).samples[:, 0, :])
