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


PyObject* Prebin(PyObject *obj, PyObject *args)
{
  PyObject *in_obj,*Iin_obj,*out_obj,*Iout_obj;
  Py_ssize_t nin,nIin, nout, nIout;
  double *in,*Iin,*out,*Iout;
  
  if (!PyArg_ParseTuple(args, "OOOO:rebin",
  			&in_obj,&Iin_obj,&out_obj,&Iout_obj)) return NULL;
  INVECTOR(in_obj,in,nin);
  INVECTOR(Iin_obj,Iin,nIin);
  INVECTOR(out_obj,out,nout);
  OUTVECTOR(Iout_obj,Iout,nIout);
std::cout << "1drebin "<< nin << " " << nIin << " ";
std::cout << nout << " " << nIout << std::endl << std::flush;
  if (nin != nIin+1 || nout != nIout+1) {
    PyErr_SetString(PyExc_ValueError, "_reduction.rebin: must have one more bin edges than bins");
    return NULL;
  }
  rebin_counts<double>(nin,in,Iin,nout,out,Iout);
  return Py_BuildValue("");
}

PyObject* Prebin2d(PyObject *obj, PyObject *args)
{
  PyObject *xin_obj, *yin_obj, *Iin_obj;  
  PyObject *xout_obj, *yout_obj, *Iout_obj;  
  Py_ssize_t nxin, nyin, nIin;
  Py_ssize_t nxout, nyout, nIout;
  Py_ssize_t *shape_in, *shape_out;
  double *xin,*yin,*Iin,*xout,*yout,*Iout;
  
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
std::cout << "2drebin " << nxin << " " << nyin << " " << nIin << " ";
std::cout << nxout << " " << nyout << " " << nIout << std::endl << std::flush;
  if ((nxin-1)*(nyin-1) != nIin || (nxout-1)*(nyout-1) != nIout) {
    PyErr_SetString(PyExc_ValueError, "_reduction.rebin2D: must have one more bin edges than bins");
    return NULL;
  }
  rebin_counts_2D<double>(nxin,xin,nyin,yin,Iin,nxout,xout,nyout,yout,Iout);
  return Py_BuildValue("");
}
	
static PyMethodDef methods[] = {
   {"str2imat",
     Pstr2imat,
     METH_VARARGS,
     "str2imat(str,data): convert string to integer matrix, returning shape"
    },
    {"rebin",
     Prebin,
     METH_VARARGS,
     "rebin(xi,Ii,xo,Io): rebin from bin edges xi to bin edges xo"
    },
    {"rebin2d",
     Prebin2d,
     METH_VARARGS,
     "rebin2d(xi,yi,Ii,xo,yo,Io): 2-D rebin from (xi,yi) to (xo,yo)"
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
