import numpy as np
from numpy.testing import assert_equal
from nose.tools import assert_raises
from nose.tools import assert_true
from scipy.sparse import csr_matrix

from scikits.learn.metrics.pairwise import check_pairwise_arrays

def check_dense_matrices():
    """ Ensure that pairwise array check works for dense matrices."""
    # Check that if XB is None, XB is returned as reference to XA
    XA = np.resize(np.arange(40), (5, 8))
    XA_checked, XB_checked = check_pairwise_arrays(XA, None)
    assert_true(XA_checked is XB_checked)
    assert_equal(XA, XA_checked)

def check_XB_returned():
    """ Ensure that if XA and XB are given correctly, they return as equal."""
    # Check that if XB is not None, it is returned equal.
    # Note that the second dimension of XB is the same as XA.
    XA = np.resize(np.arange(40), (5, 8))
    XB = np.resize(np.arange(32), (4, 8))
    XA_checked, XB_checked = check_pairwise_arrays(XA, XB)
    assert_equal(XA, XA_checked)
    assert_equal(XB, XB_checked)


def check_different_dimensions():
    """ Ensure an error is raised if the dimensions are different. """
    XA = np.resize(np.arange(45), (5, 9))
    XB = np.resize(np.arange(32), (4, 8))
    assert_raises(ValueError, check_pairwise_array, XA, XB)


def check_invalid_dimensions():
    """ Ensure an error is raised on 1D input arrays. """
    XA = np.arange(45)
    XB = np.resize(np.arange(32), (4, 8))
    assert_raises(ValueError, check_pairwise_array, XA, XB)
    XA = np.resize(np.arange(45), (5, 9))
    XB = np.arange(32)
    assert_raises(ValueError, check_pairwise_array, XA, XB)


def check_sparse_arrays():
    """ Ensures that checks return valid sparse matrices. """
    rng = np.random.RandomState(0)
    XA = rng.random_sample((5, 4))
    XA_sparse = csr_matrix(XA)
    XB = rng.random_sample((5, 4))
    XB_sparse = csr_matrix(XB)
    XA_checked, XB_checked = check_pairwise_arrays(XA_sparse, XB_sparse)
    assert_equal(XA_sparse, XA_checked)
    assert_equal(XB_sparse, XB_checked)


