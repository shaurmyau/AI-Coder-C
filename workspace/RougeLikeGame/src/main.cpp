#include "Game.hpp"
#include <iostream>

int main() {
    try {
        Game game;
        if (game.init()) {
            game.run();
        } else {
            std::cerr << "Failed to initialize the game." << std::endl;
            return 1;
        }
    } catch (const std::exception& e) {
        std::cerr << "Error: " << e.what() << std::endl;
        return 1;
    }

    return 0;
}
