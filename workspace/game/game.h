#pragma once

#include <windows.h>
#include <vector>
#include <algorithm>
#include <ctime>

// Константы игры
constexpr int TILE_SIZE = 32;
constexpr int SCREEN_WIDTH = 800;
constexpr int SCREEN_HEIGHT = 600;
constexpr int MAP_WIDTH = SCREEN_WIDTH / TILE_SIZE;
constexpr int MAP_HEIGHT = SCREEN_HEIGHT / TILE_SIZE;

// Структура тайла карты
struct Tile {
    bool is_wall;
    bool is_door;
};

// Игрок
struct Player {
    int x, y;
    int health = 100;
    int maxHealth = 100;
    int damage = 5;
    bool alive = true;
};

// Враг
struct Enemy {
    int id;
    int x, y;
    int health = 30;
    int maxHealth = 30;
    int damage = 8;
    bool alive = true;
};

// Игровое состояние
struct GameState {
    Player player;
    std::vector<Enemy> enemies;
    Tile tiles[MAP_WIDTH][MAP_HEIGHT];
    int frameCount = 0;
    bool gameOver = false;
    
    // Спавн врагов каждые N кадров
    int enemySpawnTimer = 0;
    static constexpr int ENEMY_SPAWN_INTERVAL = 180; // ~3 секунды при 60 FPS
};

// Предварительное объявление функции WndProc
LRESULT CALLBACK WndProc(HWND, UINT, WPARAM, LPARAM);

// Обработка изменения размера окна
void OnSize(HWND hwnd, int width, int height);

// Функции инициализации
void init_game(GameState& state);
void reset_game(GameState& state);

// Игровые функции
void spawn_enemies(GameState& state);
void move_player(GameState& state, int dx, int dy);
void update_enemies(GameState& state);
