/* This program is public domain. */

#include <iostream>
#include <iomanip>
#include <Python.h>
#include <rebin.h>
#include <rebin2D.h>


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


template <typename T>
PyObject* Prebin(PyObject *obj, PyObject *args)
{
  PyObject *in_obj,*Iin_obj,*out_obj,*Iout_obj;
  Py_ssize_t nin,nIin, nout, nIout;
  double *in, *out;
  T *Iin, *Iout;

  if (!PyArg_ParseTuple(args, "OOOO:rebin",
  			&in_obj,&Iin_obj,&out_obj,&Iout_obj)) return NULL;
  INVECTOR(in_obj,in,nin);
  INVECTOR(Iin_obj,Iin,nIin);
  INVECTOR(out_obj,out,nout);
  OUTVECTOR(Iout_obj,Iout,nIout);
  if (nin-1 != nIin || nout-1 != nIout) {
    PyErr_SetString(PyExc_ValueError,
    	"_reduction.rebin: must have one more bin edges than bins");
    return NULL;
  }
  rebin_counts<T>(nin-1,in,Iin,nout-1,out,Iout);
  return Py_BuildValue("");
}

template <typename T>
PyObject* Prebin2d(PyObject *obj, PyObject *args)
{
  PyObject *xin_obj, *yin_obj, *Iin_obj;
  PyObject *xout_obj, *yout_obj, *Iout_obj;
  Py_ssize_t nxin, nyin, nIin;
  Py_ssize_t nxout, nyout, nIout;
  Py_ssize_t *shape_in, *shape_out;
  double *xin,*yin,*xout,*yout;
  T *Iin, *Iout;

  if (!PyArg_ParseTuple(args, "OOOOOO:rebin",
	  		&xin_obj, &yin_obj, &Iin_obj,
  			&xout_obj, &yout_obj, &Iout_obj))
  	return NULL;

  INVECTOR(xin_obj,xin,nxin);
  INVECTOR(yin_obj,yin,nyin);
  INVECTOR(Iin_obj,Iin,nIin);
  INVECTOR(xout_obj,xout,nxout);
  INVECTOR(yout_obj,yout,nyout);
  OUTVECTOR(Iout_obj,Iout,nIout);
  if ((nxin-1)*(nyin-1) != nIin || (nxout-1)*(nyout-1) != nIout) {
    //printf("%d %d %d %d %d %d\n",nxin,nyin,nIin,nxout,nyout,nIout);
    PyErr_SetString(PyExc_ValueError,
    	"_reduction.rebin2d: must have one more bin edges than bins");
    return NULL;
  }
  rebin_counts_2D<T>(nxin-1,xin,nyin-1,yin,Iin,
      nxout-1,xout,nyout-1,yout,Iout);
  return Py_BuildValue("");
}

static PyMethodDef methods[] = {
   {"str2imat",
     &Pstr2imat,
     METH_VARARGS,
     "str2imat(str,data): convert string to integer matrix, returning shape"
    },
    {"rebin_uint8",
     &Prebin<unsigned char>,
     METH_VARARGS,
     "rebin_uint8(xi,Ii,xo,Io): rebin from bin edges xi to bin edges xo"
    },
    {"rebin2d_uint8",
     &Prebin2d<unsigned char>,
     METH_VARARGS,
     "rebin2d_uint8(xi,yi,Ii,xo,yo,Io): 2-D rebin from (xi,yi) to (xo,yo)"
    },
    {"rebin_uint16",
     &Prebin<unsigned short>,
     METH_VARARGS,
     "rebin_uint16(xi,Ii,xo,Io): rebin from bin edges xi to bin edges xo"
    },
    {"rebin2d_uint16",
     &Prebin2d<unsigned short>,
     METH_VARARGS,
     "rebin2d_uint16(xi,yi,Ii,xo,yo,Io): 2-D rebin from (xi,yi) to (xo,yo)"
    },
    {"rebin_uint32",
     &Prebin<unsigned long>,
     METH_VARARGS,
     "rebin_uint32(xi,Ii,xo,Io): rebin from bin edges xi to bin edges xo"
    },
    {"rebin2d_uint32",
     &Prebin2d<unsigned long>,
     METH_VARARGS,
     "rebin2d_uint32(xi,yi,Ii,xo,yo,Io): 2-D rebin from (xi,yi) to (xo,yo)"
    },
    {"rebin_float32",
     &Prebin<float>,
     METH_VARARGS,
     "rebin_float32(xi,Ii,xo,Io): rebin from bin edges xi to bin edges xo"
    },
    {"rebin2d_float32",
     &Prebin2d<float>,
     METH_VARARGS,
     "rebin2d_float32(xi,yi,Ii,xo,yo,Io): 2-D rebin from (xi,yi) to (xo,yo)"
    },
    {"rebin_float64",
     &Prebin<double>,
     METH_VARARGS,
     "rebin_float64(xi,Ii,xo,Io): rebin from bin edges xi to bin edges xo"
    },
    {"rebin2d_float64",
     &Prebin2d<double>,
     METH_VARARGS,
     "rebin2d_float64(xi,yi,Ii,xo,yo,Io): 2-D rebin from (xi,yi) to (xo,yo)"
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
