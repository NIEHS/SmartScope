#include "Python.h"
#include <string>
#include "PySEMSocket.h"

#ifdef _DEBUG
#define new DEBUG_NEW
#endif

#if PY_MAJOR_VERSION > 3 || (PY_MAJOR_VERSION == 3 && PY_MINOR_VERSION >= 4)
#define BUFFER_TYPE
#endif

// Definitions from SerialEM: these should come from a common include file
#define MAX_BUFFERS  20
#define MAX_FFT_BUFFERS 8
#define EXTRA_NO_VALUE -1.e8f
#define EXTRA_VALUE_TEST -9.e7f
#define SCRIPT_NORMAL_EXIT  -123456
#define SCRIPT_EXIT_NO_EXC  -654321
#define BUFFER_PROCESSED -1


#define INT_NO_VALUE -2000000000
static char sErrorBuf[ERR_BUF_SIZE] = {0x00};

static PyObject *sSerialEMError;
static PyObject *sExitedError;
static PyObject *sSEMModuleError;
static bool sExitWasCalled;
static bool sInitializedScript = false;
static CPySEMSocket sSocket;


static ScriptLangData dataStruct;
static ScriptLangData *sScriptData = &dataStruct;


#define MAC_SAME_NAME(nam, req, flg, cme) CME_##cme,
#define MAC_DIFF_NAME(nam, req, flg, fnc, cme) CME_##cme,
#define MAC_SAME_FUNC(nam, req, flg, fnc, cme) CME_##cme,
#define MAC_SAME_FUNC_NOARG MAC_SAME_FUNC
#define MAC_DIFF_NAME_NOARG MAC_DIFF_NAME
#define MAC_SAME_NAME_NOARG MAC_SAME_NAME
#define MAC_SAME_NAME_ARG(a, b, c, d, e) MAC_SAME_NAME(a, b, c, d)
#define MAC_DIFF_NAME_ARG(a, b, c, d, e, f) MAC_DIFF_NAME(a, b, c, d, e)
#define MAC_SAME_FUNC_ARG(a, b, c, d, e, f) MAC_SAME_FUNC(a, b, c, d, e)

// An enum with indexes to true commands, preceded by special operations
enum {
#include "MacroMasterList.h"
};

/*
* Static functions
*/
static PyObject *RunCommand(int funcCode, const char *name, const char *keys,
  PyObject *args);

void DebugToLog(const char *message)
{
  printf("%s", message);
}

void ErrorToLog(const char *message) 
{
  strcpy_s(sErrorBuf, ERR_BUF_SIZE, message);
  DebugToLog(message);
}

void EitherToLog(const char *prefix, const char *message, bool saveErr)
{
  if (saveErr)
    ErrorToLog(message);
  else
    DebugToLog(message);
}

/*
 * An even more convenient function for debug output
 */
void DebugFmt(char *fmt, ...)
{
  va_list args;
  va_start(args, fmt);
  vsprintf_s(sErrorBuf, ERR_BUF_SIZE, fmt, args);
  va_end(args);
  DebugToLog(sErrorBuf);
}

/*
 * Now for Python handling
 * Macros defining the different types of standardized calls
 */

/*
 * Buffer Protocol-related code is largely copied from the example in
 *  https://jakevdp.github.io/blog/2014/05/05/introduction-to-the-python-buffer-protocol/
 * which is released with a BSD-type license
 */
#ifdef BUFFER_TYPE
 /* This is where we define the PyBufferImage object structure */
typedef struct {
  PyObject_HEAD
    
  /* Type-specific fields go below. */
  void *array;
  int imType;
  int rowBytes;
  int sizeX, sizeY;
  int itemSize;
  Py_ssize_t shape[2];
  Py_ssize_t strides[2];
  char format[8];
} PyBufferImage;


/* This is the __init__ function, implemented in C */
static int PyBufferImage_init(PyBufferImage *bufIm, PyObject *args, PyObject *kwds)
{
  char *strPtr;
  int bufInd, len;
  bufIm->array = NULL;

  if (kwds) {
    PyErr_SetString(PyExc_TypeError, "Keywords are not supported when initializing"
      " a bufferImage");
    return -1;   // -1 works here, no second error
  }

  // Get the buffer argument
  if (!PyArg_ParseTuple(args, "s", &strPtr))
    return -1;
  len = (int)strlen(strPtr);
  if (len == 1 || (len == 2 && strPtr[1] == 'F')) {
    bufInd = strPtr[0] - 'A';
    if (bufInd >= 0 && ((len == 1 && bufInd < MAX_BUFFERS) ||
      (len == 2 && bufInd < MAX_FFT_BUFFERS))) {
      bufIm->array = sSocket.GetBufferImage
        (bufInd, len - 1, strPtr, bufIm->imType, bufIm->rowBytes, bufIm->sizeX,
         bufIm->sizeY, bufIm->itemSize, &bufIm->format[0]);
      if (!bufIm->array) {
        PyErr_SetString(sSEMModuleError, sSocket.mErrorBuf);

        // -1 here and below is silent, 0 gives an exception from the exception with
        // "returned a result with an error set"
        return 0;  
      }

      return 0;
    }
  }
  PyErr_Format(sSEMModuleError, "\"%s\" is not a valid buffer specification", strPtr);
  return 0;
}


/* this function is called when the object is deallocated */
static void PyBufferImage_dealloc(PyBufferImage *bufIm)
{
  free(bufIm->array);
  Py_TYPE(bufIm)->tp_free((PyObject*)bufIm);
}

// The function to fill the buffer object values
static int PyBufferImage_getbuffer(PyObject *obj, Py_buffer *view, int flags)
{
  if (view == NULL) {
    PyErr_SetString(PyExc_ValueError, "NULL view in getbuffer");
    return -1;
  }

  PyBufferImage* bufIm = (PyBufferImage*)obj;

  // Refuse a request for strictly contiguous buffer (no strides) if the stride is actually
  // needed
  if (!(flags & PyBUF_ANY_CONTIGUOUS) &&
    bufIm->rowBytes != bufIm->itemSize * bufIm->sizeX) {
    PyErr_SetString(sSEMModuleError, "Calling function requested a contiguous buffer "
                    "image without strides and the image has padded lines");
    return -1;
  }

  // The first dimension is the slow one
  bufIm->shape[0] = bufIm->sizeY;
  bufIm->shape[1] = bufIm->sizeX;
  bufIm->strides[0] = bufIm->rowBytes;
  bufIm->strides[1] = bufIm->itemSize;

  view->obj = obj;
  view->buf = (void*)bufIm->array;
  view->len = bufIm->rowBytes * bufIm->sizeY;
  view->readonly = 1;
  view->itemsize = bufIm->itemSize;
  view->format = bufIm->format;
  view->ndim = 2;
  view->shape = &bufIm->shape[0];
  view->strides = (flags & PyBUF_ANY_CONTIGUOUS) ? NULL : &bufIm->strides[0];
  view->suboffsets = NULL;
  view->internal = NULL;

  Py_INCREF(bufIm);  // need to increase the reference count
  return 0;
}

static PyBufferProcs PyBufferImage_as_buffer = {
  // this definition is only compatible with Python 3.3 and above
  (getbufferproc)PyBufferImage_getbuffer,
  (releasebufferproc)0,  // we do not require any special release function
};

/* Here is the type structure: we put the above functions in the appropriate place
in order to actually define the Python object type */
static PyTypeObject PyBufferImageType = {
  PyVarObject_HEAD_INIT(NULL, 0)
  "serialem.PyBufferImage",        /* tp_name */
  sizeof(PyBufferImage),            /* tp_basicsize */
  0,                            /* tp_itemsize */
  (destructor)PyBufferImage_dealloc,/* tp_dealloc */
  0,                            /* tp_print */
  0,                            /* tp_getattr */
  0,                            /* tp_setattr */
  0,                            /* tp_reserved */
  0,                            /* tp_repr */
  0,                            /* tp_as_number */
  0,                            /* tp_as_sequence */
  0,                            /* tp_as_mapping */
  0,                            /* tp_hash  */
  0,                            /* tp_call */
  0,                            /* tp_str */
  0,                            /* tp_getattro */
  0,                            /* tp_setattro */
  &PyBufferImage_as_buffer,     /* tp_as_buffer */
  Py_TPFLAGS_DEFAULT,           /* tp_flags */
  "PyBufferImage object",           /* tp_doc */
  0,                            /* tp_traverse */
  0,                            /* tp_clear */
  0,                            /* tp_richcompare */
  0,                            /* tp_weaklistoffset */
  0,                            /* tp_iter */
  0,                            /* tp_iternext */
  0,                            /* tp_methods */
  0,                            /* tp_members */
  0,                            /* tp_getset */
  0,                            /* tp_base */
  0,                            /* tp_dict */
  0,                            /* tp_descr_get */
  0,                            /* tp_descr_set */
  0,                            /* tp_dictoffset */
  (initproc)PyBufferImage_init,     /* tp_init */
};

// End of buffer protocol code based on the blog */

// PutImageInBuffer
PyObject *serialem_PutImageInBuffer(PyObject *self, PyObject *args)
{
  int toBufInd, baseBufInd, sizeX = 0, sizeY = 0, imType, xInd;
  char *toBufPtr, *baseBufPtr = NULL;
  int moreBinning = 1;
  int capFlag = BUFFER_PROCESSED;
  PyObject *bufObj;
  Py_buffer view;
 
  if (!PyArg_ParseTuple(args, "Os|iisii", &bufObj, &toBufPtr, &sizeX, &sizeY, 
                        &baseBufPtr, &moreBinning, &capFlag))
    return NULL;

  // Check buffers
  if (!baseBufPtr)
    baseBufPtr = toBufPtr;
  toBufInd = (int)toBufPtr[0] - (int)'A';
  if (toBufInd < 0 || toBufInd >= MAX_BUFFERS || strlen(toBufPtr) > 1) {
    PyErr_Format(sSEMModuleError, "Invalid specification of buffer to place image into:"
                 " %s", toBufPtr);
    return NULL;
  }
  baseBufInd = (int)baseBufPtr[0] - (int)'A';
  if (baseBufInd < 0 || baseBufInd >= MAX_BUFFERS || strlen(baseBufPtr) > 1) {
    PyErr_Format(sSEMModuleError, "Invalid specification of buffer to use as basis for "
                 "information: %s", baseBufPtr);
    return NULL;
  }

  // Other checks on object and view
  if (PyObject_GetBuffer(bufObj, &view, PyBUF_FORMAT) == -1) {
    PyErr_SetString(sSEMModuleError, "The image object does not have the proper form "
                    "for accessing its array");
    return NULL;
  }

  // Complain about ndim unless it fits the pattern for a numpy array
  if (view.ndim != 2 && (view.shape || view.ndim)) {
    PyErr_Format(sSEMModuleError, "The image object does not have a 2-dimensional "
                 "array (ndim=%d)", view.ndim);
    PyBuffer_Release(&view);
    return NULL;
  }

  if (!view.buf) {
    PyErr_SetString(sSerialEMError, "The image object has a NULL array pointer");
    PyBuffer_Release(&view);
    return NULL;
  }

  // Check contiguity and set index of X and Y size
  if (PyBuffer_IsContiguous(&view, 'C')) {
    xInd = 1;
  } else if (PyBuffer_IsContiguous(&view, 'F')) {
    xInd = 0;
  } else {
    PyErr_SetString(sSEMModuleError, "The image object has a non-contiguous array");
    PyBuffer_Release(&view);
    return NULL;
  }

  // Set X and Y size with shape, fall back to entered values
  sizeX = view.shape ? (int)view.shape[xInd] : sizeX;
  sizeY = view.shape ? (int)view.shape[1 - xInd] : sizeY;
  if (sizeX <= 0 || sizeY <= 0) {
    PyErr_SetString(sSEMModuleError, "You must call this function with positive X and "
                    "Y sizes; the image object lacks size information");
    PyBuffer_Release(&view);
    return NULL;
  }

  // Decode the format, perhaps too restrictively
  if (!strcmp(view.format, "B"))
    imType = MRC_MODE_BYTE;
  else if (!strcmp(view.format, "f"))
    imType = MRC_MODE_FLOAT;
  else if(!strcmp(view.format, "h"))
    imType = MRC_MODE_SHORT;
  else if (!strcmp(view.format, "H"))
    imType = MRC_MODE_USHORT;
  else if (!strcmp(view.format, "BBB"))
    imType = MRC_MODE_RGB;
  else {
    PyErr_Format(sSEMModuleError, "The image's format specification, \"%s\", does not "
                 "correspond to a type supported in SerialEM", view.format);
    PyBuffer_Release(&view);
    return NULL;
  }

  // Call the function to deliver the image
  if (sSocket.PutImageInbuffer(view.buf, imType, sizeX, sizeY, (int)view.itemsize,
                               toBufInd, baseBufInd, moreBinning, capFlag)) {
    PyErr_SetString(sSEMModuleError, sSocket.mErrorBuf);
    PyBuffer_Release(&view);
    return NULL;
  }
  
  PyBuffer_Release(&view);
  Py_RETURN_NONE;
}

#endif

// ConnectToSEM
PyObject *serialem_ConnectToSEM(PyObject *self, PyObject *args)
{
  int port = 0;
  char *ipAddress = NULL;
  if (!PyArg_ParseTuple(args, "|is", &port, &ipAddress))
    return NULL;
  if (sSocket.InitializeSocket(port, ipAddress)) {
    PyErr_SetString(sSEMModuleError, sSocket.mErrorBuf);
    return NULL;
  }
  Py_RETURN_NONE;
}

// ScriptIsInitialized
PyObject *serialem_ScriptIsInitialized(PyObject *self, PyObject *args)
{
  if (!PyArg_ParseTuple(args, ""))
    return NULL;
  sInitializedScript = true;
  Py_RETURN_NONE;
}

// This is both the pattern for making a specialized set as done below,
// and also necessary to define away the rest of entries in the master list
#define MAC_SAME_FUNC(nam, req, flg, fnc, cme)  
#define MAC_SAME_NAME(nam, req, flg, cme) MAC_SAME_FUNC(nam, req, flg, 0, cme)
#define MAC_DIFF_NAME  MAC_SAME_FUNC

// ARGUMENTS
#define MAC_SAME_FUNC_ARG(nam, req, flg, fnc, cme, key)   \
PyObject *serialem_##nam(PyObject *self, PyObject *args) \
{  \
  return RunCommand(CME_##cme, #nam, #key, args);     \
}
#define MAC_SAME_NAME_ARG(nam, req, flg, cme, key) MAC_SAME_FUNC_ARG(nam, req, flg, 0, cme, key)
#define MAC_DIFF_NAME_ARG MAC_SAME_FUNC_ARG

// NO ARG
#define MAC_SAME_FUNC_NOARG(nam, req, flg, fnc, cme)    \
PyObject *serialem_##nam(PyObject *self, PyObject *args) \
{  \
  return RunCommand(CME_##cme, #nam, "", args);     \
}
#define MAC_SAME_NAME_NOARG(nam, req, flg, cme) MAC_SAME_FUNC_NOARG(nam, req, flg, 0, cme)

/*
 * Now include all the calls
 */

#include "MacroMasterList.h"


// Definitions for building up the method table

#define MAC_SAME_FUNC(nam, req, flg, fnc, cme)  
#define MAC_SAME_NAME(nam, req, flg, cme) MAC_SAME_FUNC(nam, req, flg, 0, cme)
#define MAC_DIFF_NAME  MAC_SAME_FUNC

// ARGUMENTS
#define MAC_SAME_FUNC_ARG(nam, req, flg, fnc, cme, key) \
  {#nam, serialem_##nam, METH_VARARGS},
#define MAC_SAME_NAME_ARG(nam, req, flg, cme, key) MAC_SAME_FUNC_ARG(nam, req, flg, 0, cme, key)
#define MAC_DIFF_NAME_ARG MAC_SAME_FUNC_ARG

// NO ARG
#define MAC_SAME_FUNC_NOARG(nam, req, flg, fnc, cme)  \
  MAC_SAME_FUNC_ARG(nam, req, flg, fnc, cme, 0)
#define MAC_SAME_NAME_NOARG(nam, req, flg, cme) MAC_SAME_FUNC_ARG(nam, req, flg, 0, cme, 0)

// Include to make the method table
static PyMethodDef serialemmethods[] = {
#include "MacroMasterList.h"
  {"ConnectToSEM", serialem_ConnectToSEM,  METH_VARARGS},
  {"ScriptIsInitialized", serialem_ScriptIsInitialized,  METH_VARARGS},
#if PY_MAJOR_VERSION >= 3
  {"PutImageInBuffer", serialem_PutImageInBuffer, METH_VARARGS},
#endif
  {NULL, NULL}};

// Define the module
#if PY_MAJOR_VERSION >= 3
static PyModuleDef serialemModule = {
  PyModuleDef_HEAD_INIT, "serialem", NULL, -1, serialemmethods,
  NULL, NULL, NULL, NULL
};
#endif

#if PY_MAJOR_VERSION >= 3
#ifdef _WIN32
PyObject *PyInit_serialem(void)
#else
PyMODINIT_FUNC PyInit_serialem(void)
#endif
#else
PyMODINIT_FUNC initserialem(void)
#endif
{
  PyObject *mod;
  sSocket.mScriptData = sScriptData;

#ifdef BUFFER_TYPE
  PyBufferImageType.tp_new = PyType_GenericNew;
  if (PyType_Ready(&PyBufferImageType) < 0)
    return NULL;
  Py_INCREF(&PyBufferImageType);
#endif

#if PY_MAJOR_VERSION >= 3
  mod = PyModule_Create(&serialemModule);
  if (mod == NULL)
    return NULL;
#else
  mod = Py_InitModule("serialem", serialemmethods);
  if (!mod)
    return;
#endif

  // Set up two kinds of exceptions, error and exit
  sSerialEMError = PyErr_NewException("serialem.SEMerror", NULL, NULL);
  Py_XINCREF(sSerialEMError);
  sSEMModuleError = PyErr_NewException("serialem.SEMmoduleError", NULL, NULL);
  Py_XINCREF(sSEMModuleError);
  sExitedError = PyErr_NewException("serialem.SEMexited", NULL, NULL);
  Py_XINCREF(sExitedError);
  if (PyModule_AddObject(mod, "SEMerror", sSerialEMError) < 0 ||
      PyModule_AddObject(mod, "SEMmoduleError", sSEMModuleError) < 0 || 
      PyModule_AddObject(mod, "SEMexited", sExitedError) < 0
#ifdef BUFFER_TYPE
      || PyModule_AddObject(mod, "bufferImage", (PyObject *)&PyBufferImageType) < 0
#endif
      ) {

    Py_XDECREF(sSerialEMError);
    Py_CLEAR(sSerialEMError);
    Py_XDECREF(sSEMModuleError);
    Py_CLEAR(sSEMModuleError);
    Py_XDECREF(sExitedError);
    Py_CLEAR(sExitedError);
#ifdef BUFFER_TYPE
    Py_DECREF(&PyBufferImageType);
#endif
    Py_DECREF(mod);
#if PY_MAJOR_VERSION >= 3
    return NULL;
#endif
  }

#if PY_MAJOR_VERSION >= 3
  return mod;
#endif
}


int fgetline(FILE *fp, char s[], int limit);

static int CheckInitialization()
{
  BOOL OKtoRun;
  if (sSocket.InitializeSocket()) {
    PyErr_SetString(sSEMModuleError, sSocket.mErrorBuf);
    return 1;
  }
  if (sInitializedScript)
    return 0;
  if (sSocket.OKtoRunExternalScript(OKtoRun)) {
    PyErr_SetString(sSEMModuleError, sSocket.mErrorBuf);
    return 1;
  }
  if (!OKtoRun) {
    PyErr_SetString(sSEMModuleError, "SerialEM is busy and not ready to run a script");
    return 1;    
  }
  sInitializedScript = true;
  return 0;
}


/*
 * Function run by all functions called from the script interpreter to do the final  
 * setting of scriptData and handshake with SerialEM.
 * It should respond to errors as appropriate for the scripting language, such as by
 * an exception
 */
static PyObject *RunCommand(int funcCode, const char *name, const char *keys,
  PyObject *args)
{
  char *strPtrs[MAX_SCRIPT_LANG_ARGS];
  void *aP[MAX_SCRIPT_LANG_ARGS];
  int tempInts[MAX_SCRIPT_LANG_ARGS];
  std::string format;
  int ind, ond, retval, numArgs = (int)strlen(keys);
  bool gotOpt = false;

  // Make sure things are initialized
  if (CheckInitialization())
    return NULL;
  
  // Parse the keys and create the format string.  Allow for ints
  for (ind = 0; ind < numArgs; ind++) {
    strPtrs[ind] = NULL;
    sScriptData->itemDbl[ind + 1] = EXTRA_NO_VALUE;
    tempInts[ind] = INT_NO_VALUE;

    if ((keys[ind] == 's' || keys[ind] == 'd' || keys[ind] == 'i') && !gotOpt) {
      gotOpt = true;
      format += '|';
    }
    if (keys[ind] == 'S' || keys[ind] == 's') {
      aP[ind] = &strPtrs[ind];
      format += 's';
    } else if (keys[ind] == 'D' || keys[ind] == 'd') {
      aP[ind] = &sScriptData->itemDbl[ind + 1];
      format += 'd';
    } else if (keys[ind] == 'I' || keys[ind] == 'i') {
      aP[ind] = &tempInts[ind];
      format += 'i';
    } else {
      format = "Incorrect character in argument keys for function ";
      format += name;
      PyErr_SetString(sSEMModuleError, format.c_str());
      return NULL;
    }
  }
  format += ":";
  format += name;
  //DebugFmt("Keys %s  num %d  format %s", keys, numArgs, format.c_str());

  // There should be a more elegant way to do this...  Parse the arguments
  switch (numArgs) {
  case 0:
    retval = PyArg_ParseTuple(args, format.c_str());
    break;
  case 1:
    retval = PyArg_ParseTuple(args, format.c_str(), aP[0]);
    break;
  case 2:
    retval = PyArg_ParseTuple(args, format.c_str(), aP[0], aP[1]);
    break;
  case 3:
    retval = PyArg_ParseTuple(args, format.c_str(), aP[0], aP[1], aP[2]);
    break;
  case 4:
    retval = PyArg_ParseTuple(args, format.c_str(), aP[0], aP[1],  aP[2], aP[3]);
    break;
  case 5:
    retval = PyArg_ParseTuple(args, format.c_str(), aP[0], aP[1],  aP[2], aP[3], aP[4]);
    break;
  case 6:
    retval = PyArg_ParseTuple(args, format.c_str(), aP[0], aP[1],  aP[2], aP[3], aP[4], 
      aP[5]);
    break;
  case 7:
    retval = PyArg_ParseTuple(args, format.c_str(), aP[0], aP[1],  aP[2], aP[3], aP[4], 
      aP[5], aP[6]);
    break;
  case 8:
    retval = PyArg_ParseTuple(args, format.c_str(), aP[0], aP[1],  aP[2], aP[3], aP[4], 
      aP[5], aP[6], aP[7]);
    break;
  case 9:
    retval = PyArg_ParseTuple(args, format.c_str(), aP[0], aP[1],  aP[2], aP[3], aP[4], 
      aP[5], aP[6], aP[7], aP[8]);
    break;
  case 10:
    retval = PyArg_ParseTuple(args, format.c_str(), aP[0], aP[1],  aP[2], aP[3], aP[4],
      aP[5], aP[6], aP[7], aP[8], aP[9]);
    break;
  case 11:
    retval = PyArg_ParseTuple(args, format.c_str(), aP[0], aP[1],  aP[2], aP[3], aP[4], 
      aP[5], aP[6], aP[7], aP[8], aP[9], aP[10]);
    break;
  case 12:
    retval = PyArg_ParseTuple(args, format.c_str(), aP[0], aP[1],  aP[2], aP[3], aP[4],
      aP[5], aP[6], aP[7], aP[8], aP[9], aP[10], aP[11]);
    break;
  case 13:
    retval = PyArg_ParseTuple(args, format.c_str(), aP[0], aP[1],  aP[2], aP[3], aP[4],
      aP[5], aP[6], aP[7], aP[8], aP[9], aP[10], aP[11], aP[12]);
    break;
  case 14:
    retval = PyArg_ParseTuple(args, format.c_str(), aP[0], aP[1],  aP[2], aP[3], aP[4],
      aP[5], aP[6], aP[7], aP[8], aP[9], aP[10], aP[11], aP[12], aP[13]);
    break;
  case 15:
    retval = PyArg_ParseTuple(args, format.c_str(), aP[0], aP[1],  aP[2], aP[3], aP[4],
      aP[5], aP[6], aP[7], aP[8], aP[9], aP[10], aP[11], aP[12], aP[13], aP[14]);
    break;
  case 16:
    retval = PyArg_ParseTuple(args, format.c_str(), aP[0], aP[1],  aP[2], aP[3], aP[4],
      aP[5], aP[6], aP[7], aP[8], aP[9], aP[10], aP[11], aP[12], aP[13], aP[14], aP[15]);
    break;
  case 17:
    retval = PyArg_ParseTuple(args, format.c_str(), aP[0], aP[1],  aP[2], aP[3], aP[4],
      aP[5], aP[6], aP[7], aP[8], aP[9], aP[10], aP[11], aP[12], aP[13], aP[14], aP[15], 
      aP[16]);
    break;
  case 18:
    retval = PyArg_ParseTuple(args, format.c_str(), aP[0], aP[1],  aP[2], aP[3], aP[4], 
      aP[5], aP[6], aP[7], aP[8], aP[9], aP[10], aP[11], aP[12], aP[13], aP[14], aP[15], 
      aP[16], aP[17]);
    break;
  case 19:
    retval = PyArg_ParseTuple(args, format.c_str(), aP[0], aP[1],  aP[2], aP[3], aP[4],
      aP[5], aP[6], aP[7], aP[8], aP[9], aP[10], aP[11], aP[12], aP[13], aP[14], aP[15], 
      aP[16], aP[17], aP[18]);
    break;
  default:
    retval = 1;
  }

  if (!retval)
    return NULL;

  // Move strings and ints into the shared structure and get strings for doubles/ints
  sScriptData->lastNonEmptyInd = 0;
  for (ind = 0; ind < numArgs; ind++) {
    ond = ind + 1;
    if (sScriptData->itemDbl[ond] < EXTRA_VALUE_TEST && !strPtrs[ind] && 
      tempInts[ind] == INT_NO_VALUE)
      break;
    sScriptData->lastNonEmptyInd = ond;
    if (keys[ind] == 'S' || keys[ind] == 's') {
      sScriptData->strItems[ond] = strPtrs[ind];
      sScriptData->itemDbl[ond] = atof(strPtrs[ind]);
    } else if (keys[ind] == 'D' || keys[ind] == 'd') {
      sprintf_s(sErrorBuf, ERR_BUF_SIZE, "%f", sScriptData->itemDbl[ond]);
      sScriptData->strItems[ond] = sErrorBuf;
      if (sScriptData->strItems[ond].find('.') >= 0) {
        while (sScriptData->strItems[ond][sScriptData->strItems[ond].size() - 1] == '0')
          sScriptData->strItems[ond].resize(sScriptData->strItems[ond].size() - 1);
      }
    } else {
      sScriptData->itemDbl[ond] = tempInts[ind];
      sprintf_s(sErrorBuf, ERR_BUF_SIZE, "%d", tempInts[ind]);
      sScriptData->strItems[ond] = sErrorBuf;
    }
  }

  // Set the function code and signal ready, wait until done
  sScriptData->functionCode = funcCode;
  sScriptData->commandReady = 1;
  sExitWasCalled = funcCode == CME_EXIT;
  if (sSocket.RegularCommand()) {
    PyErr_SetString(sSEMModuleError, sSocket.mErrorBuf);
    return NULL;
  }
  
  // When an error flag is set on the other side: Throw an exit exception if it is 
  // signaled to do that, or throw a catchable error exception unless already exiting
  // from an exception
  if (sScriptData->errorOccurred) {
    if (sScriptData->errorOccurred == SCRIPT_NORMAL_EXIT) {
      PyErr_SetString(sExitedError, "Normal exit");
      sInitializedScript = false;
    } else if (sScriptData->errorOccurred == SCRIPT_EXIT_NO_EXC) {
      Py_RETURN_NONE;
      sInitializedScript = false;
    } else {
      PyErr_SetString(sSerialEMError, (sScriptData->highestReportInd >= 0 &&
                                       sScriptData->repValIsString[0]) ?
                      sScriptData->reportedStrs[0].c_str() :
                      "No message from command error");
    }
    return NULL;
  }
  
  // Return None for nothing
  if (sScriptData->highestReportInd < 0) {
    Py_RETURN_NONE;
  }
  
  // Or return a single value
  if (!sScriptData->highestReportInd) {
    if (sScriptData->repValIsString[0]) {
      //SEMTrace('[', "returning string %s", sScriptData->reportedStrs[0].c_str());
      return Py_BuildValue("s", sScriptData->reportedStrs[0].c_str());
    } else {
      //SEMTrace('[', "returning float %f", sScriptData->reportedVals[0]);
      return Py_BuildValue("f", sScriptData->reportedVals[0]);
    }
  }
  
  // Or build up a return tuple
  PyObject *tup = PyTuple_New(sScriptData->highestReportInd + 1);
  for (ind = 0; ind <= sScriptData->highestReportInd; ind++) {
    if (sScriptData->repValIsString[ind]) {
      PyTuple_SET_ITEM(tup, ind,
                       PyUnicode_FromString(sScriptData->reportedStrs[ind].c_str()));
    } else {
      PyTuple_SET_ITEM(tup, ind, PyFloat_FromDouble(sScriptData->reportedVals[ind]));
    }
  }
  return tup;
}
