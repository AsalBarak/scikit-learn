# Authors: Gilles Louppe,
#          Brian Holt

import numpy as np

from ..base import clone
from ..base import BaseEstimator, ClassifierMixin, RegressorMixin
from ..tree import DecisionTreeClassifier, DecisionTreeRegressor, \
                   ExtraTreeClassifier, ExtraTreeRegressor
from ..utils import check_random_state

__all__ = [
    "RandomForestClassifier",
    "RandomForestRegressor",
    "ExtraTreesClassifier",
    "ExtraTreesRegressor"
]


class Forest(BaseEstimator):
    """Base class for forests of trees estimators.

    Warning: This class should not be used directly. Use derived classes instead.
    """
    def __init__(self, base_tree, n_trees=10, bootstrap=False, random_state=None):
        self.base_tree = base_tree
        self.n_trees = n_trees
        self.bootstrap = bootstrap
        self.random_state = check_random_state(random_state)
        self.forest = []

    def fit(self, X, y):
        """Build a forest of trees from the training set (X, y).

        Parameters
        ----------
        X : array-like of shape = [n_samples, n_features]
            The training input samples.

        y : array-like, shape = [n_samples]
            The target values (integers that correspond to classes in
            classification, real numbers in regression).

        Return
        ------
        self : object
            Returns self.
        """
        X = np.atleast_2d(X)
        y = np.atleast_1d(y)

        if isinstance(self.base_tree, ClassifierMixin):
            self.classes = np.unique(y)
            self.n_classes = len(self.classes)
            y = np.searchsorted(self.classes, y)

        for i in xrange(self.n_trees):
            tree = clone(self.base_tree)

            if self.bootstrap:
                n_samples = X.shape[0]
                indices = np.random.randint(0, n_samples, n_samples)

                X = X[indices]
                y = y[indices]

            tree.fit(X, y)
            self.forest.append(tree)

class ForestClassifier(Forest, ClassifierMixin):
    """Base class for forest of trees-based classifiers.

    Warning: This class should not be used directly. Use derived classes instead."""
    def __init__(self, base_tree, n_trees=10, bootstrap=False, random_state=None):
        Forest.__init__(self, base_tree,
                              n_trees,
                              bootstrap=bootstrap,
                              random_state=random_state)

    def predict(self, X):
        """Predict class for X.

        The predicted class of an input sample is computed as the likeliest
        prediction of the trees in the forest.

        Parameters
        ----------
        X : array-like of shape = [n_samples, n_features]
            The input samples.

        Returns
        -------
        predictions : array of shape = [n_samples]
            The predicted classes.
        """
        return self.classes[np.argmax(self.predict_proba(X), axis=1)]

    def predict_proba(self, X):
        """Predict class probabilities for X.

        The predicted class probabilities of an input sample is computed as
        the mean class probabilities of the trees in the forest.

        Parameters
        ----------
        X : array-like of shape = [n_samples, n_features]
            The input samples.

        Returns
        -------
        p : array of shape = [n_samples]
            The class probabilities of the input samples.
        """
        X = np.atleast_2d(X)
        p = np.zeros((X.shape[0], self.n_classes))

        for tree in self.forest:
            p += tree.predict_proba(X)

        p /= self.n_trees

        return p

class ForestRegressor(Forest, RegressorMixin):
    """Base class for forest of trees-based regressors.

    Warning: This class should not be used directly. Use derived classes instead."""
    def __init__(self, base_tree, n_trees=10, bootstrap=False, random_state=None):
        Forest.__init__(self, base_tree,
                              n_trees,
                              bootstrap=bootstrap,
                              random_state=random_state)

    def predict(self, X):
        """Predict regression target for X.

        The predicted regression target of an input sample is computed as the
        mean regression target of the trees in the forest.

        Parameters
        ----------
        X : array-like of shape = [n_samples, n_features]
            The input samples.

        Returns
        -------
        predictions : array of shape = [n_samples]
            The predicted values.
        """
        X = np.atleast_2d(X)
        y_hat = np.zeros(X.shape[0])

        for tree in self.forest:
            y_hat += tree.predict(X)

        y_hat /= self.n_trees

        return y_hat

class RandomForestClassifier(ForestClassifier):
    """Random forest classifier.

    TODO"""
    def __init__(self, n_trees=10, bootstrap=True, random_state=None, **tree_args):
        ForestClassifier.__init__(self, DecisionTreeClassifier(**tree_args),
                                        n_trees,
                                        bootstrap=bootstrap,
                                        random_state=random_state)

class RandomForestRegressor(ForestRegressor):
    """Random forest regressor.

    TODO"""
    def __init__(self, n_trees=10, bootstrap=True, random_state=None, **tree_args):
        ForestRegressor.__init__(self, DecisionTreeRegressor(**tree_args),
                                       n_trees,
                                       bootstrap=bootstrap,
                                       random_state=random_state)

class ExtraTreesClassifier(ForestClassifier):
    """Extra-trees classifier.

    TODO"""
    def __init__(self, n_trees=10, bootstrap=False, random_state=None, **tree_args):
        ForestClassifier.__init__(self, ExtraTreeClassifier(**tree_args),
                                        n_trees,
                                        bootstrap=bootstrap,
                                        random_state=random_state)

class ExtraTreesRegressor(ForestRegressor):
    """Extra-trees regressor.

    TODO"""
    def __init__(self, n_trees=10, bootstrap=False, random_state=None, **tree_args):
        ForestRegressor.__init__(self, ExtraTreeRegressor(**tree_args),
                                       n_trees,
                                       bootstrap=bootstrap,
                                       random_state=random_state)
