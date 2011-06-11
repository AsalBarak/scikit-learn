/*
 * Authors: Mathieu Blondel <mathieu@mblondel.org>
 *          Lars Buitinck <L.J.Buitinck@uva.nl>
 *
 * License: Simple BSD
 *
 * This module implements _load_svmlight_format, a fast and memory efficient
 * function to load the file format originally created for svmlight and now used
 * by many other libraries, including libsvm.
 *
 * The function loads the file directly in a CSR sparse matrix without memory
 * copying.  The approach taken is to use 4 C++ vectors (data, indices, indptr
 * and labels) and to incrementally feed them with elements. Ndarrays are then
 * instantiated by PyArray_SimpleNewFromData, i.e., no memory is
 * copied.
 *
 * Since the memory is not allocated by the ndarray, the ndarray doesn't own the
 * memory and thus cannot deallocate it. To automatically deallocate memory, the
 * technique described at http://blog.enthought.com/?p=62 is used. The main idea
 * is to use an additional object that the ndarray does own and that will be
 * responsible for deallocating the memory.
 */


#include <Python.h>
#include <numpy/arrayobject.h>

#include <iostream>
#include <fstream>
#include <string>
#include <vector>

// An object responsible for deallocating the memory
struct BaseVectorOwner {
  PyObject_HEAD
  int typenum; // NPY_DOUBLE or NPY_INT
};

template <typename T>
struct VectorOwner : public BaseVectorOwner {
  std::vector<T> v;
};


extern "C" {
static void dealloc(PyObject *self)
{
  BaseVectorOwner &obj = *reinterpret_cast<BaseVectorOwner *>(self);
  if (obj.typenum == NPY_DOUBLE)
    static_cast<VectorOwner<double> &>(obj).v.~vector<double>();
  else if (obj.typenum == NPY_INT)
    static_cast<VectorOwner<int> &>(obj).v.~vector<int>();
  obj.ob_type->tp_free(self);
}
}

static PyTypeObject IntVectorOwnerType = {
  PyObject_HEAD_INIT(NULL)
  0, /*ob_size*/
  "deallocator", /*tp_name*/
  sizeof(VectorOwner<int>), /*tp_basicsize*/
  0, /*tp_itemsize*/
  dealloc, /*tp_dealloc*/
  0, /*tp_print*/
  0, /*tp_getattr*/
  0, /*tp_setattr*/
  0, /*tp_compare*/
  0, /*tp_repr*/
  0, /*tp_as_number*/
  0, /*tp_as_sequence*/
  0, /*tp_as_mapping*/
  0, /*tp_hash */
  0, /*tp_call*/
  0, /*tp_str*/
  0, /*tp_getattro*/
  0, /*tp_setattro*/
  0, /*tp_as_buffer*/
  Py_TPFLAGS_DEFAULT, /*tp_flags*/
  "Internal deallocator object", /* tp_doc */
},
DoubleVectorOwnerType = {
  PyObject_HEAD_INIT(NULL)
  0, /*ob_size*/
  "deallocator", /*tp_name*/
  sizeof(VectorOwner<double>), /*tp_basicsize*/
  0, /*tp_itemsize*/
  dealloc, /*tp_dealloc*/
  0, /*tp_print*/
  0, /*tp_getattr*/
  0, /*tp_setattr*/
  0, /*tp_compare*/
  0, /*tp_repr*/
  0, /*tp_as_number*/
  0, /*tp_as_sequence*/
  0, /*tp_as_mapping*/
  0, /*tp_hash */
  0, /*tp_call*/
  0, /*tp_str*/
  0, /*tp_getattro*/
  0, /*tp_setattro*/
  0, /*tp_as_buffer*/
  Py_TPFLAGS_DEFAULT, /*tp_flags*/
  "Internal deallocator object", /* tp_doc */
};

PyTypeObject &vector_owner_type(int typenum)
{
  switch (typenum) {
    case NPY_INT: return IntVectorOwnerType;
    case NPY_DOUBLE: return DoubleVectorOwnerType;
  }
}

// Convert a C++ vector to a 1d-ndarray WITHOUT memory copying.
// Takes ownership of v's contents.
template <typename T>
static PyObject *to_1d_array(std::vector<T> &v, int typenum)
{
  npy_intp dims[1] = {v.size()};

  // A C++ vector's first element is guaranteed to point to the internally used
  // array of memory (memory is contiguous).
  PyObject *arr = PyArray_SimpleNewFromData(1, dims, typenum, &v[0]);

  // FIXME: goto is even less safe in C++ than in C.
  // We should be using exceptions.
  if (!arr)
    goto fail;

  VectorOwner<T> *owner;
  owner = PyObject_New(VectorOwner<T>, &vector_owner_type(typenum));

  if (!owner)
    goto fail;

  owner->typenum = typenum;
  new (&owner->v) std::vector<T>();
  owner->v.swap(v);

  PyArray_BASE(arr) = (PyObject *)owner;

  return arr;

fail:
  Py_XDECREF(arr);

  return 0;
}

static bool
parse_line(const std::string& line,
           std::vector<double> &data,
           std::vector<int> &indices,
           std::vector<int> &indptr,
           std::vector<double> &labels)
{
  if (line.length() == 0)
    return false;

  // Parse label
  const char *in_string = line.c_str();
  double y;

  if (!sscanf(in_string, "%lf", &y)) {
    return false;
  }

  labels.push_back(y);

  const char* position;
  position = strchr(in_string, ' ') + 1;

  indptr.push_back(data.size());

  // Parse feature-value pairs
  for ( ;
       (position
      && position < in_string + line.length()
      && position[0] != '#');
       position = strchr(position, ' ')) {

    // Consume multiple spaces, if needed.
    while (isspace(*position))
      position++;

    // Parse the feature-value pair.
    int id = atoi(position);
    position = strchr(position, ':') + 1;
    double value = atof(position);
    indices.push_back(id);
    data.push_back(value);
  }

  return true;
}

/*
 * Parse entire file. Returns success/failure.
 */
static bool
parse_file(char const *file_path,
           size_t buffer_size,
           std::vector<double> &data,
           std::vector<int> &indices,
           std::vector<int> &indptr,
           std::vector<double> &labels)
{
  std::vector<char> buffer(buffer_size);

  std::ifstream file_stream(file_path);
  if (!file_stream)
    return false;

  file_stream.rdbuf()->pubsetbuf(buffer.data(), buffer_size);

  std::string line;
  while (std::getline(file_stream, line)) {
    if (!parse_line(line, data, indices, indptr, labels))
      return false;
  }
  indptr.push_back(data.size());
  return true;
}

static const char load_svmlight_format_doc[] =
  "Load file in svmlight format and return a CSR.";

extern "C" {
static PyObject *load_svmlight_format(PyObject *self, PyObject *args)
{
  // initialization
  _import_array();

  DoubleVectorOwnerType.tp_new = PyType_GenericNew;
  IntVectorOwnerType.tp_new = PyType_GenericNew;
  if (PyType_Ready(&DoubleVectorOwnerType) < 0
   || PyType_Ready(&IntVectorOwnerType) < 0)
    return 0;

  std::vector<double> data, labels;
  std::vector<int> indices, indptr;

  // read function arguments
  char const *file_path;
  int buffer_mb;

  // FIXME: memory leaked
  if (!PyArg_ParseTuple(args, "si", &file_path, &buffer_mb))
    return 0;

  // FIXME: should check whether buffer_mb >= 0
  size_t buffer_size = buffer_mb * 1024 * 1024;

  return parse_file(file_path, buffer_size, data, indices, indptr, labels)
    ?  Py_BuildValue("OOOO",
                     to_1d_array(data, NPY_DOUBLE),
                     to_1d_array(indices, NPY_INT),
                     to_1d_array(indptr, NPY_INT),
                     to_1d_array(labels, NPY_DOUBLE))
    : Py_BuildValue("()");
}
}

static PyMethodDef svmlight_format_methods[] = {
  {"_load_svmlight_format", load_svmlight_format,
    METH_VARARGS, load_svmlight_format_doc},
  {NULL, NULL, 0, NULL}
};

static const char svmlight_format_doc[] =
  "Loader for svmlight / libsvm datasets - C++ helper routines";

extern "C" {
PyMODINIT_FUNC init_svmlight_format(void)
{
  Py_InitModule3("_svmlight_format",
                 svmlight_format_methods,
                 svmlight_format_doc);
}
}
