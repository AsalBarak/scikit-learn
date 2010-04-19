#include <stdlib.h>
#include <numpy/arrayobject.h>
#include "linear.h"

/*
 * Convert matrix to sparse representation suitable for libsvm. x is
 * expected to be an array of length nrow*ncol.
 *
 * Typically the matrix will be dense, so we speed up the routine for
 * this case. We create a temporary array temp that collects non-zero
 * elements and after we just memcpy that to the proper array.
 *
 * Special care must be taken with indices, since libsvm indices start
 * at 1 and not at 0.
 *
 */
struct feature_node **dense_to_sparse (double *x, npy_intp *dims)
{
    struct feature_node **sparse;
    register int i, j;              /* number of nonzero elements in row i */
    struct feature_node *temp;          /* stack for nonzero elements */
    struct feature_node *T;             /* pointer to the top of the stack */
    int count;

    sparse = (struct feature_node **) malloc (dims[0] * sizeof(struct feature_node *));
    temp = (struct feature_node *) malloc ((dims[1]+2) * sizeof(struct feature_node));

    if (sparse == NULL || temp == NULL) return NULL;

    for (i=0; i<dims[0]; ++i) {
        T = temp; /* reset stack pointer */

        for (j=1; j<=dims[1]; ++j) {
            T->value = *x;
            if (T->value != 0) {
                T->index = j;
                ++ T;
            }
            ++ x; /* go to next element */
        }

        /* set bias element */
        T->value = 1.0;
        T->index = j;
        ++ T;

        /* set sentinel */
        T->index = -1;
        ++ T;

        /* allocate memory and copy collected items*/
        count = T - temp;
        sparse[i] = (struct feature_node *) malloc(count * sizeof(struct feature_node));
        if (sparse[i] == NULL) return NULL;
        memcpy(sparse[i], temp, count * sizeof(struct feature_node));
    }

    free(temp);
    return sparse;
}

struct feature_node **dense_to_sparse_nobias (double *x, npy_intp *dims)
{
    struct feature_node **sparse;
    register int i, j;              /* number of nonzero elements in row i */
    struct feature_node *temp;          /* stack for nonzero elements */
    struct feature_node *T;             /* pointer to the top of the stack */
    int count;

    sparse = (struct feature_node **) malloc (dims[0] * sizeof(struct feature_node *));
    temp = (struct feature_node *) malloc ((dims[1]+1) * sizeof(struct feature_node));

    if (sparse == NULL || temp == NULL) return NULL;

    for (i=0; i<dims[0]; ++i) {
        T = temp; /* reset stack pointer */

        for (j=1; j<=dims[1]; ++j) {
            T->value = *x;
            if (T->value != 0) {
                T->index = j;
                ++T;
            }
            ++x; /* go to next element */
        }

        /* set sentinel */
        T->index = -1;
        ++T;

        /* allocate memory and copy collected items*/
        count = T - temp;
        sparse[i] = (struct feature_node *) malloc(count * sizeof(struct feature_node));
        if (sparse[i] == NULL) return NULL;
        memcpy(sparse[i], temp, count * sizeof(struct feature_node));
    }

    free(temp);
    return sparse;
}

struct problem * set_problem(char *X,char *Y, npy_intp *dims, double bias)
{
    struct problem *problem;
    /* not performant, but its the simpler way */
    problem = (struct problem *) malloc(sizeof(struct problem));
    if (problem == NULL) return NULL;
    problem->l = (int) dims[0];

    if (bias > 0) {
        problem->n = (int) dims[1] + 1;
    } else {
        problem->n = (int) dims[1];
    }
    problem->y = (int *) Y;
    problem->x = dense_to_sparse((double *) X, dims); /* TODO: free */
    problem->bias = bias;
    if (problem->x == NULL) { 
        free(problem);
        return NULL;
    }
    return problem;
}


/* Create a paramater struct with and return it */
struct parameter * set_parameter(int solver_type, double eps, double C, npy_intp nr_weight, char *weight_label, char *weight)
{
    struct parameter *param;
    param = (struct parameter *) malloc(sizeof(struct parameter));
    if (param == NULL) return NULL;
    param->solver_type = solver_type;
    param->eps = eps;
    param->C = C;
    param->nr_weight = (int) nr_weight;
    param->weight_label = (int *) weight_label;
    param->weight = (double *) weight;
    return param;
}

struct model * set_model(struct parameter *param, char *coef, npy_intp *dims, 
                         char *label, double bias)
{
    npy_int len_w = dims[0] * dims[1];
    struct model *model;

    model = (struct model *)  malloc(sizeof(struct model));
    model->w =       (double *)   malloc( len_w * sizeof(double)); 
    model->label =   (int *)      malloc( dims[0] * sizeof(int));;

    memcpy(model->label, label, dims[0] * sizeof(int));
    memcpy(model->w, coef, len_w * sizeof(double));

    model->nr_class = (int) dims[1];

    int m = (int) dims[0];
    model->nr_feature = bias > 0 ? m - 1 : m;
    model->param = *param;
    model->bias = bias;

    return model;
}

void copy_w(char *data, struct model *model, int len)
{
    memcpy(data, model->w, len * sizeof(double));
}

double get_bias(struct model *model)
{
    return model->bias;
}

void free_problem(struct problem *problem)
{
    int i;
    for(i=problem->l-1; i>=0; --i) free(problem->x[i]);
    free(problem->x);
}

void free_parameter(struct parameter *param)
{
    free(param);
}

int copy_predict(char *train, struct model *model, npy_intp *train_dims,
                 char *dec_values)
{
    int *t = (int *) dec_values;
    register int i, n;
    n = train_dims[0];
    struct feature_node **train_nodes;
    train_nodes = dense_to_sparse((double *) train, train_dims);
    if (train_nodes == NULL)
        return -1;
    for(i=0; i<n; ++i) {
        *t = predict(model, train_nodes[i]);
        free(train_nodes[i]);
        ++t;
    }
    return 0;
}

int copy_label(char *data, struct model *model_, int nr_class)
{
    memcpy(data, model_->label, nr_class * sizeof(int));
    return 0;
}
