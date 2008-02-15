/* This program is public domain. */

#include <Python.h>


#define INVECTOR(obj,buf,len)										\
    do { \
        int err = PyObject_AsReadBuffer(obj, (const void **)(&buf), &len); \
        if (err < 0) return NULL; \
        len /= sizeof(*buf); \
    } while (0)
    
#define OUTVECTOR(obj,buf,len) \
    do { \
        int err = PyObject_AsWriteBuffer(obj, (void **)(&buf), &len); \
        if (err < 0) return NULL; \
        len /= sizeof(*buf); \
    } while (0)

extern "C" int 
str2imat(const char str[], int size, int imat[], int *rows, int *columns);


PyObject* Pstr2imat(PyObject *obj, PyObject *args)
{
  const char *str;
  PyObject *data_obj;
  Py_ssize_t ndata;
  int rows, cols;
  int *data;
  
  if (!PyArg_ParseTuple(args, "sO:str2imat", &str,&data_obj)) return NULL;
  OUTVECTOR(data_obj,data,ndata);
  str2imat(str, int(ndata), data, &rows, &cols);
  return Py_BuildValue("ii",rows,cols);
}

static PyMethodDef methods[] = {
   {"str2imat",
     Pstr2imat,
     METH_VARARGS,
     "str2imat(str,data): convert string to integer matrix, returning shape"
    },
    {0}
} ;


#if defined(WIN32) && !defined(__MINGW32__)
__declspec(dllexport)
#endif

	
extern "C" void init_reduction(void) {
  Py_InitModule4("_reduction",
  		methods,
		"Reduction C Library",
		0,
		PYTHON_API_VERSION
		);
}
