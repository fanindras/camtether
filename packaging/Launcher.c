/* Native launcher and current-user camera registration adapter. MIT. */
#ifndef UNICODE
#define UNICODE
#endif
#define _UNICODE
#define COBJMACROS
#define INITGUID
#include <windows.h>
#include <shellapi.h>
#include <wchar.h>
#include <stdint.h>
#include <stdlib.h>
#include <stdio.h>

#define CLASS_KEY L"Software\\Classes\\CLSID\\{A3FCE0F5-3493-419F-958A-ABA1250EC20B}"
#define INPROC_KEY CLASS_KEY L"\\InprocServer32"
#define CATEGORY_KEY L"Software\\Classes\\CLSID\\{860BB310-5D01-11D0-BD3B-00A0C911CE86}\\Instance\\CamTether"
#define CLSID_VALUE L"{A3FCE0F5-3493-419F-958A-ABA1250EC20B}"
#define OWNER L"CamTetherCameraOwner"
#define SESSION L"CamTetherSession"
#define CAP 32768

#include "WmiRegistry.h"

static LONG own_key(const wchar_t *path,REGSAM view,const wchar_t *session){
    LONG e=external_set(path,view,OWNER,L"CamTether");
    if(!e)e=external_set(path,view,SESSION,session);return e;
}
static LONG session_owned(const wchar_t *path,REGSAM view,const wchar_t *session,BOOL *owned){
    wchar_t owner[64],current[64];*owned=FALSE;
    LONG e=external_read(path,view,OWNER,owner,64);
    if(e==ERROR_FILE_NOT_FOUND)return ERROR_SUCCESS;if(e)return e;
    if(wcscmp(owner,L"CamTether"))return ERROR_SUCCESS;
    e=external_read(path,view,SESSION,current,64);
    if(e==ERROR_FILE_NOT_FOUND)return ERROR_SUCCESS;if(e)return e;
    *owned=!wcscmp(current,session);return ERROR_SUCCESS;
}
static LONG remove_value_if_present(const wchar_t *path,REGSAM view,const wchar_t *name){
    wchar_t value[CAP];LONG e=external_read(path,view,name,value,CAP);
    if(e==ERROR_FILE_NOT_FOUND)return ERROR_SUCCESS;if(e)return e;
    return external_delete_value(path,view,name);
}
static LONG remove_markers(const wchar_t *path,REGSAM view){
    LONG e=remove_value_if_present(path,view,SESSION);
    if(!e)e=remove_value_if_present(path,view,OWNER);return e;
}
static LONG cleanup(REGSAM view,const wchar_t *session,const wchar_t *dll){
    LONG result=0,e;BOOL owned=FALSE;wchar_t existing[CAP];
    e=session_owned(CATEGORY_KEY,view,session,&owned);if(e)result=e;
    if(!e&&owned){
        e=remove_value_if_present(CATEGORY_KEY,view,L"CLSID");
        if(!e)e=remove_value_if_present(CATEGORY_KEY,view,L"FriendlyName");
        if(!e)e=remove_markers(CATEGORY_KEY,view);
        if(!e)e=external_remove_empty(CATEGORY_KEY,view);
        if(e)result=e;
    }
    e=session_owned(CLASS_KEY,view,session,&owned);if(e&&!result)result=e;
    if(!e&&owned){
        e=external_read(INPROC_KEY,view,NULL,existing,CAP);
        if(!e&&wcscmp(existing,dll))return ERROR_INVALID_DATA;
        if(e&&e!=ERROR_FILE_NOT_FOUND)return e;
        e=remove_value_if_present(INPROC_KEY,view,NULL);
        if(!e)e=remove_value_if_present(INPROC_KEY,view,L"ThreadingModel");
        if(!e)e=external_remove_empty(INPROC_KEY,view);
        if(!e)e=remove_markers(CLASS_KEY,view);
        if(!e)e=external_remove_empty(CLASS_KEY,view);
        if(e&&!result)result=e;
    }
    return result;
}
static LONG available_key(const wchar_t *path,REGSAM view){
    BOOL occupied=FALSE;LONG e=external_occupied(path,view,&occupied);
    if(e==ERROR_FILE_NOT_FOUND)return ERROR_SUCCESS;
    if(e)return e;
    return occupied?ERROR_ALREADY_EXISTS:ERROR_SUCCESS;
}
static LONG register_view(REGSAM view,const wchar_t *session,const wchar_t *dll){
    wchar_t owner[64],existing[CAP];
    LONG e=external_read(CLASS_KEY,view,OWNER,owner,64);
    if(e&&e!=ERROR_FILE_NOT_FOUND)return e;
    BOOL ours=!e&&!wcscmp(owner,L"CamTether");
    if(ours){
        e=external_read(INPROC_KEY,view,NULL,existing,CAP);
        if(!e&&wcscmp(existing,dll))return ERROR_ALREADY_EXISTS;
        if(e&&e!=ERROR_FILE_NOT_FOUND)return e;
    }
    BOOL has_existing=FALSE;
#ifndef CAMTETHER_VALIDATION_FORCE_FILTER
    e=external_read(INPROC_KEY,view,NULL,existing,CAP);
    if(e==ERROR_FILE_NOT_FOUND)e=provider_read(TRUE,INPROC_KEY,view,NULL,existing,CAP);
    if(e&&e!=ERROR_FILE_NOT_FOUND)return e;
    has_existing=!e;
#endif
#ifdef CAMTETHER_VALIDATION_FORCE_FILTER
    if(!ours){e=available_key(CLASS_KEY,view);if(e)return e;}
    has_existing=FALSE;
#endif
    if(ours||!has_existing){
        if(!ours){e=available_key(CLASS_KEY,view);if(e)return e;}
        e=own_key(CLASS_KEY,view,session);if(e)return e;
        e=external_set(INPROC_KEY,view,NULL,dll);if(e)return e;
        e=external_set(INPROC_KEY,view,L"ThreadingModel",L"Both");if(e)return e;
    }else if(GetFileAttributesW(existing)==INVALID_FILE_ATTRIBUTES)return ERROR_FILE_NOT_FOUND;
    e=external_read(CATEGORY_KEY,view,OWNER,owner,64);
    if(e&&e!=ERROR_FILE_NOT_FOUND)return e;
    if(e||wcscmp(owner,L"CamTether")){e=available_key(CATEGORY_KEY,view);if(e)return e;}
    e=own_key(CATEGORY_KEY,view,session);if(e)return e;
    e=external_set(CATEGORY_KEY,view,L"CLSID",CLSID_VALUE);if(e)return e;
    return external_set(CATEGORY_KEY,view,L"FriendlyName",L"CamTether");
}

static HANDLE registration_mutex=NULL;
static wchar_t registration_session[64],registration_dll64[CAP],registration_dll32[CAP];
__declspec(dllexport) LONG WINAPI CamTetherUnregisterCamera(void){
    if(!registration_mutex)return ERROR_SUCCESS;
    registry_deadline=GetTickCount64()+25000;
    LONG a=cleanup(KEY_WOW64_64KEY,registration_session,registration_dll64);
    LONG b=cleanup(KEY_WOW64_32KEY,registration_session,registration_dll32);
    ReleaseMutex(registration_mutex);CloseHandle(registration_mutex);registration_mutex=NULL;
    registry_close();return a?a:b;
}
__declspec(dllexport) LONG WINAPI CamTetherRegisterCamera(const wchar_t *session,const wchar_t *folder){
    if(registration_mutex)return ERROR_ALREADY_EXISTS;
    if(!session||!folder||wcslen(session)!=32||wcslen(folder)!=24)return ERROR_INVALID_PARAMETER;
    for(unsigned i=0;i<32;i++)if(!wcschr(L"0123456789abcdef",session[i]))return ERROR_INVALID_PARAMETER;
    for(unsigned i=0;i<24;i++)if(!wcschr(L"0123456789abcdef",folder[i]))return ERROR_INVALID_PARAMETER;
    wchar_t local[CAP];DWORD n=GetEnvironmentVariableW(L"LOCALAPPDATA",local,CAP);
    if(!n||n>CAP-160)return ERROR_BAD_PATHNAME;
    swprintf(registration_dll64,CAP,L"%ls\\CamTetherCamera\\%ls\\obs-virtualcam-module64.dll",local,folder);
    swprintf(registration_dll32,CAP,L"%ls\\CamTetherCamera\\%ls\\obs-virtualcam-module32.dll",local,folder);
    if(GetFileAttributesW(registration_dll64)==INVALID_FILE_ATTRIBUTES||GetFileAttributesW(registration_dll32)==INVALID_FILE_ATTRIBUTES)return ERROR_FILE_NOT_FOUND;
    HANDLE mutex=CreateMutexW(NULL,FALSE,L"Local\\CamTetherCameraRegistration");if(!mutex)return GetLastError();
    DWORD wait=WaitForSingleObject(mutex,5000);
    if(wait!=WAIT_OBJECT_0&&wait!=WAIT_ABANDONED){CloseHandle(mutex);return ERROR_BUSY;}
    registration_mutex=mutex;wcscpy(registration_session,session);
    registry_deadline=GetTickCount64()+25000;
    LONG e=register_view(KEY_WOW64_64KEY,session,registration_dll64);
    if(!e)e=register_view(KEY_WOW64_32KEY,session,registration_dll32);
    if(e)CamTetherUnregisterCamera();
    registry_close();return e;
}
typedef int (__cdecl *PythonMain)(int,wchar_t**);

int WINAPI wWinMain(HINSTANCE instance,HINSTANCE previous,wchar_t *cmd,int show) {
    wchar_t root[CAP],dll[CAP],exe[CAP],script[CAP];
    DWORD n=GetModuleFileNameW(NULL,root,CAP);
    if(!n || n>CAP-100) return ERROR_BAD_PATHNAME;
    wchar_t *slash=wcsrchr(root,L'\\');if(!slash)return ERROR_BAD_PATHNAME;*slash=0;
    swprintf(dll,CAP,L"%ls\\runtime\\python313.dll",root);
    swprintf(exe,CAP,L"%ls\\runtime\\pythonw.exe",root);
    swprintf(script,CAP,L"%ls\\launch.py",root);
    HMODULE python=LoadLibraryExW(dll,NULL,LOAD_LIBRARY_SEARCH_DLL_LOAD_DIR|LOAD_LIBRARY_SEARCH_DEFAULT_DIRS);
    PythonMain main=python?(PythonMain)GetProcAddress(python,"Py_Main"):NULL;
    if(!main) {MessageBoxW(NULL,L"The packaged Python runtime could not load. Repair or reinstall CamTether.",L"CamTether startup error",MB_OK|MB_ICONERROR);return ERROR_DLL_INIT_FAILED;}
    wchar_t *args[2]={exe,script};
    return main(2,args);
}

