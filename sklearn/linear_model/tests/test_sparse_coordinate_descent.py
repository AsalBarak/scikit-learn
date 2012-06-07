import warnings
from sys import version_info

import numpy as np
from scipy import interpolate
import scipy.sparse as sp

from numpy.testing import assert_array_almost_equal
from numpy.testing import assert_almost_equal
from numpy.testing import assert_equal

from nose import SkipTest
from nose.tools import assert_true
from sklearn.utils.testing import assert_greater
from sklearn.utils.testing import assert_less, assert_greater

from sklearn.linear_model.coordinate_descent import Lasso, \
    LassoCV, ElasticNet, ElasticNetCV


def test_sparse_coef():
    """ Check that the sparse_coef propery works """
    clf = ElasticNet()
    clf.coef_ = [1, 2, 3]

    assert_true(sp.isspmatrix(clf.sparse_coef_))
    assert_equal(clf.sparse_coef_.todense().tolist()[0], clf.coef_)


def test_lasso_zero():
    """Check that the sparse lasso can handle zero data without crashing"""
    X = sp.csc_matrix((3, 1))
    y = [0, 0, 0]
    T = np.array([[1], [2], [3]])
    clf = Lasso().fit(X, y)
    pred = clf.predict(T)
    assert_array_almost_equal(clf.coef_, [0])
    assert_array_almost_equal(pred, [0, 0, 0])
    assert_almost_equal(clf.dual_gap_,  0)


def test_enet_toy_list_input():
    """Test ElasticNet for various parameters of alpha and rho with list X"""

    X = np.array([[-1], [0], [1]])
    Y = [-1, 0, 1]       # just a straight line
    T = np.array([[2], [3], [4]])  # test sample

    # this should be the same as unregularized least squares
    clf = ElasticNet(alpha=0, rho=1.0)
    clf.fit(X, Y)
    pred = clf.predict(T)
    assert_array_almost_equal(clf.coef_, [1])
    assert_array_almost_equal(pred, [2, 3, 4])
    assert_almost_equal(clf.dual_gap_, 0)

    clf = ElasticNet(alpha=0.5, rho=0.3, max_iter=1000)
    clf.fit(X, Y)
    pred = clf.predict(T)
    assert_array_almost_equal(clf.coef_, [0.50819], decimal=3)
    assert_array_almost_equal(pred, [1.0163,  1.5245,  2.0327], decimal=3)
    assert_almost_equal(clf.dual_gap_, 0)

    clf = ElasticNet(alpha=0.5, rho=0.5)
    clf.fit(X, Y)
    pred = clf.predict(T)
    assert_array_almost_equal(clf.coef_, [0.45454], 3)
    assert_array_almost_equal(pred, [0.9090,  1.3636,  1.8181], 3)
    assert_almost_equal(clf.dual_gap_, 0)


def test_enet_toy_explicit_sparse_input():
    """Test ElasticNet for various parameters of alpha and rho with sparse X"""

    # training samples
    X = sp.lil_matrix((3, 1))
    X[0, 0] = -1
    # X[1, 0] = 0
    X[2, 0] = 1
    Y = [-1, 0, 1]       # just a straight line (the identity function)

    # test samples
    T = sp.lil_matrix((3, 1))
    T[0, 0] = 2
    T[1, 0] = 3
    T[2, 0] = 4

    # this should be the same as lasso
    clf = ElasticNet(alpha=0, rho=1.0)
    clf.fit(X, Y)
    pred = clf.predict(T)
    assert_array_almost_equal(clf.coef_, [1])
    assert_array_almost_equal(pred, [2, 3, 4])
    assert_almost_equal(clf.dual_gap_, 0)

    clf = ElasticNet(alpha=0.5, rho=0.3, max_iter=1000)
    clf.fit(X, Y)
    pred = clf.predict(T)
    assert_array_almost_equal(clf.coef_, [0.50819], decimal=3)
    assert_array_almost_equal(pred, [1.0163,  1.5245,  2.0327], decimal=3)
    assert_almost_equal(clf.dual_gap_, 0)

    clf = ElasticNet(alpha=0.5, rho=0.5)
    clf.fit(X, Y)
    pred = clf.predict(T)
    assert_array_almost_equal(clf.coef_, [0.45454], 3)
    assert_array_almost_equal(pred, [0.9090,  1.3636,  1.8181], 3)
    assert_almost_equal(clf.dual_gap_, 0)


def make_sparse_data(n_samples, n_features, n_informative, seed=42,
                     positive=False):
    random_state = np.random.RandomState(seed)

    # build an ill-posed linear regression problem with many noisy features and
    # comparatively few samples

    # generate a ground truth model
    w = random_state.randn(n_features)
    w[n_informative:] = 0.0  # only the top features are impacting the model
    if positive:
        w = np.abs(w)

    X = random_state.randn(n_samples, n_features)
    rnd = random_state.uniform(size=(n_samples, n_features))
    X[rnd > 0.5] = 0.0  # 50% of zeros in input signal

    # generate training ground truth labels
    y = np.dot(X, w)
    return X, y


def _test_sparse_enet_not_as_toy_dataset(alpha, fit_intercept, positive):
    n_samples, n_features, max_iter = 100, 100, 1000
    n_informative = 10

    X, y = make_sparse_data(n_samples, n_features, n_informative,
                            positive=positive)

    X_train, X_test = X[n_samples / 2:], X[:n_samples / 2]
    y_train, y_test = y[n_samples / 2:], y[:n_samples / 2]

    s_clf = ElasticNet(alpha=alpha, rho=0.8, fit_intercept=fit_intercept,
                       max_iter=max_iter, tol=1e-7, positive=positive,
                       warm_start=True)
    s_clf.fit(X_train, y_train)

    assert_almost_equal(s_clf.dual_gap_, 0, 4)
    assert_greater(s_clf.score(X_test, y_test), 0.85)

    # check the convergence is the same as the dense version
    d_clf = ElasticNet(alpha=alpha, rho=0.8, fit_intercept=fit_intercept,
                      max_iter=max_iter, tol=1e-7, positive=positive,
                      warm_start=True)
    d_clf.fit(X_train, y_train)

    assert_almost_equal(d_clf.dual_gap_, 0, 4)
    assert_greater(d_clf.score(X_test, y_test), 0.85)

    assert_almost_equal(s_clf.coef_, d_clf.coef_, 5)
    assert_almost_equal(s_clf.intercept_, d_clf.intercept_, 5)

    # check that the coefs are sparse
    assert_less(np.sum(s_clf.coef_ != 0.0), 2 * n_informative)

    # check that warm restart leads to the same result with
    # sparse and dense versions

    rng = np.random.RandomState(seed=0)
    coef_init = rng.randn(n_features)

    d_clf.fit(X_train, y_train, coef_init=coef_init)
    s_clf.fit(X_train, y_train, coef_init=coef_init)

    assert_almost_equal(s_clf.coef_, d_clf.coef_, 5)
    assert_almost_equal(s_clf.intercept_, d_clf.intercept_, 5)


def test_sparse_enet_not_as_toy_dataset():
    _test_sparse_enet_not_as_toy_dataset(alpha=0.1, fit_intercept=False,
                                         positive=False)
    _test_sparse_enet_not_as_toy_dataset(alpha=0.1, fit_intercept=True,
                                         positive=False)
    _test_sparse_enet_not_as_toy_dataset(alpha=1e-3, fit_intercept=False,
                                         positive=True)
    _test_sparse_enet_not_as_toy_dataset(alpha=1e-3, fit_intercept=True,
                                         positive=True)


def test_sparse_lasso_not_as_toy_dataset():
    n_samples, n_features, max_iter = 100, 100, 1000
    n_informative = 10

    X, y = make_sparse_data(n_samples, n_features, n_informative)

    X_train, X_test = X[n_samples / 2:], X[:n_samples / 2]
    y_train, y_test = y[n_samples / 2:], y[:n_samples / 2]

    s_clf = Lasso(alpha=0.1, fit_intercept=False,
                        max_iter=max_iter, tol=1e-7)
    s_clf.fit(X_train, y_train)
    assert_almost_equal(s_clf.dual_gap_, 0, 4)
    assert_greater(s_clf.score(X_test, y_test), 0.85)

    # check the convergence is the same as the dense version
    d_clf = Lasso(alpha=0.1, fit_intercept=False, max_iter=max_iter,
            tol=1e-7)
    d_clf.fit(X_train, y_train)
    assert_almost_equal(d_clf.dual_gap_, 0, 4)
    assert_greater(d_clf.score(X_test, y_test), 0.85)

    # check that the coefs are sparse
    assert_equal(np.sum(s_clf.coef_ != 0.0), n_informative)