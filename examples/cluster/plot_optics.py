"""
===================================
Demo of OPTICS clustering algorithm
===================================

Finds core samples of high density and expands clusters from them.
"""
from sklearn.datasets.samples_generator import make_blobs
from sklearn.preprocessing import StandardScaler
from sklearn.cluster.optics import OPTICS

##############################################################################
# Generate sample data
centers = [[1, 1], [-1, -1], [1, -1]]
X, labels_true = make_blobs(n_samples=750, centers=centers, 
                            cluster_std=0.4, random_state=0)

##############################################################################

##############################################################################
# Compute OPTICS
# Note the large eps; seeding problems when eps is close to
# desired epsPrime 

clust = OPTICS(eps=0.3, min_samples=10)

# Run the fit

clust.fit(X)

##############################################################################
# Plot result

core_samples_mask = np.zeros_like(clust.labels_, dtype=bool)
core_samples_mask[clust.core_samples] = True

import matplotlib.pyplot as plt

# Black removed and is used for noise instead.
unique_labels = set(clust.labels_)
colors = plt.cm.Spectral(np.linspace(0, 1, len(unique_labels)))
for k, col in zip(unique_labels, colors):
    if k == -1:
        # Black used for noise.
        col = 'k'

    class_member_mask = (clust.labels_ == k)

    xy = X[class_member_mask & core_samples_mask]
    plt.plot(xy[:, 0], xy[:, 1], 'o', markerfacecolor=col,
             markeredgecolor='k', markersize=14)

    xy = X[class_member_mask & ~core_samples_mask]
    plt.plot(xy[:, 0], xy[:, 1], 'o', markerfacecolor=col,
             markeredgecolor='k', markersize=6)

plt.title('Estimated number of clusters: %d' % clust.n_clusters)
plt.show()

# (Re)-extract clustering structure. This can be run for any clustering distance, 
# and can be run multiple times without rerunning OPTICS
# OPTICS does need to be re-run to change the min-pts parameter

clust.extract(.11)


core_samples_mask = np.zeros_like(clust.labels_, dtype=bool)
core_samples_mask[clust.core_samples] = True

# Black removed and is used for noise instead.
unique_labels = set(clust.labels_)
colors = plt.cm.Spectral(np.linspace(0, 1, len(unique_labels)))
for k, col in zip(unique_labels, colors):
    if k == -1:
        # Black used for noise.
        col = 'k'

    class_member_mask = (clust.labels_ == k)

    xy = X[class_member_mask & core_samples_mask]
    plt.plot(xy[:, 0], xy[:, 1], '.', markerfacecolor=col,
             markeredgecolor='k', markersize=14, alpha=0.5)

    xy = X[class_member_mask & ~core_samples_mask]
    plt.plot(xy[:, 0], xy[:, 1], '.', markerfacecolor=col,
             markeredgecolor='k', markersize=6, alpha=0.5)

plt.title('Estimated number of clusters: %d' % clust.n_clusters)
plt.show()
