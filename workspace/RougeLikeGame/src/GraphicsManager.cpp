#include "GraphicsManager.hpp"

void GraphicsManager::clear(sf::RenderWindow& window, const sf::Color& color) {
    window.clear(color);
}

void GraphicsManager::renderEntity(const sf::Sprite& sprite, sf::RenderWindow& window) const {
    window.draw(sprite);
}

void GraphicsManager::renderItem(const sf::Sprite& sprite, sf::RenderWindow& window) const {
    window.draw(sprite);
}

void GraphicsManager::renderUI(sf::RenderWindow& window, const std::shared_ptr<class Player> player, int level) const {
    // Рендерим здоровье игрока
    drawHealthBar(window, 10, 10, player->getHealth(), player->getMaxHealth(), sf::Color::Red);
    
    // Уровень
    sf::Text levelText("Level: " + std::to_string(level), sf::Font(), 24);
    levelText.setPosition(10, 50);
    window.draw(levelText);
}

void GraphicsManager::drawHealthBar(sf::RenderWindow& window, float x, float y, int current, int max, const sf::Color& color) const {
    if (max <= 0) return;
    
    float barWidth = 200.0f;
    float barHeight = 20.0f;
    float fillWidth = (static_cast<float>(current) / static_cast<float>(max)) * barWidth;
    
    // Фон полоски здоровья
    sf::RectangleShape background(sf::Vector2f(barWidth, barHeight));
    background.setFillColor(sf::Color(50, 50, 50));
    background.setPosition(x, y);
    window.draw(background);
    
    // Заполненная часть
    sf::RectangleShape fill(sf::Vector2f(fillWidth, barHeight));
    fill.setFillColor(color);
    fill.setPosition(x, y);
    window.draw(fill);
}
