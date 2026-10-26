/* Run outside an MSIX host's private registry view. Uses only disposable keys. */
#define wWinMain unused_app_main
#include "../packaging/Launcher.c"
#undef wWinMain
#include <assert.h>

int main(void){
    wchar_t path[256],value[128];
    swprintf(path,256,L"Software\\Classes\\CamTetherTest-%lu-%llu",GetCurrentProcessId(),GetTickCount64());
    for(unsigned i=0;i<2;i++){
        REGSAM view=i?KEY_WOW64_32KEY:KEY_WOW64_64KEY;
        BOOL occupied=FALSE;
        assert(external_read(path,view,L"missing",value,128)==ERROR_FILE_NOT_FOUND);
        assert(external_set(path,view,L"owned",L"test")==0);
        assert(external_read(path,view,L"owned",value,128)==0&&!wcscmp(value,L"test"));
        assert(external_read(path,view,L"missing",value,128)==ERROR_FILE_NOT_FOUND);
        assert(external_delete_value(path,view,L"owned")==0);
        assert(external_read(path,view,NULL,value,128)==ERROR_FILE_NOT_FOUND);
        HKEY key=NULL;assert(RegOpenKeyExW(HKEY_CURRENT_USER,path,0,KEY_SET_VALUE|view,&key)==0);
        DWORD number=42;
        for(unsigned kind=0;kind<2;kind++){
            assert(RegSetValueExW(key,NULL,0,kind?REG_NONE:REG_DWORD,(BYTE*)&number,sizeof(number))==0);
            assert(external_read(path,view,NULL,value,128)!=0);
            LONG e=external_occupied(path,view,&occupied);
            assert(e!=0||occupied);
            assert(external_remove_empty(path,view)!=0);
            DWORD bytes=sizeof(number),type=0;
            assert(RegQueryValueExW(key,NULL,NULL,&type,(BYTE*)&number,&bytes)==0);
            assert(type==(kind?REG_NONE:REG_DWORD));
        }
        assert(RegDeleteValueW(key,NULL)==0);RegCloseKey(key);
        assert(external_remove_empty(path,view)==0);
        assert(external_read(path,view,NULL,value,128)==ERROR_FILE_NOT_FOUND);
    }
    registry_close();puts("PASS: both views; missing values; string values; unknown default types preserved; empty-key cleanup");
    return 0;
}
