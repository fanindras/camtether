/* Local Windows registry provider adapter. MIT.
 * Typed Win32 results from the Windows WMI service avoid private MSIX views.
 * Only current-user paths and explicitly selected 32/64-bit views are used.
 */
#ifndef CAMTETHER_WMI_REGISTRY_H
#define CAMTETHER_WMI_REGISTRY_H
#include <wbemidl.h>
#include <sddl.h>
static IWbemServices *registry_service=NULL;
static IWbemClassObject *registry_class=NULL;
static IWbemContext *registry_context[2]={NULL,NULL};
static BOOL registry_com_initialized=FALSE;
static wchar_t registry_sid[256];
static ULONGLONG registry_deadline=0;
static void registry_close(void){
    for(unsigned i=0;i<2;i++)if(registry_context[i]){IWbemContext_Release(registry_context[i]);registry_context[i]=NULL;}
    if(registry_class){IWbemClassObject_Release(registry_class);registry_class=NULL;}
    if(registry_service){IWbemServices_Release(registry_service);registry_service=NULL;}
    if(registry_com_initialized){CoUninitialize();registry_com_initialized=FALSE;}
}
static LONG registry_open(void){
    if(registry_service)return ERROR_SUCCESS;
    HRESULT hr=CoInitializeEx(NULL,COINIT_MULTITHREADED);
    if(SUCCEEDED(hr))registry_com_initialized=TRUE;
    else if(hr!=RPC_E_CHANGED_MODE)return hr;
    HANDLE token=NULL;DWORD bytes=0;LPWSTR sid=NULL;
    if(!OpenProcessToken(GetCurrentProcess(),TOKEN_QUERY,&token)){registry_close();return GetLastError();}
    GetTokenInformation(token,TokenUser,NULL,0,&bytes);
    TOKEN_USER *user=HeapAlloc(GetProcessHeap(),0,bytes);LONG error=ERROR_SUCCESS;
    if(!user)error=ERROR_NOT_ENOUGH_MEMORY;
    else if(!GetTokenInformation(token,TokenUser,user,bytes,&bytes)||!ConvertSidToStringSidW(user->User.Sid,&sid))error=GetLastError();
    if(!error){if(wcslen(sid)>=256)error=ERROR_BUFFER_OVERFLOW;else wcscpy(registry_sid,sid);}
    if(sid)LocalFree(sid);if(user)HeapFree(GetProcessHeap(),0,user);CloseHandle(token);
    if(error){registry_close();return error;}
    IWbemLocator *locator=NULL;
    hr=CoCreateInstance(&CLSID_WbemLocator,NULL,CLSCTX_INPROC_SERVER,&IID_IWbemLocator,(void**)&locator);
    BSTR ns=SysAllocString(L"ROOT\\DEFAULT"),cls=SysAllocString(L"StdRegProv");
    if(!ns||!cls)hr=E_OUTOFMEMORY;
    if(SUCCEEDED(hr))hr=IWbemLocator_ConnectServer(locator,ns,NULL,NULL,NULL,WBEM_FLAG_CONNECT_USE_MAX_WAIT,NULL,NULL,&registry_service);
    if(locator)IWbemLocator_Release(locator);SysFreeString(ns);
    if(SUCCEEDED(hr))hr=CoSetProxyBlanket((IUnknown*)registry_service,RPC_C_AUTHN_WINNT,RPC_C_AUTHZ_NONE,NULL,RPC_C_AUTHN_LEVEL_CALL,RPC_C_IMP_LEVEL_IMPERSONATE,NULL,EOAC_NONE);
    if(SUCCEEDED(hr))hr=IWbemServices_GetObject(registry_service,cls,0,NULL,&registry_class,NULL);
    SysFreeString(cls);
    for(unsigned i=0;SUCCEEDED(hr)&&i<2;i++){
        hr=CoCreateInstance(&CLSID_WbemContext,NULL,CLSCTX_INPROC_SERVER,&IID_IWbemContext,(void**)&registry_context[i]);
        VARIANT v;VariantInit(&v);V_VT(&v)=VT_I4;V_I4(&v)=i?32:64;
        if(SUCCEEDED(hr))hr=IWbemContext_SetValue(registry_context[i],L"__ProviderArchitecture",0,&v);
        V_VT(&v)=VT_BOOL;V_BOOL(&v)=VARIANT_TRUE;
        if(SUCCEEDED(hr))hr=IWbemContext_SetValue(registry_context[i],L"__RequiredArchitecture",0,&v);
    }
    if(FAILED(hr)){registry_close();return hr;}return ERROR_SUCCESS;
}
static HRESULT registry_put_string(IWbemClassObject *input,const wchar_t *name,const wchar_t *value){
    VARIANT v;VariantInit(&v);V_VT(&v)=VT_BSTR;V_BSTR(&v)=SysAllocString(value?value:L"");
    if(!V_BSTR(&v))return E_OUTOFMEMORY;
    HRESULT hr=IWbemClassObject_Put(input,name,0,&v,0);VariantClear(&v);return hr;
}
static LONG registry_call(DWORD hive,const wchar_t *path,REGSAM view,const wchar_t *method,
                          const wchar_t *name,const wchar_t *value,IWbemClassObject **result){
    *result=NULL;
    if(registry_deadline&&GetTickCount64()>=registry_deadline)return ERROR_TIMEOUT;
    LONG e=registry_open();if(e)return e;
    IWbemClassObject *signature=NULL,*input=NULL;IWbemCallResult *pending=NULL;
    HRESULT hr=IWbemClassObject_GetMethod(registry_class,method,0,&signature,NULL);
    if(SUCCEEDED(hr))hr=IWbemClassObject_SpawnInstance(signature,0,&input);
    if(signature)IWbemClassObject_Release(signature);
    VARIANT v;VariantInit(&v);V_VT(&v)=VT_I4;V_I4(&v)=(LONG)hive;
    if(SUCCEEDED(hr))hr=IWbemClassObject_Put(input,L"hDefKey",0,&v,0);
    if(SUCCEEDED(hr))hr=registry_put_string(input,L"sSubKeyName",path);
    if(SUCCEEDED(hr)&&name)hr=registry_put_string(input,L"sValueName",name);
    if(SUCCEEDED(hr)&&value)hr=registry_put_string(input,L"sValue",value);
    BSTR cls=SysAllocString(L"StdRegProv"),meth=SysAllocString(method);
    if(!cls||!meth)hr=E_OUTOFMEMORY;
    if(SUCCEEDED(hr))hr=IWbemServices_ExecMethod(registry_service,cls,meth,WBEM_FLAG_RETURN_IMMEDIATELY,
                    registry_context[view==KEY_WOW64_32KEY?1:0],input,NULL,&pending);
    SysFreeString(cls);SysFreeString(meth);if(input)IWbemClassObject_Release(input);
    if(SUCCEEDED(hr)){
        ULONGLONG now=GetTickCount64(),remaining=registry_deadline?(registry_deadline>now?registry_deadline-now:0):10000;
        hr=IWbemCallResult_GetResultObject(pending,(LONG)(remaining<10000?remaining:10000),result);
    }
    if(pending)IWbemCallResult_Release(pending);
    if(hr==WBEM_S_TIMEDOUT)hr=HRESULT_FROM_WIN32(ERROR_TIMEOUT);
    if(FAILED(hr))return hr;
    if(!*result)return ERROR_INVALID_DATA;
    VariantInit(&v);hr=IWbemClassObject_Get(*result,L"ReturnValue",0,&v,NULL,NULL);
    if(SUCCEEDED(hr)&&(V_VT(&v)==VT_I4||V_VT(&v)==VT_UI4))e=(LONG)V_UI4(&v);else e=FAILED(hr)?hr:ERROR_INVALID_DATA;
    VariantClear(&v);
    if(e){IWbemClassObject_Release(*result);*result=NULL;}return e;
}
static LONG user_call(const wchar_t *path,REGSAM view,const wchar_t *method,const wchar_t *name,const wchar_t *value,IWbemClassObject **result){
    LONG e=registry_open();if(e)return e;
    wchar_t full[CAP];if(wcslen(registry_sid)+wcslen(path)+2>=CAP)return ERROR_BUFFER_OVERFLOW;
    swprintf(full,CAP,L"%ls\\%ls",registry_sid,path);
    return registry_call(0x80000003,full,view,method,name,value,result);
}
static LONG read_call(BOOL machine,const wchar_t *path,REGSAM view,const wchar_t *method,const wchar_t *name,IWbemClassObject **result){
    return machine?registry_call(0x80000002,path,view,method,name,NULL,result):user_call(path,view,method,name,NULL,result);
}
static LONG provider_read(BOOL machine,const wchar_t *path,REGSAM view,const wchar_t *name,wchar_t *value,DWORD chars){
    IWbemClassObject *result=NULL;LONG e=read_call(machine,path,view,L"GetStringValue",name?name:L"",&result);
    if(e==1){
        /* StdRegProv returns 1 for an absent value, but never infer absence
         * from a failed string conversion alone. Type mismatch HRESULTs stay errors. */
        LONG check=read_call(machine,path,view,L"GetBinaryValue",name?name:L"",&result);
        if(result)IWbemClassObject_Release(result);result=NULL;
        if(check!=1)return check?check:ERROR_INVALID_DATA;
        check=read_call(machine,path,view,L"EnumValues",NULL,&result);
        if(check)return check;
        VARIANT names;VariantInit(&names);
        HRESULT hr=IWbemClassObject_Get(result,L"sNames",0,&names,NULL,NULL);
        IWbemClassObject_Release(result);result=NULL;
        if(FAILED(hr)){VariantClear(&names);return hr;}
        if(V_VT(&names)==(VT_ARRAY|VT_BSTR)){
            LONG lo=0,hi=-1;
            hr=SafeArrayGetLBound(V_ARRAY(&names),1,&lo);
            if(SUCCEEDED(hr))hr=SafeArrayGetUBound(V_ARRAY(&names),1,&hi);
            for(LONG i=lo;SUCCEEDED(hr)&&i<=hi;i++){
                BSTR found=NULL;hr=SafeArrayGetElement(V_ARRAY(&names),&i,&found);
                BOOL same=found&&!_wcsicmp(found,name?name:L"");SysFreeString(found);
                if(same){VariantClear(&names);return ERROR_INVALID_DATA;}
            }
        }else if(V_VT(&names)!=VT_NULL&&V_VT(&names)!=VT_EMPTY)hr=E_UNEXPECTED;
        VariantClear(&names);
        return FAILED(hr)?hr:ERROR_FILE_NOT_FOUND;
    }
    if(e)return e;VARIANT v;VariantInit(&v);HRESULT hr=IWbemClassObject_Get(result,L"sValue",0,&v,NULL,NULL);
    if(FAILED(hr))e=hr;
    else if(V_VT(&v)!=VT_BSTR||!V_BSTR(&v))e=ERROR_INVALID_DATA;
    else if(SysStringLen(V_BSTR(&v))>=chars)e=ERROR_MORE_DATA;
    else wcscpy(value,V_BSTR(&v));
    VariantClear(&v);IWbemClassObject_Release(result);return e;
}
static LONG external_read(const wchar_t *path,REGSAM view,const wchar_t *name,wchar_t *value,DWORD chars){
    return provider_read(FALSE,path,view,name,value,chars);
}
static LONG external_names(const wchar_t *path,REGSAM view,const wchar_t *method,VARIANT *names){
    IWbemClassObject *result=NULL;VariantInit(names);
    LONG e=user_call(path,view,method,NULL,NULL,&result);if(e)return e;
    HRESULT hr=IWbemClassObject_Get(result,L"sNames",0,names,NULL,NULL);IWbemClassObject_Release(result);
    if(FAILED(hr))return hr;
    if(V_VT(names)!=VT_NULL&&V_VT(names)!=VT_EMPTY&&V_VT(names)!=(VT_ARRAY|VT_BSTR))return ERROR_INVALID_DATA;
    return ERROR_SUCCESS;
}
static ULONG name_count(VARIANT *v){
    if(V_VT(v)==VT_NULL||V_VT(v)==VT_EMPTY)return 0;
    LONG lo=0,hi=-1;if(FAILED(SafeArrayGetLBound(V_ARRAY(v),1,&lo))||FAILED(SafeArrayGetUBound(V_ARRAY(v),1,&hi)))return 0xffffffff;
    return hi>=lo?(ULONG)(hi-lo+1):0;
}
static LONG external_occupied(const wchar_t *path,REGSAM view,BOOL *occupied){
    VARIANT values,children;*occupied=FALSE;
    LONG e=external_names(path,view,L"EnumValues",&values);if(e){VariantClear(&values);return e;}
    if(name_count(&values))*occupied=TRUE;VariantClear(&values);
    wchar_t default_value[CAP];e=external_read(path,view,NULL,default_value,CAP);
    if(!e)*occupied=TRUE;else if(e!=ERROR_FILE_NOT_FOUND)return e;
    e=external_names(path,view,L"EnumKey",&children);if(e){VariantClear(&children);return e;}
    if(name_count(&children))*occupied=TRUE;VariantClear(&children);return ERROR_SUCCESS;
}
static LONG external_set(const wchar_t *path,REGSAM view,const wchar_t *name,const wchar_t *value){
    IWbemClassObject *result=NULL;LONG e=user_call(path,view,L"CreateKey",NULL,NULL,&result);
    if(result)IWbemClassObject_Release(result);if(e)return e;
    e=user_call(path,view,L"SetStringValue",name?name:L"",value,&result);
    if(result)IWbemClassObject_Release(result);return e;
}
static LONG external_delete_value(const wchar_t *path,REGSAM view,const wchar_t *name){
    IWbemClassObject *result=NULL;LONG e=user_call(path,view,L"DeleteValue",name?name:L"",NULL,&result);
    if(result)IWbemClassObject_Release(result);return e;
}
static LONG external_remove_empty(const wchar_t *path,REGSAM view){
    BOOL occupied=TRUE;LONG e=external_occupied(path,view,&occupied);
    if(e==ERROR_FILE_NOT_FOUND)return ERROR_SUCCESS;if(e||occupied)return e;
    IWbemClassObject *result=NULL;e=user_call(path,view,L"DeleteKey",NULL,NULL,&result);
    if(result)IWbemClassObject_Release(result);return e;
}
#endif
