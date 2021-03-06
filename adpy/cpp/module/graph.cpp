//#define NO_IMPORT_ARRAY
#include "interface.hpp"
#include "external.hpp"

#ifndef MODULE
    #define MODULE graph
#endif

#ifdef PY3
    #define initFunc GET_MODULE(PyInit_,MODULE)
#else
    #define initFunc GET_MODULE(init,MODULE)
#endif
#define modName VALUE(MODULE)

PyObject* initialize(PyObject *self, PyObject *args) {
    #ifdef GPU
        int count;
        int rank = PyInt_AsLong(PyTuple_GetItem(args, 0));
        gpuErrorCheck(cudaSetDevice(rank));
        gpuErrorCheck(cudaSetDeviceFlags(cudaDeviceMapHost));
        gpuErrorCheck(cudaGetDeviceCount(&count));
        printf("GPU devices: %d, rank: %d\n", count, rank);
    #endif

    external_init(args);

    Py_INCREF(Py_None);
    return Py_None;
}

PyMethodDef StaticMethods[] = {
    {"initialize",  initialize, METH_VARARGS, "Execute a shell command."},
};
extern PyMethodDef ExtraMethods[];
static PyMethodDef* Methods;

void interface_exit() {
    external_exit();
    free(Methods);
}

PyMODINIT_FUNC
initFunc(void)
{
    PyObject *m;
    int n = 0;
    while(1) {
        if (ExtraMethods[n].ml_name == NULL) 
            break;
        n++;
    }
    n++;
    Methods = (PyMethodDef*) malloc(sizeof(PyMethodDef)*(1+n));
    memcpy(Methods, StaticMethods, sizeof(PyMethodDef)*1);
    memcpy(Methods + 1, ExtraMethods, sizeof(PyMethodDef)*n);

    #ifdef PY3
        static struct PyModuleDef moduledef = {
            PyModuleDef_HEAD_INIT,  /* m_base */
            modName,                 /* m_name */
            NULL,                   /* m_doc */
            -1,                     /* m_size */
            Methods            /* m_methods */
        };
        m = PyModule_Create(&moduledef);
        if (m == NULL) {
            cout << "Module import failed: " << modName << endl;
            return NULL;
        }
    #else
        m = Py_InitModule(modName, Methods);
        if (m == NULL)
            return;
    #endif
    import_array();
    Py_AtExit(interface_exit);

    //SpamError = PyErr_NewException("spam.error", NULL, NULL);
    //Py_INCREF(SpamError);
    //PyModule_AddObject(m, "error", SpamError);
    #ifdef PY3
        return m;
    #endif
}


