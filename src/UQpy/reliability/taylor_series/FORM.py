import logging
from typing import Union
import numpy as np
import scipy.stats as stats
from beartype import beartype
from UQpy.distributions.baseclass import Distribution
from UQpy.transformations import *
from UQpy.reliability.taylor_series.baseclass.TaylorSeries import TaylorSeries
from UQpy.utilities.ValidationTypes import PositiveInteger
from UQpy.transformations import Decorrelate


class FORM(TaylorSeries):
    """
    A class perform the First Order reliability Method. The ``run`` method of the ``FORM`` class can be invoked many
    times and each time the results are appended to the existing ones.
    This is a child class of the ``taylor_series`` class.
    **Input:**
    See ``taylor_series`` class.
    **Attributes:**
    * **Pf_form** (`float`):
        First-order probability of failure estimate.
    * **beta_form** (`float`):
        Hasofer-Lind reliability index.
    * **DesignPoint_U** (`ndarray`):
        Design point in the uncorrelated standard normal space **U**.
    * **DesignPoint_X** (`ndarray`):
        Design point in the parameter space **X**.
    * **alpha** (`ndarray`):
        Direction cosine.
    * **form_iterations** (`int`):
        Number of model evaluations.
    * **u_record** (`list`):
        Record of all iteration points in the standard normal space **U**.
    * **x_record** (`list`):
        Record of all iteration points in the parameter space **X**.
    * **beta_record** (`list`):
        Record of all Hasofer-Lind reliability index values.
    * **dg_u_record** (`list`):
        Record of the model's gradient  in the standard normal space.
    * **alpha_record** (`list`):
        Record of the alpha (directional cosine).
    * **g_record** (`list`):
        Record of the performance function.
    * **error_record** (`list`):
        Record of the error defined by criteria `e1, e2, e3`.
    **Methods:**
     """
    @beartype
    def __init__(self,
                 distributions: Union[None, Distribution, list[Distribution]],
                 runmodel_object,
                 form_object=None,
                 seed_x: Union[list, np.ndarray] = None,
                 seed_u: Union[list, np.ndarray] = None,
                 df_step: Union[int, float] = 0.01,
                 corr_x: Union[list, np.ndarray] = None,
                 corr_z: Union[list, np.ndarray] = None,
                 iterations_number: PositiveInteger = 100,
                 tol1: Union[float, int] = None,
                 tol2: Union[float, int] = None,
                 tol3: Union[float, int] = None):

        super().__init__(distributions, runmodel_object, form_object, corr_x, corr_z, seed_x, seed_u,
                         iterations_number, tol1, tol2, tol3, df_step)

        self.logger = logging.getLogger(__name__)

        # Initialize output
        self.beta_form = None
        self.DesignPoint_U = None
        self.DesignPoint_X = None
        self.alpha = None
        self.failure_probability = None
        self.x = None
        self.alpha = None
        self.g0 = None
        self.form_iterations = None
        self.df_step = df_step
        self.error_record = None

        self.tol1 = tol1
        self.tol2 = tol2
        self.tol3 = tol3

        self.u_record = None
        self.x_record = None
        self.g_record = None
        self.dg_u_record = None
        self.alpha_record = None
        self.beta_record = None
        self.jzx = None

        self.call = None

        if self.seed_u is not None:
            self.run(seed_u=self.seed_u)
        elif self.seed_x is not None:
            self.run(seed_x=self.seed_x)
        else:
            pass

    def run(self, seed_x=None, seed_u=None):
        """
        Run FORM
        This is an instance method that runs FORM.
        **Input:**
        * **seed_u** or **seed_x** (`ndarray`):
            See ``taylor_series`` parent class.
        """
        self.logger.info('UQpy: Running FORM...')
        if seed_u is None and seed_x is None:
            seed = np.zeros(self.dimension)
        elif seed_u is None and seed_x is not None:
            self.nataf_object.run(samples_x=seed_x.reshape(1, -1), jacobian=False)
            seed_z = self.nataf_object.samples_z
            seed = Decorrelate(seed_z, self.nataf_object.corr_z)
        elif seed_u is not None and seed_x is None:
            seed = np.squeeze(seed_u)
        else:
            raise ValueError('UQpy: Only one seed (seed_x or seed_u) must be provided')

        u_record = list()
        x_record = list()
        g_record = list()
        alpha_record = list()
        error_record = list()

        converged = False
        k = 0
        beta = np.zeros(shape=(self.n_iter + 1,))
        u = np.zeros([self.n_iter + 1, self.dimension])
        u[0, :] = seed
        g_record.append(0.0)
        dg_u_record = np.zeros([self.n_iter + 1, self.dimension])

        while not converged:
            self.logger.info('Number of iteration:', k)
            # FORM always starts from the standard normal space
            if k == 0:
                if seed_x is not None:
                    x = seed_x
                else:
                    seed_z = Correlate(samples_u=seed.reshape(1, -1),
                                       corr_z=self.nataf_object.corr_z).samples_z
                    self.nataf_object.run(samples_z=seed_z.reshape(1, -1), jacobian=True)
                    x = self.nataf_object.samples_x
                    self.jzx = self.nataf_object.jxz
            else:
                z = Correlate(u[k, :].reshape(1, -1), self.nataf_object.corr_z).samples_z
                self.nataf_object.run(samples_z=z, jacobian=True)
                x = self.nataf_object.samples_x
                self.jzx = self.nataf_object.jxz

            self.x = x
            u_record.append(u)
            x_record.append(x)
            self.logger.info('Design point Y: {0}\n'.format(u[k, :]) +
                             'Design point X: {0}\n'.format(self.x) +
                             'Jacobian Jzx: {0}\n'.format(self.jzx))

            # 2. evaluate Limit State Function and the gradient at point u_k and direction cosines
            dg_u, qoi, _ = \
                self.derivatives(point_u=u[k, :], point_x=self.x, runmodel_object=self.runmodel_object,
                                 nataf_object=self.nataf_object, df_step=self.df_step, order='first')
            g_record.append(qoi)

            dg_u_record[k + 1, :] = dg_u
            norm_grad = np.linalg.norm(dg_u_record[k + 1, :])
            alpha = dg_u / norm_grad
            self.logger.info('Directional cosines (alpha): {0}\n'.format(alpha) +
                             'Gradient (dg_y): {0}\n'.format(dg_u_record[k + 1, :]) +
                             'norm dg_y:', norm_grad)

            self.alpha = alpha.squeeze()
            alpha_record.append(self.alpha)
            beta[k] = -np.inner(u[k, :].T, self.alpha)
            beta[k + 1] = beta[k] + qoi / norm_grad
            self.logger.info('Beta: {0}\n'.format(beta[k]) +
                             'Pf: {0}'.format(stats.norm.cdf(-beta[k])))

            u[k + 1, :] = -beta[k + 1] * self.alpha

            if (self.tol1 is not None) and (self.tol2 is not None) and (self.tol3 is not None):
                error1 = np.linalg.norm(u[k + 1, :] - u[k, :])
                error2 = np.linalg.norm(beta[k + 1] - beta[k])
                error3 = np.linalg.norm(dg_u_record[k + 1, :] - dg_u_record[k, :])
                error_record.append([error1, error2, error3])
                if error1 <= self.tol1 and error2 <= self.tol2 and error3 < self.tol3:
                    converged = True
                else:
                    k = k + 1

            if (self.tol1 is None) and (self.tol2 is None) and (self.tol3 is None):
                error1 = np.linalg.norm(u[k + 1, :] - u[k, :])
                error2 = np.linalg.norm(beta[k + 1] - beta[k])
                error3 = np.linalg.norm(dg_u_record[k + 1, :] - dg_u_record[k, :])
                error_record.append([error1, error2, error3])
                if error1 <= 1e-3 or error2 <= 1e-3 or error3 < 1e-3:
                    converged = True
                else:
                    k = k + 1

            elif (self.tol1 is not None) and (self.tol2 is None) and (self.tol3 is None):
                error1 = np.linalg.norm(u[k + 1, :] - u[k, :])
                error_record.append(error1)
                if error1 <= self.tol1:
                    converged = True
                else:
                    k = k + 1

            elif (self.tol1 is None) and (self.tol2 is not None) and (self.tol3 is None):
                error2 = np.linalg.norm(beta[k + 1] - beta[k])
                error_record.append(error2)
                if error2 <= self.tol2:
                    converged = True
                else:
                    k = k + 1

            elif (self.tol1 is None) and (self.tol2 is None) and (self.tol3 is not None):
                error3 = np.linalg.norm(dg_u_record[k + 1, :] - dg_u_record[k, :])
                error_record.append(error3)
                if error3 < self.tol3:
                    converged = True
                else:
                    k = k + 1

            elif (self.tol1 is not None) and (self.tol2 is not None) and (self.tol3 is None):
                error1 = np.linalg.norm(u[k + 1, :] - u[k, :])
                error2 = np.linalg.norm(beta[k + 1] - beta[k])
                error_record.append([error1, error2])
                if error1 <= self.tol1 and error2 <= self.tol1:
                    converged = True
                else:
                    k = k + 1

            elif (self.tol1 is not None) and (self.tol2 is None) and (self.tol3 is not None):
                error1 = np.linalg.norm(u[k + 1, :] - u[k, :])
                error3 = np.linalg.norm(dg_u_record[k + 1, :] - dg_u_record[k, :])
                error_record.append([error1, error3])
                if error1 <= self.tol1 and error3 < self.tol3:
                    converged = True
                else:
                    k = k + 1

            elif (self.tol1 is None) and (self.tol2 is not None) and (self.tol3 is not None):
                error2 = np.linalg.norm(beta[k + 1] - beta[k])
                error3 = np.linalg.norm(dg_u_record[k + 1, :] - dg_u_record[k, :])
                error_record.append([error2, error3])
                if error2 <= self.tol2 and error3 < self.tol3:
                    converged = True
                else:
                    k = k + 1

            self.logger.error('Error: %s', error_record[-1])

            if converged is True or k > self.n_iter:
                break

        if k > self.n_iter:
            self.logger\
                .info('UQpy: Maximum number of iterations {0} was reached before convergence.'.format(self.n_iter))
            self.error_record = error_record
            self.u_record = [u_record]
            self.x_record = [x_record]
            self.g_record = [g_record]
            self.dg_u_record = [dg_u_record[:k]]
            self.alpha_record = [alpha_record]
        else:
            if self.call is None:
                self.beta_record = [beta[:k]]
                self.error_record = error_record
                self.beta_form = [beta[k]]
                self.DesignPoint_U = [u[k, :]]
                self.DesignPoint_X = [np.squeeze(self.x)]
                self.failure_probability = [stats.norm.cdf(-self.beta_form[-1])]
                self.form_iterations = [k]
                self.u_record = [u_record[:k]]
                self.x_record = [x_record[:k]]
                self.g_record = [g_record]
                self.dg_u_record = [dg_u_record[:k]]
                self.alpha_record = [alpha_record]
            else:
                self.beta_record = self.beta_record + [beta[:k]]
                self.beta_form = self.beta_form + [beta[k]]
                self.error_record = self.error_record + error_record
                self.DesignPoint_U = self.DesignPoint_U + [u[k, :]]
                self.DesignPoint_X = self.DesignPoint_X + [np.squeeze(self.x)]
                self.failure_probability = self.failure_probability + [stats.norm.cdf(-beta[k])]
                self.form_iterations = self.form_iterations + [k]
                self.u_record = self.u_record + [u_record[:k]]
                self.x_record = self.x_record + [x_record[:k]]
                self.g_record = self.g_record + [g_record]
                self.dg_u_record = self.dg_u_record + [dg_u_record[:k]]
                self.alpha_record = self.alpha_record + [alpha_record]
            self.call = True
