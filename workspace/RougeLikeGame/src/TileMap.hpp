#pragma once

#include <SFML/Graphics.hpp>

class TileMap {
public:
    explicit TileMap(int width, int height);
    ~TileMap() = default;
    
    void render(sf::RenderWindow& window, int level) const;
    
private:
    int width;
    int height;
};
