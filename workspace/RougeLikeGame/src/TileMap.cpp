#include "TileMap.hpp"

TileMap::TileMap(int width, int height)
    : width(width)
    , height(height) {
}

void TileMap::render(sf::RenderWindow& window, int level) const {
    // Рендерим пол подземелья
    sf::RectangleShape floor(sf::Vector2f(width * 64, height * 64));
    floor.setFillColor(sf::Color(50, 70, 40));
    floor.setPosition(0, 0);
    window.draw(floor);
    
    // Рендерим стены/препятствия
    sf::RectangleShape wall(sf::Vector2f(64, 64));
    for (int y = 0; y < height; ++y) {
        for (int x = 0; x < width; ++x) {
            if ((x + y) % 3 == 0) { // Простая генерация стен
                wall.setFillColor(sf::Color(80, 60, 40));
                wall.setPosition(x * 64, y * 64);
                window.draw(wall);
            }
        }
    }
}
