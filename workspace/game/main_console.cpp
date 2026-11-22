#include <windows.h>
#include "game.h"

// Функция main для консольного запуска (запускает WinMain)
int main(int argc, char* argv[]) {
    // Для Windows GUI приложений используем GetModuleHandleW(nullptr)
    HINSTANCE hInstance = reinterpret_cast<HINSTANCE>(GetModuleHandleW(NULL));
    HINSTANCE hPrevInstance = NULL;
    LPSTR lpCmdLine = "";
    int nCmdShow = SW_SHOWNORMAL;
    
    // Запускаем WinMain
    return WinMain(hInstance, hPrevInstance, lpCmdLine, nCmdShow);
}
