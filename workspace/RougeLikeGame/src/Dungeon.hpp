#pragma once

#include <SFML/Graphics.hpp>
#include <memory>
#include "Player.hpp"
#include "Monster.hpp"
#include "Item.hpp"

class Dungeon {
public:
    explicit Dungeon(int width = 20, int height = 15);
    ~Dungeon() = default;
    
    // Процедурная генерация уровня
    void generateLevel(int levelNumber);
    
    // Получение информации о тайлах
    bool getTileAt(int x, int y) const;
    sf::Color getTileColor(int x, int y) const;
    
    // Игрок и сущности
    std::optional<sf::FloatRect> getPlayerPosition() const { return playerPosition; }
    void setPlayerPosition(const sf::FloatRect& pos) { playerPosition = pos; }
    
    // Враги
    std::vector<std::unique_ptr<Monster>> getMonsters() const { return monsters; }
    void addMonster(std::unique_ptr<Monster> monster);
    void removeDeadMonsters();
    
    // Предметы
    std::vector<std::unique_ptr<Item>> getItems() const { return items; }
    void addItem(std::unique_ptr<Item> item);
    
    // Уровень
    int getWidth() const { return width; }
    int getHeight() const { return height; }
    int getLevel() const { return level; }
    
private:
    int width;
    int height;
    int level;
    std::vector<std::unique_ptr<Monster>> monsters;
    std::vector<std::unique_ptr<Item>> items;
    std::optional<sf::FloatRect> playerPosition;
    sf::Texture floorTexture;
    sf::Texture wallTexture;
};
