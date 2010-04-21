import numpy as np
from . import liblinear


class LogisticRegression(object):

    def __init__(self, penalty='l2', eps=1e-4, C=1.0):
        self.solver_type = self._penalties[penalty]
        self.eps = eps
        self.C = C

    _penalties = {'l2': 0, 'l1' : 6}
    _weight_label = np.empty(0, dtype=np.int32)
    _weight = np.empty(0, dtype=np.float64)

    def fit(self, X, Y):
        X = np.asanyarray(X, dtype=np.float64, order='C')
        Y = np.asanyarray(Y, dtype=np.int32, order='C')
        self.coef_with_intercept_, self.label_, self.bias_ = liblinear.train_wrap(X,
                                          Y, self.solver_type, self.eps, 1.0,
                                          self.C, 0,
                                          self._weight_label,
                                          self._weight)

    def predict(self, T):
        T = np.asanyarray(T, dtype=np.float64, order='C')
        return liblinear.predict_wrap(T, self.coef_with_intercept_, self.solver_type,
                                      self.eps, self.C,
                                      self._weight_label,
                                      self._weight, self.label_,
                                      self.bias_)

    def predict_proba(self, T):
        T = np.asanyarray(T, dtype=np.float64, order='C')
        return liblinear.predict_prob_wrap(T, self.coef_with_intercept_, self.solver_type,
                                      self.eps, self.C,
                                      self._weight_label,
                                      self._weight, self.label_,
                                      self.bias_)

    @property
    def intercept_(self):
        return self.coef_with_intercept_[:,-1]

    @property
    def coef_(self):
        return self.coef_with_intercept_[:,:-1]

