"""
Naive Bayes models
==================

Naive Bayes algorithms are a set of supervised learning methods based on
applying Bayes' theorem with strong (naive) independence assumptions.

See http://scikit-learn.sourceforge.net/modules/naive_bayes.html for
complete documentation.
"""

# Author: Vincent Michel <vincent.michel@inria.fr>
#         Minor fixes by Fabian Pedregosa
#         MultinomialNB classifier by:
#         Amit Aides <amitibo@tx.technion.ac.il>
#         Yehuda Finkelstein <yehudaf@tx.technion.ac.il>
#         Lars Buitinck <L.J.Buitinck@uva.nl>
#         (parts based on earlier work by Mathieu Blondel)
#
# License: BSD Style.

from .base import BaseEstimator, ClassifierMixin
from .utils import safe_asanyarray
import numpy as np
from scipy.sparse import issparse


class GNB(BaseEstimator, ClassifierMixin):
    """
    Gaussian Naive Bayes (GNB)

    Parameters
    ----------
    X : array-like, shape = [n_samples, n_features]
        Training vector, where n_samples in the number of samples and
        n_features is the number of features.

    y : array, shape = [n_samples]
        Target vector relative to X

    Attributes
    ----------
    proba_y : array, shape = [n_classes]
        probability of each class.

    theta : array, shape [n_classes * n_features]
        mean of each feature for the different class

    sigma : array, shape [n_classes * n_features]
        variance of each feature for the different class

    Methods
    -------
    fit(X, y) : self
        Fit the model

    predict(X) : array
        Predict using the model.

    predict_proba(X) : array
        Predict the probability of each class using the model.

    predict_log_proba(X) : array
        Predict the log-probability of each class using the model.


    Examples
    --------
    >>> import numpy as np
    >>> X = np.array([[-1, -1], [-2, -1], [-3, -2], [1, 1], [2, 1], [3, 2]])
    >>> Y = np.array([1, 1, 1, 2, 2, 2])
    >>> from scikits.learn.naive_bayes import GNB
    >>> clf = GNB()
    >>> clf.fit(X, Y)
    GNB()
    >>> print clf.predict([[-0.8, -1]])
    [1]

    See also
    --------

    """

    def fit(self, X, y):
        """Fit Gaussian Naive Bayes according to X, y

        Parameters
        ----------
        X : array-like, shape = [n_samples, n_features]
            Training vectors, where n_samples is the number of samples
            and n_features is the number of features.

        y : array-like, shape = [n_samples]
            Target values.

        Returns
        -------
        self : object
            Returns self.
        """

        X = np.asanyarray(X)
        y = np.asanyarray(y)

        theta = []
        sigma = []
        proba_y = []
        unique_y = np.unique(y)
        for yi in unique_y:
            theta.append(np.mean(X[y == yi, :], 0))
            sigma.append(np.var(X[y == yi, :], 0))
            proba_y.append(np.float(np.sum(y == yi)) / np.size(y))
        self.theta = np.array(theta)
        self.sigma = np.array(sigma)
        self.proba_y = np.array(proba_y)
        self.unique_y = unique_y
        return self

    def predict(self, X):
        """
        Perform classification on an array of test vectors X.

        Parameters
        ----------
        X : array-like, shape = [n_samples, n_features]

        Returns
        -------
        C : array, shape = [n_samples]
        """
        X = np.asanyarray(X)
        y_pred = self.unique_y[np.argmax(self.predict_proba(X), 1)]
        return y_pred

    def _joint_log_likelihood(self, X):
        joint_log_likelihood = []
        for i in xrange(np.size(self.unique_y)):
            jointi = np.log(self.proba_y[i])
            n_ij = - 0.5 * np.sum(np.log(np.pi * self.sigma[i, :]))
            n_ij -= 0.5 * np.sum(((X - self.theta[i, :]) ** 2) / \
                                    (self.sigma[i, :]), 1)
            joint_log_likelihood.append(jointi + n_ij)
        joint_log_likelihood = np.array(joint_log_likelihood).T
        return joint_log_likelihood

    def predict_proba(self, X):
        """
        Return probability estimates for the test vector X.

        Parameters
        ----------
        X : array-like, shape = [n_samples, n_features]

        Returns
        -------
        C : array-like, shape = [n_samples, n_classes]
            Returns the probability of the sample for each class in
            the model, where classes are ordered by arithmetical
            order.
        """
        X = np.asanyarray(X)
        joint_log_likelihood = self._joint_log_likelihood(X)
        proba = np.exp(joint_log_likelihood)
        proba = proba / np.sum(proba, 1)[:, np.newaxis]
        return proba

    def predict_log_proba(self, X):
        """
        Return log-probability estimates for the test vector X.

        Parameters
        ----------
        X : array-like, shape = [n_samples, n_features]

        Returns
        -------
        C : array-like, shape = [n_samples, n_classes]
            Returns the log-probability of the sample for each class
            in the model, where classes are ordered by arithmetical
            order.
        """
        log_proba = self._joint_log_likelihood(X)
        # Compute a sum of logs without underflow. Equivalent to:
        # log_proba -= np.log(np.sum(np.exp(log_proba), axis=1))[:, np.newaxis]
        B = np.max(log_proba, axis=1)[:, np.newaxis]
        logaB = log_proba - B
        sup = logaB > -np.inf
        aB = np.zeros_like(logaB)
        aB[sup] = np.exp(logaB[sup])
        log_proba -= np.log(np.sum(aB, axis=1))[:, np.newaxis] + B
        return log_proba


def asanyarray_or_csr(X):
    if issparse(X):
        return X.tocsr(), True
    else:
        return np.asanyarray(X), False


def atleast2d_or_csr(X):
    if issparse(X):
        return X.tocsr()
    else:
        return np.atleast_2d(X)


class MultinomialNB(BaseEstimator, ClassifierMixin):
    """
    Naive Bayes classifier for multinomial models

    The multinomial Naive Bayes classifier is suitable for text classification.
    This class is designed to handle both dense and sparse data; it will enter
    "sparse mode" if its training matrix (X) is a sparse matrix.

    Parameters
    ----------
    alpha: float, optional (default=1.0)
        Additive (Laplace/Lidstone) smoothing parameter
        (0 for no smoothing).
    use_prior: boolean
        Whether to use label prior probabilities or not.

    Methods
    -------
    fit(X, y) : self
        Fit the model

    predict(X) : array
        Predict using the model.

    predict_proba(X) : array
        Predict the probability of each label using the model.

    predict_log_proba(X) : array
        Predict the log probability of each label using the model.

    Examples
    --------
    >>> import numpy as np
    >>> X = np.random.randint(5, size=(6, 100))
    >>> Y = np.array([1, 2, 3, 4, 5, 6])
    >>> from scikits.learn.naive_bayes import MultinomialNB
    >>> clf = MultinomialNB()
    >>> clf.fit(X, Y)
    MultinomialNB(alpha=1.0, use_prior=True)
    >>> print clf.predict(X[2])
    [3]
    """

    def __init__(self, alpha=1.0, use_prior=True):
        self.alpha = alpha
        self.use_prior = use_prior

    def fit(self, X, y, theta=None):
        """Fit Multinomial Naive Bayes according to X, y

        Parameters
        ----------
        X : array-like, shape = [n_samples, n_features]
            Training vectors, where n_samples is the number of samples
            and n_features is the number of features.

        y : array-like, shape = [n_samples]
            Target values.

        theta : array, shape [n_labels * n_features]
            Prior probability per label.

        Returns
        -------
        self : object
            Returns self.
        """
        X, self.sparse = asanyarray_or_csr(X)
        y = safe_asanyarray(y)

        self.unique_y = np.unique(y)
        n_labels = self.unique_y.size

        self.theta = None
        if not self.use_prior:
            self.theta = np.ones(n_labels) / n_labels
        if theta:
            assert len(theta) == n_labels, \
                   'Number of priors must match number of labels'
            self.theta = np.array(theta)

        # N_c is the count of all words in all documents of label c.
        # N_c_i is the a count of word i in all documents of label c.
        # theta[c] is the prior empirical probability of a document of label c.
        # theta_c_i is the (smoothed) empirical likelihood of word i
        # given a document of label c.
        #
        N_c_i_temp = []
        if self.theta is None:
            theta = []

        for yi in self.unique_y:
            if self.sparse:
                row_ind = np.nonzero(y == yi)[0]
                N_c_i_temp.append(np.array(X[row_ind, :].sum(axis=0)).ravel())
            else:
                N_c_i_temp.append(np.sum(X[y == yi, :], 0))
            if self.theta is None:
                theta.append(np.float(np.sum(y == yi)) / y.size)

        N_c_i = np.array(N_c_i_temp)
        N_c = np.sum(N_c_i, axis=1)

        # Smoothing coefficients
        #
        alpha_i = self.alpha
        alpha = alpha_i * X.shape[1]

        # Estimate the parameters of the distribution
        #
        self.theta_c_i = (np.log(N_c_i + alpha_i)
                         - np.log(N_c.reshape(-1, 1) + alpha))
        if self.theta is None:
            self.theta = np.array(theta)

        return self

    def predict(self, X):
        """
        Perform classification on an array of test vectors X.

        Parameters
        ----------
        X : array-like, shape = [n_samples, n_features]

        Returns
        -------
        C : array, shape = [n_samples]
        """
        joint_log_likelihood = self._joint_log_likelihood(X)
        y_pred = self.unique_y[np.argmax(joint_log_likelihood, axis=0)]

        return y_pred

    def _joint_log_likelihood(self, X):
        """Calculate the posterior log probability of the samples X"""

        X = atleast2d_or_csr(X)

        joint_log_likelihood = []
        for i in xrange(self.unique_y.size):
            if self.sparse:
                n_ij = self.theta_c_i[i] * X.T
            else:
                n_ij = np.dot(self.theta_c_i[i], X.T)
            n_ij += np.log(self.theta[i])
            joint_log_likelihood.append(n_ij)

        return np.array(joint_log_likelihood)

    def predict_proba(self, X):
        """
        Return probability estimates for the test vector X.

        Parameters
        ----------
        X : array-like, shape = [n_samples, n_features]

        Returns
        -------
        C : array-like, shape = [n_samples, n_labels]
            Returns the probability of the sample for each label in
            the model, where labels are ordered by arithmetical
            order.
        """
        return np.exp(self.predict_log_proba(X))

    def predict_log_proba(self, X):
        """
        Return log-probability estimates for the test vector X.

        Parameters
        ----------
        X : array-like, shape = [n_samples, n_features]

        Returns
        -------
        C : array-like, shape = [n_samples, n_labels]
            Returns the log-probability of the sample for each label
            in the model, where labels are ordered by arithmetical
            order.
        """
        jll = self._joint_log_likelihood(X)
        # normalize by P(x) = P(f_1, ..., f_n)
        normalize = np.logaddexp.reduce(jll[:, np.newaxis])
        return jll - normalize
