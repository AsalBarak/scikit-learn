"""
A comparison of different methods in GLM

Data comes from a random square matrix.

"""
from datetime import datetime
import numpy as np
from scikits.learn import glm
import pylab as pl


if __name__ == '__main__':

    
    n_iter = 20

    time_ridge   = np.empty (n_iter)
    time_ols     = np.empty (n_iter)
    time_lasso   = np.empty (n_iter)

    dimensions = 10 * np.arange(n_iter)

    for i in range(n_iter):

        print 'Iteration %s of %s' % (i, n_iter)

        n, m = 10*i + 3, 10*i + 3

        X = np.random.randn (n, m) 
        Y = np.random.randn (n)

        start = datetime.now()
        ridge = glm.Ridge(alpha=0.)
        ridge.fit (X, Y)
        time_ridge[i] = (datetime.now() - start).total_seconds()

        start = datetime.now()
        ols = glm.LinearRegression()
        ols.fit (X, Y)
        time_ols[i] = (datetime.now() - start).total_seconds()


        start = datetime.now()
        lasso = glm.LassoLARS()
        lasso.fit (X, Y)
        time_lasso[i] = (datetime.now() - start).total_seconds()

        

    pl.xlabel ('Dimesions')
    pl.ylabel ('Time (in seconds)')
    pl.plot (dimensions, time_ridge, color='r')
    pl.plot (dimensions, time_ols, color='g')
    pl.plot (dimensions, time_lasso, color='b')

    pl.legend (['Ridge', 'OLS', 'LassoLARS'])
    pl.axis ('tight')
    pl.show()
