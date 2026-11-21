#include "InputHandler.hpp"

void InputHandler::handleEvent(const sf::Event& event, std::unique_ptr<Player>& player, Dungeon& dungeon) {
    if (event.type == sf::Event::KeyPressed) {
        handleMovement(event.key.code, *player);
        
        // Атака по пробелу
        if (event.key.code == sf::Keyboard::Space) {
            player->attack();
        }
        
        // Использование предмета по E
        if (event.key.code == sf::Keyboard::E) {
            player->useItem();
        }
    }
}

void InputHandler::handleMovement(sf::Keyboard::Key key, Player& player) {
    switch (key) {
        case sf::Keyboard::Up:
            player.moveUp();
            break;
        case sf::Keyboard::Down:
            player.moveDown();
            break;
        case sf::Keyboard::Left:
            player.moveLeft();
            break;
        case sf::Keyboard::Right:
            player.moveRight();
            break;
    }
}
