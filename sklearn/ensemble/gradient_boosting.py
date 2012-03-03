# Authors: Peter Prettenhofer
#
# License: BSD Style.
#
# TODO:
#      * Multi-class classification
#      * Huber loss for regression
#      * Partial-dependency plots
#      * Routine to find optimal n_estimators
#

from __future__ import division
import numpy as np

from .base import BaseEnsemble
from ..base import ClassifierMixin
from ..base import RegressorMixin
from ..utils import check_random_state

from ..tree.tree import _build_tree
from ..tree.tree import compute_feature_importances
from ..tree.tree import Tree
from ..tree._tree import _find_best_split
from ..tree._tree import MSE
from ..tree._tree import DTYPE


# ignore overflows due to exp(-pred) in BinomailDeviance
#np.seterr(invalid='raise', under='raise', divide='raise', over='ignore')


class MedianPredictor(object):
    """A simple initial estimator that predicts the median
    of the training targets.
    """

    median = None

    def fit(self, X, y):
        self.median = np.median(y)

    def predict(self, X):
        y = np.empty((X.shape[0],), dtype=np.float64)
        y.fill(self.median)
        return y


class MeanPredictor(object):
    """A simple initial estimator that predicts the mean
    of the training targets.
    """

    mean = None

    def fit(self, X, y):
        self.mean = np.mean(y)

    def predict(self, X):
        y = np.empty((X.shape[0],), dtype=np.float64)
        y.fill(self.mean)
        return y


class ClassPriorPredictor(object):
    """A simple initial estimator that predicts the mean
    of the training targets.
    """

    prior = None

    def fit(self, X, y):
        self.prior = np.log(np.sum(y) / np.sum(1.0 - y))

    def predict(self, X):
        y = np.empty((X.shape[0],), dtype=np.float64)
        y.fill(self.prior)
        return y


class LossFunction(object):
    """Abstract base class for various loss functions."""

    def init_estimator(self, X, y):
        pass

    def __call__(self, y, pred):
        pass

    def negative_gradient(self, y, pred):
        """Compute the negative gradient."""
        pass

    def update_terminal_regions(self, tree, X, y, residual, y_pred,
                                learn_rate=1.0):
        """Update the terminal regions (=leaves) of the given tree and
        updates the current predictions of the model. Traverses tree
        and invokes template method `_update_terminal_region`."""
        for leaf in np.where(tree.children[:, 0] == Tree.LEAF)[0]:
            self._update_terminal_region(tree, leaf, X, y, residual, y_pred)

        # update predictions
        mask = tree.terminal_region != -1
        y_pred[mask] += learn_rate * \
                        tree.value[:, 0].take(tree.terminal_region[mask],
                                              axis=0)

        # save memory
        del tree.terminal_region

    def _update_terminal_region(self, tree, leaf, X, y, residual, pred):
        """Template method for updating terminal regions (=leafs). """
        pass


class LeastSquaresError(LossFunction):
    """Loss function for least squares (LS) estimation.
    Terminal regions need not to be updated for least squares. """

    def init_estimator(self):
        return MeanPredictor()

    def __call__(self, y, pred):
        return np.mean((y - pred) ** 2.0)

    def negative_gradient(self, y, pred):
        return y - pred


class LeastAbsoluteError(LossFunction):
    """Loss function for least absolute deviation (LAD) regression. """

    def init_estimator(self):
        return MedianPredictor()

    def __call__(self, y, pred):
        return np.abs(y - pred).mean()

    def negative_gradient(self, y, pred):
        return np.sign(y - pred)

    def _update_terminal_region(self, tree, leaf, X, y, residual, pred):
        """LAD updates terminal regions to median estimates. """
        terminal_region = np.where(tree.terminal_region == leaf)[0]
        tree.value[leaf, 0] = np.median(y.take(terminal_region, axis=0) - \
                                        pred.take(terminal_region, axis=0))


class BinomialDeviance(LossFunction):
    """Binomial deviance loss function for binary classification."""

    def init_estimator(self):
        return ClassPriorPredictor()

    def __call__(self, y, pred):
        """Compute the deviance (= negative log-likelihood). """
        # logaddexp(0, v) == log(1.0 + exp(v))
        return -2.0 * np.sum(y * pred -
                             np.logaddexp(0.0, pred)) / y.shape[0]

    def negative_gradient(self, y, pred):
        return y - 1.0 / (1.0 + np.exp(-pred))

    def _update_terminal_region(self, tree, leaf, X, y, residual, pred):
        """Make a single Newton-Raphson step. """
        terminal_region = np.where(tree.terminal_region == leaf)[0]
        residual = residual.take(terminal_region, axis=0)
        y = y.take(terminal_region, axis=0)

        numerator = residual.sum()
        denominator = np.sum((y - residual) * (1.0 - y + residual))

        if denominator == 0.0:
            tree.value[leaf, 0] = 0.0
        else:
            tree.value[leaf, 0] = numerator / denominator


LOSS_FUNCTIONS = {'ls': LeastSquaresError,
                  'lad': LeastAbsoluteError,
                  'deviance': BinomialDeviance}


class BaseGradientBoosting(BaseEnsemble):
    """Abstract base class for Gradient Boosting. """

    def __init__(self, loss, learn_rate, n_estimators, min_samples_split,
                 min_samples_leaf, max_depth, init, subsample, random_state):
        if n_estimators <= 0:
            raise ValueError("n_estimators must be greater than 0")
        self.n_estimators = n_estimators

        if learn_rate <= 0.0:
            raise ValueError("learn_rate must be greater than 0")
        self.learn_rate = learn_rate

        if loss not in LOSS_FUNCTIONS:
            raise ValueError("loss '%s' not supported" % loss)
        self.loss = loss

        if min_samples_split <= 0:
            raise ValueError("min_samples_split must be larger than 0.")
        self.min_samples_split = min_samples_split

        if min_samples_leaf <= 0:
            raise ValueError("min_samples_leaf must be larger than 0.")
        self.min_samples_leaf = min_samples_leaf

        if subsample <= 0.0 or subsample > 1:
            raise ValueError("subsample must be in (0,1]")
        self.subsample = subsample

        if max_depth <= 0:
            raise ValueError("max_depth must be larger than 0.")
        self.max_depth = max_depth

        if init is not None:
            if not hasattr(init, 'fit') or not hasattr(init, 'predict'):
                raise ValueError("init must be valid estimator")
        self.init = init

        self.random_state = check_random_state(random_state)

        self.estimators_ = []

    def fit(self, X, y, monitor=None):
        """Fit the gradient boosting model.

        Parameters
        ----------
        X : array-like, shape = [n_samples, n_features]
            Training vectors, where n_samples is the number of samples
            and n_features is the number of features. Use fortran-style
            to avoid memory copies.

        y : array-like, shape = [n_samples]
            Target values (integers in classification, real numbers in
            regression)
            For classification, labels must correspond to classes
            0, 1, ..., n_classes-1

        Returns
        -------
        self : object
            Returns self.
        """
        X = np.asfortranarray(X, dtype=DTYPE)
        y = np.ascontiguousarray(y)

        n_samples, n_features = X.shape
        if y.shape[0] != n_samples:
            raise ValueError("Number of labels does not match " \
                             "number of samples.")
        self.n_features = n_features

        loss = LOSS_FUNCTIONS[self.loss]()

        # store loss object for future use
        self.loss_ = loss

        if self.init is None:
            self.init = loss.init_estimator()

        # create argsorted X for fast tree induction
        X_argsorted = np.asfortranarray(
            np.argsort(X.T, axis=1).astype(np.int32).T)

        # fit initial model
        self.init.fit(X, y)

        # init predictions
        y_pred = self.init.predict(X)

        self.estimators_ = []

        self.train_deviance = np.zeros((self.n_estimators,), dtype=np.float64)
        self.oob_deviance = np.zeros((self.n_estimators), dtype=np.float64)

        sample_mask = np.ones((n_samples,), dtype=np.bool)

        # perform boosting iterations
        for i in xrange(self.n_estimators):

            # subsampling
            if self.subsample < 1.0:
                sample_mask = self.random_state.rand(n_samples) \
                              >= (1.0 - self.subsample)

            residual = loss.negative_gradient(y, y_pred)

            # induce regression tree on residuals
            tree = _build_tree(X, residual, MSE(), self.max_depth,
                               self.min_samples_split, self.min_samples_leaf,
                               0.0, n_features, self.random_state,
                               1, _find_best_split, sample_mask,
                               X_argsorted, True)

            # update tree leafs
            loss.update_terminal_regions(tree, X, y, residual, y_pred,
                                         self.learn_rate)

            # add tree to ensemble
            self.estimators_.append(tree)

            # update out-of-bag predictions and deviance
            if self.subsample < 1.0:
                y_pred[~sample_mask] = self._predict(
                    X[~sample_mask], old_pred=y_pred[~sample_mask])
                self.oob_deviance[i] = loss(y[~sample_mask],
                                            y_pred[~sample_mask])

            self.train_deviance[i] = loss(y[sample_mask], y_pred[sample_mask])

            if monitor:
                stop = monitor(self, i)
                if stop:
                    break

        return self

    def _predict(self, X, old_pred=None):
        """Predict targets with current model. Re-uses predictions
        from previous iteration if available.
        """
        if old_pred is not None:
            return old_pred + self.learn_rate * \
                   self.estimators_[-1].predict(X).ravel()
        else:
            y = self.init.predict(X)
            for tree in self.estimators_:
                y += self.learn_rate * tree.predict(X).ravel()
            return y

    def _make_estimator(self, append=True):
        raise NotImplementedError()

    @property
    def feature_importances_(self):
        if not self.estimators_ or len(self.estimators_) == 0:
            raise ValueError("Estimator not fitted, " \
                             "call `fit` before `feature_importances_`.")
        importances = sum(compute_feature_importances(tree, self.n_features,
                                                      method='squared')
                          for tree in self.estimators_) / len(self.estimators_)
        importances = 100.0 * (importances / importances.max())
        return importances


class GradientBoostingClassifier(BaseGradientBoosting, ClassifierMixin):
    """Gradient Boosting for classification. GB builds an additive model in a
    forward stage-wise fashion; it allows for the optimization of
    arbitrary differentiable loss functions. In each stage a regression
    tree is fit on the negative gradient of binomial or multinomial
    deviance.

    Parameters
    ----------
    n_estimators : int (default=100)
        The number of boosting stages to perform. Gradient boosting
        is fairly robust to over-fitting so a large number usually
        results in better performance.

    learn_rate : float, optional (default=0.1)
        learning rate shrinks the contribution of each tree by `learn_rate`.
        There is a trade-off between learn_rate and n_estimators (see Discussion).

    max_depth : integer, optional (default=3)
        maximum depth of the individual regression estimators. The maximum
        depth limits the number of nodes in the tree. Tune this parameter
        for best performance; the best value depends on the interaction
        of the input variables.

    min_samples_split : integer, optional (default=1)
        The minimum number of samples required to split an internal node.

    min_samples_leaf : integer, optional (default=1)
        The minimum number of samples required to be at a leaf node.

    subsample : float, optional (default=1.0)
        The fraction of samples to be used for fitting the individual base
        learners. If smaller than 1.0 this results in Stochastic Gradient
        Boosting. `subsample` interacts with the parameter `n_estimators`
        (see Discussion).

    Examples
    --------
    >>> samples = [[0, 0, 2], [1, 0, 0]]
    >>> labels = [0, 1]
    >>> from sklearn.ensemble import GradientBoostingClassifier
    >>> gb = GradientBoostingClassifier().fit(samples, labels)
    >>> print gb.predict([[0.5, 0, 0]])
    [0]

    See also
    --------
    DecisionTreeClassifier, RandomForestClassifier

    Discussion
    ----------
    The optimal algorithm for a given dataset is a complicated choice, and
    depends on a number of factors:
    * n_estimators vs. learn_rate
        TODO
    * n_estimators vs. subsample
        TODO

    References
    ----------
    J. Friedman, Greedy Function Approximation: A Gradient Boosting
    Machine, The Annals of Statistics, Vol. 29, No. 5, 2001.

    J. Friedman, Stochastic Gradient Boosting, 1999

    T. Hastie, R. Tibshirani and J. Friedman.
    Elements of Statistical Learning Ed. 2, Springer, 2009.
    """

    def __init__(self, loss='deviance', learn_rate=0.1, n_estimators=100,
                 subsample=1.0, min_samples_split=1, min_samples_leaf=1,
                 max_depth=3, init=None, random_state=None):

        super(GradientBoostingClassifier, self).__init__(
            loss, learn_rate, n_estimators, min_samples_split, min_samples_leaf,
            max_depth, init, subsample, random_state)

    def fit(self, X, y, monitor=None):
        """Fit the gradient boosting model.

        Parameters
        ----------
        X : array-like, shape = [n_samples, n_features]
            Training vectors, where n_samples is the number of samples
            and n_features is the number of features. Use fortran-style
            to avoid memory copies.

        y : array-like, shape = [n_samples]
            Target values (integers in classification, real numbers in
            regression)
            For classification, labels must correspond to classes
            0, 1, ..., n_classes-1

        Returns
        -------
        self : object
            Returns self.
        """
        self.classes = np.unique(y)
        if self.classes.shape[0] != 2:
            raise ValueError("only binary classification supported")
        y = np.searchsorted(self.classes, y)
        return super(GradientBoostingClassifier, self).fit(X, y,
                                                           monitor=monitor)

    def predict(self, X):
        X = np.atleast_2d(X)
        X = X.astype(DTYPE)
        if len(self.estimators_) == 0:
            raise ValueError("Estimator not fitted, " \
                             "call `fit` before `predict`.")
        f = self._predict(X)
        return self.classes.take(f >= 0.0, axis=0)

    def predict_proba(self, X):
        X = np.atleast_2d(X)
        X = X.astype(DTYPE)
        if len(self.estimators_) == 0:
            raise ValueError("Estimator not fitted, " \
                             "call `fit` before `predict_proba`.")
        f = self._predict(X)
        P = np.ones((X.shape[0], 2), dtype=np.float64)
        P[:, 1] = 1.0 / (1.0 + np.exp(-f))
        P[:, 0] -= P[:, 1]
        return P


class GradientBoostingRegressor(BaseGradientBoosting, RegressorMixin):
    """Gradient Boosting for regression. GB builds an additive model in a
    forward stage-wise fashion; it allows for the optimization of
    arbitrary differentiable loss functions. In each stage a regression
    tree is fit on the negative gradient of the given loss function.

    Parameters
    ----------
    n_estimators : int (default=100)
        The number of boosting stages to perform. Gradient boosting
        is fairly robust to over-fitting so a large number usually
        results in better performance.

    learn_rate : float, optional (default=0.1)
        learning rate shrinks the contribution of each tree by `learn_rate`.
        There is a trade-off between learn_rate and n_estimators.

    loss : {'ls', 'lad'}, optional
        loss function to be optimized. 'ls' refers to least squares
        regression. 'lad' (least absolute deviation) is a highly robust
        loss function soley based on order information of the input
        variables.

    max_depth : integer, optional (default=3)
        maximum depth of the individual regression estimators. The maximum
        depth limits the number of nodes in the tree. Tune this parameter
        for best performance; the best value depends on the interaction
        of the input variables.

    min_samples_split : integer, optional (default=1)
        The minimum number of samples required to split an internal node.

    min_samples_leaf : integer, optional (default=1)
        The minimum number of samples required to be at a leaf node.

    subsample : float, optional (default=1.0)
        The fraction of samples to be used for fitting the individual base
        learners. If smaller than 1.0 this results in Stochastic Gradient
        Boosting. `subsample` interacts with the parameter `n_estimators`
        (see Discussion).

    Examples
    --------
    >>> samples = [[0, 0, 2], [1, 0, 0]]
    >>> labels = [0, 1]
    >>> from sklearn.ensemble import GradientBoostingRegressor
    >>> gb = GradientBoostingRegressor().fit(samples, labels)
    >>> print gb.predict([[0, 0, 0]])    # doctest: +ELLIPSIS
    [  1.32806997e-05]

    See also
    --------
    DecisionTreeRegressor, RandomForestRegressor

    References
    ----------
    J. Friedman, Greedy Function Approximation: A Gradient Boosting
    Machine, The Annals of Statistics, Vol. 29, No. 5, 2001.

    J. Friedman, Stochastic Gradient Boosting, 1999

    T. Hastie, R. Tibshirani and J. Friedman.
    Elements of Statistical Learning Ed. 2, Springer, 2009.
    """

    def __init__(self, loss='ls', learn_rate=0.1, n_estimators=100, subsample=1.0,
                 min_samples_split=1, min_samples_leaf=1, max_depth=3,
                 init=None, random_state=None):

        super(GradientBoostingRegressor, self).__init__(
            loss, learn_rate, n_estimators, min_samples_split, min_samples_leaf,
            max_depth, init, subsample, random_state)

    def predict(self, X):
        X = np.atleast_2d(X)
        X = X.astype(DTYPE)
        if len(self.estimators_) == 0:
            raise ValueError("Estimator not fitted, " \
                             "call `fit` before `predict`.")
        y = self._predict(X)
        return y
