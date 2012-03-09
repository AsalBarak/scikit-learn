# Author: Lars Buitinck <L.J.Buitinck@uva.nl>
# License: BSD-style.

import numpy as np
import scipy.sparse as sp

from nose.tools import assert_equal
from numpy.testing import assert_array_equal

from sklearn.feature_extraction import DictVectorizer
from sklearn.feature_selection import SelectKBest, chi2


def test_dictvectorizer():
    D = [{"foo": 1, "bar": 3},
         {"bar": 4, "baz": 2},
         {"bar": 1, "quux": 1, "quuux": 2}]

    for sparse in (True, False):
        for dtype in (int, np.float32, np.int16):
            v = DictVectorizer(sparse=sparse, dtype=dtype)
            X = v.fit_transform(D)

            assert_equal(sp.issparse(X), sparse)
            assert_equal(X.shape, (3, 5))
            assert_equal(X.sum(), 14)
            assert_equal(v.inverse_transform(X), D)


def test_feature_selection():
    # make two feature dicts with two useful features and a bunch of useless
    # ones, in terms of chi2
    d1 = dict([("useless%d" % i, 10) for i in xrange(20)],
              useful1=1, useful2=20)
    d2 = dict([("useless%d" % i, 10) for i in xrange(20)],
              useful1=20, useful2=1)

    for indices in (True, False):
        v = DictVectorizer().fit([d1, d2])
        X = v.transform([d1, d2])
        sel = SelectKBest(chi2, k=2).fit(X, [0, 1])

        v.restrict(sel.get_support(indices=indices), indices=indices)
        assert_equal(v.get_feature_names(), ["useful1", "useful2"])


def test_unseen_features():
    D = [{"camelot": 0, "spamalot": 1}]
    v = DictVectorizer(sparse=False).fit(D)
    X = v.transform({"push the pram a lot": 2})

    assert_array_equal(X, np.zeros((1, 2)))
