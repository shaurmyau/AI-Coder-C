#include "game.h"
#include <random>

void init_game(GameState& state) {
    // Инициализация генератора случайных чисел
    srand(static_cast<unsigned int>(time(nullptr)));
    reset_game(state);
}

void reset_game(GameState& state) {
    // Сброс игрока
    state.player.x = 1;
    state.player.y = 1;
    state.player.health = state.player.maxHealth;
    state.player.alive = true;
    
    // Очистка врагов
    state.enemies.clear();
    
    // Генерация карты (простая: стены по краям, случайные препятствия)
    for (int y = 0; y < MAP_HEIGHT; ++y) {
        for (int x = 0; x < MAP_WIDTH; ++x) {
            state.tiles[x][y].is_wall = false;
            state.tiles[x][y].is_door = false;
            
            // Стены по краям
            if (x == 0 || x == MAP_WIDTH - 1 || y == 0 || y == MAP_HEIGHT - 1) {
                state.tiles[x][y].is_wall = true;
            }
            // Случайные препятствия (20% шанс)
            else if (rand() % 100 < 20) {
                state.tiles[x][y].is_wall = true;
            }
        }
    }
    
    // Убедимся, что игрок не зажат в стене
    while (state.tiles[state.player.x][state.player.y].is_wall) {
        state.player.x += 1;
        if (state.player.x >= MAP_WIDTH - 1) state.player.x = 1;
    }
}

// Проверка коллизий
bool can_move(const GameState& state, int x, int y) {
    // Проверка границ
    if (x < 0 || x >= MAP_WIDTH || y < 0 || y >= MAP_HEIGHT) {
        return false;
    }
    // Проверка стен
    if (state.tiles[x][y].is_wall) {
        return false;
    }
    // Проверка врагов
    for (const auto& enemy : state.enemies) {
        if (enemy.alive && enemy.x == x && enemy.y == y) {
            return false;
        }
    }
    return true;
}

// Движение игрока
void move_player(GameState& state, int dx, int dy) {
    if (!state.player.alive || state.gameOver) return;
    
    int newX = state.player.x + dx;
    int newY = state.player.y + dy;
    
    if (can_move(state, newX, newY)) {
        state.player.x = newX;
        state.player.y = newY;
    }
}

// AI врагов (простое преследование)
void update_enemies(GameState& state) {
    for (auto& enemy : state.enemies) {
        if (!enemy.alive) continue;
        
        int dx = state.player.x - enemy.x;
        int dy = state.player.y - enemy.y;
        int dist = std::abs(dx) + std::abs(dy);
        
        // Враг атакует, если близко
        if (dist <= 1) {
            state.player.health -= enemy.damage;
            if (state.player.health <= 0) {
                state.player.health = 0;
                state.player.alive = false;
                state.gameOver = true;
            }
            continue;
        }
        
        // Движение к игроку
        int moveX = dx / dist;
        int moveY = dy / dist;
        
        if (can_move(state, enemy.x + moveX, enemy.y)) {
            enemy.x += moveX;
        } else if (can_move(state, enemy.x, enemy.y + moveY)) {
            enemy.y += moveY;
        }
    }
}

// Спавн врагов
void spawn_enemies(GameState& state) {
    state.enemySpawnTimer++;
    
    if (state.enemySpawnTimer >= state.ENEMY_SPAWN_INTERVAL) {
        state.enemySpawnTimer = 0;
        
        // Спавним 1-3 врага в случайных местах
        int count = 1 + rand() % 3;
        for (int i = 0; i < count; ++i) {
            int ex, ey;
            do {
                ex = 2 + rand() % (MAP_WIDTH - 4);
                ey = 2 + rand() % (MAP_HEIGHT - 4);
            } while (!can_move(state, ex, ey));
            
            Enemy newEnemy;
            newEnemy.id = state.enemies.size();
            newEnemy.x = ex;
            newEnemy.y = ey;
            newEnemy.health = newEnemy.maxHealth;
            newEnemy.alive = true;
            state.enemies.push_back(newEnemy);
        }
    }
}

// Отрисовка тайла
void draw_tile(HDC hdc, int x, int y, const Tile& tile) {
    RECT rect = {x * TILE_SIZE, y * TILE_SIZE, (x + 1) * TILE_SIZE, (y + 1) * TILE_SIZE};
    
    if (tile.is_wall) {
        // Красный кирпич для стен
        HBRUSH wallBrush = CreateSolidBrush(RGB(139, 69, 19)); // Brown
        FillRect(hdc, &rect, wallBrush);
        DeleteObject(wallBrush);
        
        // Обводка
        HPEN wallPen = CreatePen(PS_SOLID, 2, RGB(100, 50, 10));
        SelectObject(hdc, wallPen);
        Rectangle(hdc, x * TILE_SIZE, y * TILE_SIZE, (x + 1) * TILE_SIZE, (y + 1) * TILE_SIZE);
        DeleteObject(wallPen);
    } else {
        // Зеленая трава для пола
        HBRUSH floorBrush = CreateSolidBrush(RGB(34, 139, 34)); // Green
        FillRect(hdc, &rect, floorBrush);
        DeleteObject(floorBrush);
        
        HPEN floorPen = CreatePen(PS_SOLID, 2, RGB(50, 100, 50));
        SelectObject(hdc, floorPen);
        Rectangle(hdc, x * TILE_SIZE, y * TILE_SIZE, (x + 1) * TILE_SIZE, (y + 1) * TILE_SIZE);
        DeleteObject(floorPen);
    }
}

// Отрисовка игрока
void draw_player(HDC hdc, const Player& player) {
    if (!player.alive) return;
    
    RECT rect = {player.x * TILE_SIZE, player.y * TILE_SIZE, 
                 (player.x + 1) * TILE_SIZE, (player.y + 1) * TILE_SIZE};
    
    // Синий круг для игрока
    HBRUSH playerBrush = CreateSolidBrush(RGB(0, 120, 255)); // Blue
    FillRect(hdc, &rect, playerBrush);
    DeleteObject(playerBrush);
    
    HPEN playerPen = CreatePen(PS_SOLID, 2, RGB(0, 200, 255));
    SelectObject(hdc, playerPen);
    InflateRect(&rect, 4, 4);
    Rectangle(hdc, rect.left, rect.top, rect.right, rect.bottom);
    DeleteObject(playerPen);
    
    // Полоска здоровья
    int healthBarWidth = TILE_SIZE - 8;
    RECT healthRect = {rect.left + 4, rect.bottom - 6, 
                       rect.left + healthBarWidth, rect.bottom};
    HBRUSH healthBrush = CreateSolidBrush(RGB(255, 0, 0)); // Red for damage taken
    FillRect(hdc, &healthRect, healthBrush);
    DeleteObject(healthBrush);
    
    int healthPercent = (player.health * 100) / player.maxHealth;
    RECT greenHealthRect = {rect.left + 4, rect.bottom - 6, 
                            rect.left + (healthBarWidth * healthPercent) / 100, rect.bottom};
    HBRUSH greenHealthBrush = CreateSolidBrush(RGB(0, 255, 0)); // Green for health
    FillRect(hdc, &greenHealthRect, greenHealthBrush);
    DeleteObject(greenHealthBrush);
}

// Отрисовка врага
void draw_enemy(HDC hdc, const Enemy& enemy) {
    if (!enemy.alive) return;
    
    RECT rect = {enemy.x * TILE_SIZE, enemy.y * TILE_SIZE, 
                 (enemy.x + 1) * TILE_SIZE, (enemy.y + 1) * TILE_SIZE};
    
    // Красный квадрат для врага
    HBRUSH enemyBrush = CreateSolidBrush(RGB(255, 0, 0)); // Red
    FillRect(hdc, &rect, enemyBrush);
    DeleteObject(enemyBrush);
    
    HPEN enemyPen = CreatePen(PS_SOLID, 2, RGB(180, 0, 0));
    SelectObject(hdc, enemyPen);
    InflateRect(&rect, 4, 4);
    Rectangle(hdc, rect.left, rect.top, rect.right, rect.bottom);
    DeleteObject(enemyPen);
    
    // Полоска здоровья врага
    int healthBarWidth = TILE_SIZE - 8;
    RECT enemyHealthRect = {rect.left + 4, rect.bottom - 6, 
                            rect.left + healthBarWidth, rect.bottom};
    HBRUSH enemyHealthBrush = CreateSolidBrush(RGB(255, 0, 0)); // Red for damage taken
    FillRect(hdc, &enemyHealthRect, enemyHealthBrush);
    DeleteObject(enemyHealthBrush);
    
    int enemyHealthPercent = (enemy.health * 100) / enemy.maxHealth;
    RECT greenEnemyHealthRect = {rect.left + 4, rect.bottom - 6, 
                                 rect.left + (healthBarWidth * enemyHealthPercent) / 100, rect.bottom};
    HBRUSH greenEnemyHealthBrush = CreateSolidBrush(RGB(0, 255, 0)); // Green for health
    FillRect(hdc, &greenEnemyHealthRect, greenEnemyHealthBrush);
    DeleteObject(greenEnemyHealthBrush);
}

// Отрисовка интерфейса
void draw_ui(HDC hdc, const GameState& state) {
    // Заголовок
    HFONT titleFont = CreateFontA(
        24, 0, 0, 0, FW_BOLD, FALSE, FALSE, FALSE,
        DEFAULT_CHARSET, OUT_DEFAULT_PRECIS, CLIP_DEFAULT_PRECIS,
        CLEARTYPE_QUALITY, DEFAULT_PITCH | FF_DONTCARE, "Arial"
    );
    
    HGDIOBJ oldFont = SelectObject(hdc, titleFont);
    
    // Заголовок игры
    SetBkMode(hdc, TRANSPARENT);
    TextOutA(hdc, 10, 10, "Dungeon Crawler", 16);
    
    // Статистика игрока
    char playerStats[256];
    int aliveEnemies = 0;
    for (const auto& enemy : state.enemies) {
        if (enemy.alive) aliveEnemies++;
    }
    sprintf_s(playerStats, sizeof(playerStats), 
              "HP: %d/%d | Врагов осталось: %d",
              state.player.health, state.player.maxHealth, aliveEnemies);
    TextOutA(hdc, 10, 45, playerStats, strlen(playerStats));
    
    // Статус игры
    if (state.gameOver) {
        SetBkMode(hdc, TRANSPARENT);
        TextOutA(hdc, SCREEN_WIDTH / 2 - 100, SCREEN_HEIGHT / 2, 
                 "GAME OVER", 11);
        
        TextOutA(hdc, SCREEN_WIDTH / 2 - 80, SCREEN_HEIGHT / 2 + 30, 
                 "Нажмите любую клавишу для рестарта", 34);
    }
    
    SelectObject(hdc, oldFont);
    DeleteObject(titleFont);
}

// Обработка сообщений Windows
LRESULT CALLBACK WndProc(HWND hwnd, UINT msg, WPARAM wParam, LPARAM lParam) {
    switch (msg) {
        case WM_CREATE:
            // Инициализация уже выполнена в WinMain
            return 0;
            
        case WM_ERASEBKGND: {
            // Всегда возвращаем TRUE, чтобы окно перерисовывалось
            PAINTSTRUCT ps;
            HDC hdc = BeginPaint(hwnd, &ps);
            
            // Очистка фона
            HBRUSH whiteBrush = CreateSolidBrush(RGB(240, 240, 240));
            RECT clientRect = {0, 0, SCREEN_WIDTH, SCREEN_HEIGHT};
            FillRect(hdc, &clientRect, whiteBrush);
            DeleteObject(whiteBrush);
            
            // Отрисовка карты
            GameState* state = reinterpret_cast<GameState*>(GetWindowLongPtr(hwnd, GWLP_USERDATA));
            for (int y = 0; y < MAP_HEIGHT; ++y) {
                for (int x = 0; x < MAP_WIDTH; ++x) {
                    draw_tile(hdc, x, y, state->tiles[x][y]);
                }
            }
            
            // Отрисовка врагов
            for (const auto& enemy : state->enemies) {
                draw_enemy(hdc, enemy);
            }
            
            // Отрисовка игрока
            draw_player(hdc, state->player);
            
            // Отрисовка UI
            draw_ui(hdc, *state);
            
            EndPaint(hwnd, &ps);
            return TRUE;
        }
            
        case WM_KEYDOWN: {
            if (wParam == VK_ESCAPE) {
                PostQuitMessage(0);
                return 0;
            }
            
            // Движение игрока
            int dx = 0, dy = 0;
            switch (wParam) {
                case 'W': case '8': case VK_UP: dy = -1; break;
                case 'S': case '2': case VK_DOWN: dy = 1; break;
                case 'A': case '4': case VK_LEFT: dx = -1; break;
                case 'D': case '6': case VK_RIGHT: dx = 1; break;
            }
            
            if (dx != 0 || dy != 0) {
                move_player(*reinterpret_cast<GameState*>(GetWindowLongPtr(hwnd, GWLP_USERDATA)), dx, dy);
            }
            return 0;
        }
            
        case WM_CHAR: {
            // Рестарт игры по любой клавише (если игра окончена)
            GameState* state = reinterpret_cast<GameState*>(GetWindowLongPtr(hwnd, GWLP_USERDATA));
            if (state && state->gameOver) {
                reset_game(*state);
            }
            return 0;
        }
            
        case WM_PAINT: {
            PAINTSTRUCT ps;
            HDC hdc = BeginPaint(hwnd, &ps);
            
            // Очистка фона
            HBRUSH whiteBrush = CreateSolidBrush(RGB(240, 240, 240));
            RECT clientRect = {0, 0, SCREEN_WIDTH, SCREEN_HEIGHT};
            FillRect(hdc, &clientRect, whiteBrush);
            DeleteObject(whiteBrush);
            
            // Отрисовка карты
            GameState* state = reinterpret_cast<GameState*>(GetWindowLongPtr(hwnd, GWLP_USERDATA));
            for (int y = 0; y < MAP_HEIGHT; ++y) {
                for (int x = 0; x < MAP_WIDTH; ++x) {
                    draw_tile(hdc, x, y, state->tiles[x][y]);
                }
            }
            
            // Отрисовка врагов
            for (const auto& enemy : state->enemies) {
                draw_enemy(hdc, enemy);
            }
            
            // Отрисовка игрока
            draw_player(hdc, state->player);
            
            // Отрисовка UI
            draw_ui(hdc, *state);
            
            EndPaint(hwnd, &ps);
            return 0;
        }
        
        case WM_DESTROY:
            PostQuitMessage(0);
            return 0;
    }
    
    return DefWindowProc(hwnd, msg, wParam, lParam);
}
