"""
Orthogonal matching pursuit algorithms based on
http://www.cs.technion.ac.il/~ronrubin/Publications/KSVD-OMP-v2.pdf
"""

# Author: Vlad Niculae
#
# License: BSD Style.

import numpy as np
from scipy import linalg

def _cholesky_omp(D, y, n_atoms, eps=None):
    """
    D: array of shape (n_samples, n_features)
        Input dictionary

    y: array, shape: n_samples
        Input targets
    """
    if eps == None:
        stopping_condition = lambda: it == n_atoms  # len(idx) == n_atoms
    else:
        stopping_condition = lambda: np.dot(residual.T, residual) <= eps
    
    # initializations
    alpha = np.dot(D.T, y)
    residual = y
    it = 0
    idx = []
    L = np.ones((1, 1))

    while not stopping_condition():
        lam = np.abs(np.dot(D.T, residual)).argmax()
        if len(idx) > 0:
            w = linalg.solve_triangular(L, np.dot(D[:, idx].T, D[:, lam]),
                                        lower=True, unit_diagonal=True)
            # Updates the Cholesky decomposition of D' D
            L = np.r_[np.c_[L, np.zeros(len(L))],
                      np.atleast_2d(np.append(w, np.sqrt(1 - np.dot(w.T, w))))]
        idx.append(lam)
        it += 1
        # solves LL'x = y as a composition of two triangular systems
        Lc = linalg.solve_triangular(L, alpha[idx], lower=True)
        gamma = linalg.solve_triangular(L, Lc, trans=1, lower=True)
        residual = y - np.dot(D[:, idx], gamma)
    
    return gamma, idx

def _gram_omp(G, Dy, n_atoms, eps_0=None, eps=None):
    idx = []
    L = np.ones((1, 1))
    alpha = Dy
    eps_curr = eps_0
    delta = 0
    it = 0
    if eps == None:
        stopping_condition = lambda: it == n_atoms
    else:
        stopping_condition = lambda: eps_curr <= eps

    while not stopping_condition():
        lam = np.abs(alpha).argmax()
        if len(idx) > 0:
            w = linalg.solve_triangular(L, G[idx, lam],
                                        lower=True, unit_diagonal=True)
            L = np.r_[np.c_[L, np.zeros(len(L))],
                      np.atleast_2d(np.append(w, np.sqrt(1 - np.inner(w, w))))]
        idx.append(lam)
        it += 1
        Lc = linalg.solve_triangular(L, Dy[idx], lower=True)
        gamma = linalg.solve_triangular(L, Lc, trans=1, lower=True) 
        beta = np.dot(G[:, idx], gamma)        
        alpha = Dy - beta
        if eps != None:
            eps_curr += delta
            delta = np.inner(gamma, beta[idx])
            eps_curr -= delta
    return gamma, idx

def orthogonal_mp(D, y, n_atoms=None, eps=None, compute_gram=False):
    """
    D: array of shape (n_samples, n_features)
        Input dictionary

    y: array, shape: n_samples or (n_targets, n_samples)
        Input targets

    n_atoms: int
        Desired number of non-zero entries in the solution
    
    eps: float
        Maximum norm of the residual. If not None, overrides n_atoms.
    
    compute_gram, bool:
        Whether to perform precomputations. Improves performance when n_targets
        or n_samples is very large.
    """
    D = np.asanyarray(D)
    y = np.atleast_2d(y)
    if n_atoms == None and eps == None:
        raise ValueError('OMP needs either a target number of atoms (n_atoms) \
                         or a target residual error (eps)')
    if compute_gram:
        G = np.dot(D.T, D)
        Dy = np.dot(y, D)
        if eps != None:
            norms_squared = np.sum((y ** 2), axis=0)
        else:
            norms_squared = None
        return orthogonal_mp_gram(G, Dy, n_atoms, eps, norms_squared)

    X = np.zeros((len(y), D.shape[1]))
    for k in xrange(len(y)):
        x, idx = _cholesky_omp(D, y[k], n_atoms, eps)
        X[k, idx] = x
    return np.squeeze(X)

def orthogonal_mp_gram(G, Dy, n_atoms=None, eps=None, norms_squared=None):
    """
    G: array of shape (n_features, n_features)
        Gram matrix of the input data: D.T * D

    Dy: array, shape: n_features or (n_targets, n_features)
        Input targets multiplied by D

    n_atoms: int
        Desired number of non-zero entries in the solution
    
    eps: float
        Maximum norm of the residual. If not None, overrides n_atoms.
    
    norms_squared: array, shape: n_targets
        Squared L2 norms of the lines of y. Required if eps is not None.
    """
    if n_atoms == None and eps == None:
        raise ValueError('OMP needs either a target number of atoms (n_atoms) \
                         or a target residual error (eps)')
    if eps != None and norms_squared == None:
        raise ValueError('Gram OMP needs the precomputed norms in order \
                          to evaluate the error sum of squares.')
    X = np.zeros((len(Dy), len(G)))
    for k in range(len(Dy)):
        x, idx = _gram_omp(G, Dy[k], n_atoms,
                           norms_squared[k] if eps else None, eps)
        X[k, idx] = x
    return np.squeeze(X)
