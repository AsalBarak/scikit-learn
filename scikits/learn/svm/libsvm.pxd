cimport numpy as np

################################################################################
# Includes

cdef extern from "svm.h":
    cdef struct svm_node
    cdef struct svm_model
    cdef struct svm_parameter:
        int svm_type
        int kernel_type
        int degree	# for poly
        double gamma	# for poly/rbf/sigmoid
        double coef0	# for poly/sigmoid

        # these are for training only
        double cache_size # in MB
        double eps	# stopping criteria
        double C	# for C_SVC, EPSILON_SVR and NU_SVR
        int nr_weight		# for C_SVC
        int *weight_label	# for C_SVC
        double* weight		# for C_SVC
        double nu	# for NU_SVC, ONE_CLASS, and NU_SVR
        double p	# for EPSILON_SVR
        int shrinking	# use the shrinking heuristics
        int probability # do probability estimates

    cdef struct svm_problem:
        int l
        double *y
        svm_node *x
        double *W # instance weights

    char *svm_check_parameter(svm_problem *, svm_parameter *)
    svm_model *svm_train(svm_problem *, svm_parameter *)
    void svm_free_and_destroy_model(svm_model** model_ptr_ptr)
    void svm_cross_validation(svm_problem *, svm_parameter *, int nr_fold, double *target)


cdef extern from "libsvm_helper.c":
    # this file contains methods for accessing libsvm 'hidden' fields
    svm_node **dense_to_sparse (char *, np.npy_intp *)
    void set_parameter (svm_parameter *, int , int , int , double, double ,
                                  double , double , double , double,
                                  double, int, int, int, char *, char *)
    void set_problem (svm_problem *, char *, char *, char *, np.npy_intp *, int)

    svm_model *set_model (svm_parameter *, int, char *, np.npy_intp *,
                         char *, np.npy_intp *, np.npy_intp *, char *,
                         char *, char *, char *, char *, char *)

    void copy_sv_coef   (char *, svm_model *)
    void copy_intercept (char *, svm_model *, np.npy_intp *)
    void copy_SV        (char *, svm_model *, np.npy_intp *)
    int copy_support (char *data, svm_model *model)
    int copy_predict (char *, svm_model *, np.npy_intp *, char *)
    int copy_predict_proba (char *, svm_model *, np.npy_intp *, char *)
    int copy_predict_values(char *, svm_model *, np.npy_intp *, char *, int)
    void copy_nSV     (char *, svm_model *)
    void copy_label   (char *, svm_model *)
    void copy_probA   (char *, svm_model *, np.npy_intp *)
    void copy_probB   (char *, svm_model *, np.npy_intp *)
    np.npy_intp  get_l  (svm_model *)
    np.npy_intp  get_nr (svm_model *)
    int  free_problem   (svm_problem *)
    int  free_model     (svm_model *)
    void set_verbosity(int)
