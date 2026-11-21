#include "game.h"
#include <cassert>
#include <iostream>

// Тесты для проверки логики игры (без графического интерфейса)

void test_player_movement() {
    GameState state;
    init_game(state);
    
    // Изначально игрок должен быть в свободном месте
    assert(state.player.alive == true);
    assert(state.player.health == 100);
    
    std::cout << "✓ Тест движения игрока пройден\n";
}

void test_enemy_spawning() {
    GameState state;
    init_game(state);
    
    // Изначально нет врагов
    assert(state.enemies.empty() == true);
    
    // Симулируем спавн (пропускаем таймер)
    state.enemySpawnTimer = GameState::ENEMY_SPAWN_INTERVAL + 10;
    spawn_enemies(state);
    
    // Должны появиться враги
    assert(!state.enemies.empty());
    
    std::cout << "✓ Тест спавна врагов пройден\n";
}

void test_enemy_ai() {
    GameState state;
    init_game(state);
    
    // Создаём одного врага
    Enemy enemy;
    enemy.id = 0;
    enemy.x = 5;
    enemy.y = 5;
    enemy.health = 30;
    enemy.alive = true;
    state.enemies.push_back(enemy);
    
    // Игрок далеко от врага
    move_player(state, 1, 0); // Двигаем игрока вправо
    
    update_enemies(state);
    
    // Враг должен двигаться к игроку
    assert(std::abs(state.player.x - state.enemies[0].x) <= 
           std::abs(state.player.y - state.enemies[0].y));
    
    std::cout << "✓ Тест AI врагов пройден\n";
}

void test_collision_detection() {
    GameState state;
    init_game(state);
    
    // Создаём стену
    state.tiles[2][2].is_wall = true;
    
    // Игрок пытается пройти через стену
    move_player(state, 1, 0);
    assert(state.player.x == 2);
    
    move_player(state, 1, 0); // Должно не сработать
    assert(state.player.x == 2);
    
    std::cout << "✓ Тест коллизий пройден\n";
}

void test_enemy_damage() {
    GameState state;
    init_game(state);
    
    // Создаём врага рядом с игроком
    Enemy enemy;
    enemy.id = 0;
    enemy.x = state.player.x;
    enemy.y = state.player.y;
    enemy.health = 30;
    enemy.alive = true;
    state.enemies.push_back(enemy);
    
    // Враг должен нанести урон
    update_enemies(state);
    
    assert(state.player.health < 100);
    
    std::cout << "✓ Тест урона от врагов пройден\n";
}

void test_game_over() {
    GameState state;
    init_game(state);
    
    // Создаём врага рядом с игроком
    Enemy enemy;
    enemy.id = 0;
    enemy.x = state.player.x;
    enemy.y = state.player.y;
    enemy.health = 30;
    enemy.damage = 100; // Очень высокий урон
    enemy.alive = true;
    state.enemies.push_back(enemy);
    
    update_enemies(state);
    
    assert(state.gameOver == true);
    assert(state.player.alive == false);
    
    std::cout << "✓ Тест Game Over пройден\n";
}

int main() {
    std::cout << "=== Запуск тестов Dungeon Crawler ===\n\n";
    
    test_player_movement();
    test_enemy_spawning();
    test_collision_detection();
    test_enemy_ai();
    test_enemy_damage();
    test_game_over();
    
    std::cout << "\n=== Все тесты пройдены! ===\n";
    return 0;
}
