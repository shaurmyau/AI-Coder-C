#pragma once

#include <SFML/Graphics.hpp>

class GraphicsManager {
public:
    void clear(sf::RenderWindow& window, const sf::Color& color);
    void renderEntity(const sf::Sprite& sprite, sf::RenderWindow& window) const;
    void renderItem(const sf::Sprite& sprite, sf::RenderWindow& window) const;
    void renderUI(sf::RenderWindow& window, const std::shared_ptr<class Player> player, int level) const;
    
private:
    void drawHealthBar(sf::RenderWindow& window, float x, float y, int current, int max, const sf::Color& color) const;
};
