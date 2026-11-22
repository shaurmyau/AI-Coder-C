#include <windows.h>
#include "game.h"

// Функция main для консольного запуска (запускает WinMain)
int main(int argc, char* argv[]) {
    // Для Windows-приложений нужно использовать WinMain
    HINSTANCE hInstance = reinterpret_cast<HINSTANCE>(argc > 0 ? (HINSTANCE)&argv[0] : NULL);
    HINSTANCE hPrevInstance = NULL;
    LPSTR lpCmdLine = "";
    int nCmdShow = SW_SHOWDEFAULT;
    
    // Запускаем WinMain
    return WinMain(hInstance, hPrevInstance, lpCmdLine, nCmdShow);
}
