#pragma once

#include <SFML/Graphics.hpp>

class ParticleSystem {
public:
    void update(float deltaTime);
    void render(sf::RenderWindow& window) const;
    
private:
    std::vector<sf::ParticleEmitters> emitters;
};
