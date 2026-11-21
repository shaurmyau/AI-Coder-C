#include "Dungeon.hpp"
#include <random>
#include <cmath>

Dungeon::Dungeon(int width, int height)
    : width(width)
    , height(height)
    , level(1) {
    
    // Инициализация текстур для тайлов
    floorTexture.loadFromMemory(sf::Texture::makeImage(64, 64), sf::Color(50, 70, 40));
    wallTexture.loadFromMemory(sf::Texture::makeImage(64, 64), sf::Color(80, 60, 40));
}

void Dungeon::generateLevel(int levelNumber) {
    level = levelNumber;
    monsters.clear();
    items.clear();
    
    // Процедурная генерация: создаём врагов и предметы
    std::random_device rd;
    std::mt19983 gen(rd());
    std::uniform_int_distribution<> xPos(0, width - 1);
    std::uniform_int_distribution<> yPos(0, height - 1);
    
    // Количество врагов зависит от уровня
    int enemyCount = 3 + levelNumber;
    for (int i = 0; i < enemyCount; ++i) {
        Monster::Type type = static_cast<Monster::Type>(xPos(gen) % 5);
        if (levelNumber >= 5 && xPos(gen) % 10 == 0) {
            type = Monster::Type::BOSS;
        }
        
        auto monster = std::make_unique<Monster>(graphicsManager, *this, type);
        monster->position.left = xPos(gen) * 64 + 32;
        monster->position.top = yPos(gen) * 64 + 32;
        monsters.push_back(std::move(monster));
    }
    
    // Создаём предметы
    int itemCount = 1 + levelNumber / 2;
    for (int i = 0; i < itemCount; ++i) {
        Item::Type itemType = static_cast<Item::Type>(xPos(gen) % 8);
        auto item = std::make_unique<Item>(itemType, "Item");
        item->position.left = xPos(gen) * 64 + 32;
        item->position.top = yPos(gen) * 32 + 32;
        items.push_back(std::move(item));
    }
    
    // Устанавливаем позицию игрока в начале уровня
    playerPosition = sf::FloatRect(50, 50, 40, 60);
}

bool Dungeon::getTileAt(int x, int y) const {
    return false; // Простая реализация - все тайлы проходимы
}

sf::Color Dungeon::getTileColor(int x, int y) const {
    return sf::Color(50, 70, 40);
}

void Dungeon::addMonster(std::unique_ptr<Monster> monster) {
    monsters.push_back(std::move(monster));
}

void Dungeon::removeDeadMonsters() {
    monsters.erase(
        std::remove_if(monsters.begin(), monsters.end(),
            [](const auto& m) { return m && m->isDead(); }),
        monsters.end()
    );
}

void Dungeon::addItem(std::unique_ptr<Item> item) {
    items.push_back(std::move(item));
}
