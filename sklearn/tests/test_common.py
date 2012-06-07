"""
General tests for all estimators in sklearn.
"""
import warnings

from sklearn.utils.testing import all_estimators
from sklearn.utils.testing import assert_greater
from sklearn.base import clone, ClassifierMixin
from sklearn.datasets import load_iris
from sklearn.metrics import zero_one_score
from sklearn.lda import LDA

# import "special" estimators
from sklearn.grid_search import GridSearchCV
from sklearn.decomposition import SparseCoder
from sklearn.pipeline import Pipeline
from sklearn.ensemble import BaseEnsemble
from sklearn.multiclass import OneVsOneClassifier, OneVsRestClassifier,\
        OutputCodeClassifier
from sklearn.feature_selection import RFE, RFECV

dont_test = [Pipeline, GridSearchCV, SparseCoder]
meta_estimators = [BaseEnsemble, OneVsOneClassifier, OutputCodeClassifier,
        OneVsRestClassifier, RFE, RFECV]


def test_all_estimators():
    estimators = all_estimators()
    clf = LDA()

    # some can just not be sensibly default constructed
    for name, E in estimators:
        if E in dont_test:
            continue
        # test default-constructibility
        # get rid of deprecation warnings
        with warnings.catch_warnings(record=True) as w:
            if E in meta_estimators:
                e = E(clf)
            else:
                e = E()
            #test cloning
            clone(e)
            # test __repr__
            print(e)
        print(w)


def test_classifiers():
    estimators = all_estimators()
    classifiers = [(name, E) for name, E in estimators if issubclass(E,
        ClassifierMixin)]
    iris = load_iris()
    X, y = iris.data, iris.target
    print(classifiers)
    for name, Clf in classifiers:
        if Clf in dont_test or Clf in meta_estimators:
            continue
        clf = Clf()
        try:
            clf.fit(X, y)
            y_pred = clf.predict(X)
            assert_greater(zero_one_score(y, y_pred), 0.9)
        except Exception as ex:
            print("++++++++++++++++++++++++")
            print(clf)
            print(ex)
