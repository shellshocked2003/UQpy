import pytest
from beartype.roar import BeartypeCallHintPepParamException

from UQpy.distributions.collection import *
from UQpy.sampling.stratified_sampling.TrueStratifiedSampling import *
from UQpy.sampling.stratified_sampling.strata import SamplingCriterion
from UQpy.sampling.stratified_sampling.strata.VoronoiStrata import *


def test_rectangular_sts():
    marginals = [Uniform(loc=0., scale=1.), Uniform(loc=0., scale=1.)]
    strata = RectangularStrata(strata_number=[4, 4], random_state=1)
    x = TrueStratifiedSampling(distributions=marginals, strata_object=strata,
                               nsamples_per_stratum=1, )
    assert x.samples[6, 0] == 0.5511130624328794
    assert x.samples[12, 1] == 0.9736516658759619
    assert x.samples[2, 0] == 0.5366889727042783
    assert x.samples[9, 1] == 0.5495253722712197


def test_delaunay_sts():
    marginals = [Exponential(loc=1., scale=1.), Exponential(loc=1., scale=1.)]
    seeds = np.array([[0, 0], [0.4, 0.8], [1, 0], [1, 1]])
    strata_obj = DelaunayStrata(seeds=seeds, )
    sts_obj = TrueStratifiedSampling(distributions=marginals, strata_object=strata_obj, random_state=1,
                                     nsamples_per_stratum=1, )
    assert np.round(sts_obj.samples[2, 0], 8) == 1.90258174


def test_voronoi_sts():
    marginals = [Exponential(loc=1., scale=1.), Exponential(loc=1., scale=1.)]
    strata = VoronoiStrata(seeds_number=8, dimension=2, random_state=3)
    x = TrueStratifiedSampling(distributions=marginals, strata_object=strata,
                               nsamples_per_stratum=3)
    assert np.round(x.samples[7, 0], 8) == 3.69284409
    assert np.round(x.samples[20, 1], 8) == 1.15559632
    assert np.round(x.samples[1, 0], 8) == 1.8393015
    assert np.round(x.samples[15, 1], 8) == 2.11772762


# Rectangular
marginals = [Exponential(loc=1., scale=1.), Exponential(loc=1., scale=1.)]
strata = RectangularStrata(strata_number=[3, 3])

nsamples_per_stratum = [1] * 9
nsamples_per_stratum[4] = 0
x_sts = TrueStratifiedSampling(distributions=marginals, strata_object=strata,
                               nsamples_per_stratum=nsamples_per_stratum, random_state=1)
strata1 = RectangularStrata(strata_number=[3, 3], sampling_criterion=SamplingCriterion.CENTERED,
                            random_state=1)
x_sts1 = TrueStratifiedSampling(distributions=marginals, strata_object=strata1, nsamples_per_stratum=1, )

# Voronoi
strata_vor = VoronoiStrata(seeds_number=8, dimension=2, random_state=3)
sts_vor = TrueStratifiedSampling(distributions=marginals, strata_object=strata_vor)
sts_vor.run(nsamples_per_stratum=1)

strata_vor1 = VoronoiStrata(seeds_number=8, dimension=2, random_state=3)
sts_vor2 = TrueStratifiedSampling(distributions=marginals, strata_object=strata_vor1, )
sts_vor2.run(nsamples=8, nsamples_per_stratum=1)
sts_vor2.run()

# Delaunay
seeds = np.array([[0, 0], [0.4, 0.8], [1, 0], [1, 1]])
strata_del = DelaunayStrata(seeds=seeds, random_state=2)
sts_del = TrueStratifiedSampling(distributions=marginals, strata_object=strata_del,
                                 nsamples_per_stratum=2)


# Unit tests
def test_rect_random():
    """
    Test the samples generated by 3x3 rectangular strata, with random points
    """
    assert np.allclose(x_sts.samples, np.array([[1.14966929, 1.27457918], [1.4055223, 1.1062248],
                                                [2.25732188, 1.03126317], [1.0640978, 1.59515015],
                                                [2.60406483, 1.71936573], [1.15051073, 3.254492],
                                                [1.51330216, 4.20330958], [2.12638191, 3.20869262]]))
    assert np.allclose(x_sts.samplesU01, np.array([[0.13900733, 0.24010816], [0.33337146, 0.10077752],
                                                   [0.7155853, 0.03077953], [0.06208674, 0.44852024],
                                                   [0.79892249, 0.51293891], [0.1397315, 0.89507317],
                                                   [0.40148408, 0.95937248], [0.67579586, 0.89015584]]))


def test_rect_centered():
    """
    Test the samples generated by 3x3 rectangular strata, with centered points
    """
    tmp1 = (np.round(x_sts1.samples, 3) == np.array([[1.182, 1.182], [1.693, 1.182], [2.792, 1.182], [1.182, 1.693],
                                                     [1.693, 1.693], [2.792, 1.693], [1.182, 2.792], [1.693, 2.792],
                                                     [2.792, 2.792]])).all()
    tmp2 = (np.round(x_sts1.samplesU01, 3) == np.array([[0.167, 0.167], [0.5, 0.167], [0.833, 0.167], [0.167, 0.5],
                                                        [0.5, 0.5], [0.833, 0.5], [0.167, 0.833], [0.5, 0.833],
                                                        [0.833, 0.833]])).all()
    assert tmp1 and tmp2


def test_rect_sts_criterion():
    """
        Test the 'sts_criterion' attribute for RectangularSTS class.
    """
    with pytest.raises(AttributeError):
        RectangularStrata(sampling_criterion=SamplingCriterion.aaa)


def test_rect_strata_object():
    """
        Test type of strata_object. It should be a RectangularStrata object.
    """
    with pytest.raises(BeartypeCallHintPepParamException):
        TrueStratifiedSampling(distributions=marginals, strata_object=None, nsamples_per_stratum=1)


def test_rect_nsamples_check1():
    """
        In case of centered sampling, nsamples should be equal to number of strata in strata_object.
    """
    with pytest.raises(ValueError):
        strata.sampling_criterion = SamplingCriterion.CENTERED
        TrueStratifiedSampling(distributions=marginals, strata_object=strata, nsamples_per_stratum=1,
                               nsamples=10)


def test_vor_nsamples_per_strarum_not_0():
    """
        Test samples and weights of the class object, when all stratum has atleast 1 sample.
    """
    assert np.allclose(sts_vor.samples, np.array([[1.5185188,  2.50692166], [1.19961165, 2.53070353],
                                                  [4.64208735, 3.15996289], [1.1938551,  1.30464598],
                                                  [1.22346669, 1.46101267], [1.00251352, 1.68941482],
                                                  [1.58543262, 1.07725168], [2.12618711, 1.66531153]]))
    assert np.allclose(sts_vor.weights, np.array([0.16067610144427008, 0.15776137825840353, 0.09704553679275912,
                                                  0.12806452403454796, 0.0316694475356838, 0.053596335374910736,
                                                  0.2494276251010699, 0.12175905145835474]))



def test_vor_strata_object():
    """
        Test type of strata_object. It should be a VoronoiStrata object.
    """
    with pytest.raises(BeartypeCallHintPepParamException):
        TrueStratifiedSampling(distributions=marginals, strata_object=None)


def test_vor_random_state():
    """
        Check 'random_state' is an integer or RandomState object.
    """
    with pytest.raises(BeartypeCallHintPepParamException):
        TrueStratifiedSampling(distributions=marginals, strata_object=strata_vor, random_state='abc')


def test_vor_dist_object():
    """
        Check 'dist_object' is a Distribution object.
    """
    with pytest.raises(BeartypeCallHintPepParamException):
        TrueStratifiedSampling(distributions=[2, 1], strata_object=strata_vor)


def test_vor_dist_object2():
    """
        Check 'dist_object' is a Distribution object.
    """
    with pytest.raises(BeartypeCallHintPepParamException):
        TrueStratifiedSampling(distributions=2, strata_object=strata_vor)


def test_voronoi_nsamples_check():
    """
        In case of centered sampling, nsamples should be equal to number of strata in strata_object.
    """
    with pytest.raises(BeartypeCallHintPepParamException):
        sts_vor.run(nsamples='abc')


def test_voronoi_nsamples_per_stratum_check():
    """
        Check length of nsamples_per_stratum should be equal to number of strata in strata_object.
    """
    with pytest.raises(ValueError):
        sts_vor.run(nsamples_per_stratum=[2, 1, 0, 1])


def test_voronoi_nsamples_per_stratum_check2():
    """
        Check nsamples_per_stratum should an integer or list.
    """
    with pytest.raises(BeartypeCallHintPepParamException):
        sts_vor.run(nsamples_per_stratum='abc')


def test_del_nsamples_per_strarum_not_0():
    """
        Test samples and weights of the class object, when all stratum has atleast 1 sample.
    """
    assert np.allclose(sts_del.samples, np.array([[1.14604405, 3.46440724], [1.10919352, 1.98225373],
                                                  [1.74510444, 1.4267083], [1.95844896, 1.14825374],
                                                  [1.87318612, 3.40220043], [1.60852035, 4.16117521],
                                                  [3.23430303, 2.49568182], [3.89471882, 2.03363426]]))
    assert np.allclose(sts_del.weights, np.array([0.1,  0.1,  0.2,  0.2,  0.05, 0.05, 0.15, 0.15]))


def test_del_strata_object():
    """
        Test type of strata_object. It should be a DelaunayStrata object.
    """
    with pytest.raises(BeartypeCallHintPepParamException):
        TrueStratifiedSampling(distributions=marginals, strata_object=None)

