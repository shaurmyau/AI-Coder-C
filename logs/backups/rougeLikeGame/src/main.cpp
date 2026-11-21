#include <SFML/Graphics.hpp>
#include <cmath>
#include <optional>

int main()
{
    sf::RenderWindow window(sf::VideoMode({1280u, 720u}), "SFML 3 - C++20 Game");
    window.setFramerateLimit(144);

    sf::RectangleShape player({48.0f, 48.0f});
    player.setFillColor(sf::Color(80, 190, 255));
    player.setPosition({616.0f, 336.0f});

    sf::Clock clock;
    constexpr float speed = 280.0f;

    while (window.isOpen())
    {
        while (const std::optional event = window.pollEvent())
        {
            if (event->is<sf::Event::Closed>())
                window.close();
        }

        const float dt = clock.restart().asSeconds();
        sf::Vector2f direction{0.0f, 0.0f};
        if (sf::Keyboard::isKeyPressed(sf::Keyboard::Key::W)) direction.y -= 1.0f;
        if (sf::Keyboard::isKeyPressed(sf::Keyboard::Key::S)) direction.y += 1.0f;
        if (sf::Keyboard::isKeyPressed(sf::Keyboard::Key::A)) direction.x -= 1.0f;
        if (sf::Keyboard::isKeyPressed(sf::Keyboard::Key::D)) direction.x += 1.0f;

        const float length = std::sqrt(direction.x * direction.x + direction.y * direction.y);
        if (length > 0.0f)
        {
            direction.x /= length;
            direction.y /= length;
            player.move(direction * speed * dt);
        }

        window.clear(sf::Color(22, 26, 36));
        window.draw(player);
        window.display();
    }
    return 0;
}
