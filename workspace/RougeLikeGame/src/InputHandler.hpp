#pragma once

#include <SFML/Graphics.hpp>
#include "Player.hpp"
#include "Dungeon.hpp"

class InputHandler {
public:
    void handleEvent(const sf::Event& event, std::unique_ptr<Player>& player, Dungeon& dungeon);
    
private:
    void handleMovement(sf::Keyboard::Key key, Player& player);
};
