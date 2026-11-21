#include <windows.h>
#include "game.h"

// Регистрация классов Windows
ATOM MyRegisterClass(HINSTANCE hInstance) {
    WNDCLASSEXW wc = {};
    
    wc.cbSize = sizeof(WNDCLASSEX);
    wc.style = CS_HREDRAW | CS_VREDRAW;
    wc.lpfnWndProc = WndProc;
    wc.hInstance = hInstance;
    wc.hCursor = LoadCursor(NULL, IDC_ARROW);
    wc.hbrBackground = (HBRUSH)(COLOR_WINDOW + 1);
    wc.lpszClassName = L"DungeonCrawler";
    wc.hIcon = LoadIcon(NULL, IDI_APPLICATION);
    
    return RegisterClassExW(&wc);
}

// Создание окна
int WINAPI WinMain(HINSTANCE hInstance, HINSTANCE hPrevInstance, 
                   LPSTR lpCmdLine, int nCmdShow) {
    
    // Регистрация класса окна
    if (!MyRegisterClass(hInstance)) {
        return 0;
    }
    
    // Создание окна
    HWND hwnd = CreateWindowExW(
        0,
        L"DungeonCrawler",
        L"Dungeon Crawler - Простой рогалик",
        WS_OVERLAPPEDWINDOW,
        CW_USEDEFAULT, CW_USEDEFAULT,
        SCREEN_WIDTH, SCREEN_HEIGHT,
        NULL,
        NULL,
        hInstance,
        NULL
    );
    
    if (!hwnd) {
        return 0;
    }
    
    // Показываем окно
    ShowWindow(hwnd, nCmdShow);
    UpdateWindow(hwnd);
    
    // Создаём GameState и передаём его в окно
    GameState gameState;
    SetWindowLongPtr(hwnd, GWLP_USERDATA, reinterpret_cast<LONG_PTR>(&gameState));
    
    // Инициализация игры
    init_game(gameState);
    
    // Цикл сообщений Windows
    MSG msg;
    while (GetMessage(&msg, NULL, 0, 0) > 0) {
        TranslateMessage(&msg);
        DispatchMessage(&msg);
    }
    
    return (int)msg.wParam;
}
