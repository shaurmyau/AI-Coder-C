#include <SFML/Graphics.hpp>
#include <SFML/Window.hpp>
#include <SFML/System.hpp>
#include <iostream>
#include <memory>
#include <string>

// Простая пиксельная графика для демонстрации
class PixelSprite {
public:
    sf::Texture texture;
    sf::Sprite sprite;
    
    void loadPixelArt(const std::string& name) {
        // Создаем процедурную пиксельную графику
        sf::Image image = sf::Image::createFromData(32, 32);
        
        // Заполняем цветом в зависимости от типа сущности
        if (name == "hero") {
            // Герой - синий квадрат с деталями
            for (int y = 0; y < 32; ++y) {
                for (int x = 0; x < 32; ++x) {
                    int color = 0xFF000000;
                    if (y > 16 && x > 8 && x < 24) color = 0xFF00BFFF; // тело
                    else if (y > 16 && x > 16 && x < 20) color = 0xFFFF0000; // лицо
                    else if (y < 16 && x > 8 && x < 24) color = 0xFF00FFFF; // голова
                    else if (x > 24 && y > 16) color = 0xFFB222FF; // меч
                    image.setPixel(x, y, sf::Color(color >> 24, (color >> 16) & 0xFF, 
                                                       (color >> 8) & 0xFF, color & 0xFF));
                }
            }
        } else if (name == "enemy") {
            // Враг - красный квадрат
            for (int y = 0; y < 32; ++y) {
                for (int x = 0; x < 32; ++x) {
                    int color = 0xFF000000;
                    if (y > 8 && y < 24 && x > 8 && x < 24) color = 0xFFFF0000; // тело
                    else if (y < 16 || y > 24) color = 0xFF8B0000; // голова/ноги
                    image.setPixel(x, y, sf::Color(color >> 24, (color >> 16) & 0xFF, 
                                                       (color >> 8) & 0xFF, color & 0xFF));
                }
            }
        } else if (name == "treasure") {
            // Сокровище - золотой квадрат
            for (int y = 0; y < 32; ++y) {
                for (int x = 0; x < 32; ++x) {
                    int color = 0xFF000000;
                    if (y > 16 && x > 8 && x < 24) color = 0xFFFFD700; // тело
                    else if (y < 16 || y > 24) color = 0xFFFFA500; // границы
                    image.setPixel(x, y, sf::Color(color >> 24, (color >> 16) & 0xFF, 
                                                       (color >> 8) & 0xFF, color & 0xFF));
                }
            }
        } else if (name == "wall") {
            // Стена - серый камень
            for (int y = 0; y < 32; ++y) {
                for (int x = 0; x < 32; ++x) {
                    int color = 0xFF000000;
                    if ((x + y) % 2 == 0) color = 0xFF808080;
                    else color = 0xFF606060;
                    image.setPixel(x, y, sf::Color(color >> 24, (color >> 16) & 0xFF, 
                                                       (color >> 8) & 0xFF, color & 0xFF));
                }
            }
        } else if (name == "floor") {
            // Пол - темный камень
            for (int y = 0; y < 32; ++y) {
                for (int x = 0; x < 32; ++x) {
                    int color = 0xFF000000;
                    if ((x + y) % 4 == 0) color = 0xFF404040;
                    else color = 0xFF202020;
                    image.setPixel(x, y, sf::Color(color >> 24, (color >> 16) & 0xFF, 
                                                       (color >> 8) & 0xFF, color & 0xFF));
                }
            }
        } else if (name == "door") {
            // Дверь - коричневая
            for (int y = 0; y < 32; ++y) {
                for (int x = 0; x < 32; ++x) {
                    int color = 0xFF000000;
                    if (y > 8 && y < 24 && x > 8 && x < 24) color = 0xFF8B4513;
                    else color = 0xFF654321;
                    image.setPixel(x, y, sf::Color(color >> 24, (color >> 16) & 0xFF, 
                                                       (color >> 8) & 0xFF, color & 0xFF));
                }
            }
        } else if (name == "stairs") {
            // Лестница - желтая с черными полосами
            for (int y = 0; y < 32; ++y) {
                for (int x = 0; x < 32; ++x) {
                    int color = 0xFF000000;
                    if ((x + y) % 8 == 0) color = 0xFF000000;
                    else color = 0xFFFFA500;
                    image.setPixel(x, y, sf::Color(color >> 24, (color >> 16) & 0xFF, 
                                                       (color >> 8) & 0xFF, color & 0xFF));
                }
            }
        } else if (name == "heart") {
            // Сердце - красное
            for (int y = 0; y < 32; ++y) {
                for (int x = 0; x < 32; ++x) {
                    int color = 0xFF000000;
                    if (y > 16 && x > 8 && x < 24) color = 0xFFFF0000;
                    else if (y < 16 || y > 24) color = 0xFF8B0000;
                    image.setPixel(x, y, sf::Color(color >> 24, (color >> 16) & 0xFF, 
                                                       (color >> 8) & 0xFF, color & 0xFF));
                }
            }
        } else if (name == "potion") {
            // Зелье - зеленое
            for (int y = 0; y < 32; ++y) {
                for (int x = 0; x < 32; ++x) {
                    int color = 0xFF000000;
                    if (y > 8 && y < 24 && x > 8 && x < 24) color = 0xFF00FF00;
                    else color = 0xFF008000;
                    image.setPixel(x, y, sf::Color(color >> 24, (color >> 16) & 0xFF, 
                                                       (color >> 8) & 0xFF, color & 0xFF));
                }
            }
        } else if (name == "sword") {
            // Меч - серебристый
            for (int y = 0; y < 32; ++y) {
                for (int x = 0; x < 32; ++x) {
                    int color = 0xFF000000;
                    if (y > 16 && x > 8 && x < 24) color = 0xFFC0C0C0;
                    else if (y < 16 || y > 24) color = 0xFF707070;
                    image.setPixel(x, y, sf::Color(color >> 24, (color >> 16) & 0xFF, 
                                                       (color >> 8) & 0xFF, color & 0xFF));
                }
            }
        } else if (name == "shield") {
            // Щит - синий
            for (int y = 0; y < 32; ++y) {
                for (int x = 0; x < 32; ++x) {
                    int color = 0xFF000000;
                    if (y > 8 && y < 24 && x > 8 && x < 24) color = 0xFF00BFFF;
                    else color = 0xFF008080;
                    image.setPixel(x, y, sf::Color(color >> 24, (color >> 16) & 0xFF, 
                                                       (color >> 8) & 0xFF, color & 0xFF));
                }
            }
        } else if (name == "key") {
            // Ключ - золотой
            for (int y = 0; y < 32; ++y) {
                for (int x = 0; x < 32; ++x) {
                    int color = 0xFF000000;
                    if ((x + y) % 4 == 0) color = 0xFFDAA520;
                    else color = 0xFFB8860B;
                    image.setPixel(x, y, sf::Color(color >> 24, (color >> 16) & 0xFF, 
                                                       (color >> 8) & 0xFF, color & 0xFF));
                }
            }
        } else if (name == "gem") {
            // Алмаз - голубой
            for (int y = 0; y < 32; ++y) {
                for (int x = 0; x < 32; ++x) {
                    int color = 0xFF000000;
                    if ((x + y) % 8 == 0) color = 0xFF00FFFF;
                    else color = xFF00BFFF;
                    image.setPixel(x, y, sf::Color(color >> 24, (color >> 16) & 0xFF, 
                                                       (color >> 8) & 0xFF, color & 0xFF));
                }
            }
        } else if (name == "fire") {
            // Огонь - оранжевый
            for (int y = 0; y < 32; ++y) {
                for (int x = 0; x < 32; ++x) {
                    int color = 0xFF000000;
                    if ((x + y) % 4 == 0) color = 0xFFFF4500;
                    else color = 0xFFFF8C00;
                    image.setPixel(x, y, sf::Color(color >> 24, (color >> 16) & 0xFF, 
                                                       (color >> 8) & 0xFF, color & 0xFF));
                }
            }
        } else if (name == "ice") {
            // Лед - голубой
            for (int y = 0; y < 32; ++y) {
                for (int x = 0; x < 32; ++x) {
                    int color = 0xFF000000;
                    if ((x + y) % 4 == 0) color = 0xFFE0FFFF;
                    else color = 0xFFB0E0E6;
                    image.setPixel(x, y, sf::Color(color >> 24, (color >> 16) & 0xFF, 
                                                       (color >> 8) & 0xFF, color & 0xFF));
                }
            }
        } else if (name == "poison") {
            // Яд - зеленый с черными точками
            for (int y = 0; y < 32; ++y) {
                for (int x = 0; x < 32; ++x) {
                    int color = 0xFF000000;
                    if ((x + y) % 4 == 0) color = 0xFF00FF00;
                    else color = 0xFF008000;
                    image.setPixel(x, y, sf::Color(color >> 24, (color >> 16) & 0xFF, 
                                                       (color >> 8) & 0xFF, color & 0xFF));
                }
            }
        } else if (name == "spider") {
            // Паук - черный с красными глазами
            for (int y = 0; y < 32; ++y) {
                for (int x = 0; x < 32; ++x) {
                    int color = 0xFF000000;
                    if ((x + y) % 8 == 0) color = 0xFF1A1A1A;
                    else color = 0xFF0D0D0D;
                    image.setPixel(x, y, sf::Color(color >> 24, (color >> 16) & 0xFF, 
                                                       (color >> 8) & 0xFF, color & 0xFF));
                }
            }
        } else if (name == "skeleton") {
            // Скелет - белый с черными костями
            for (int y = 0; y < 32; ++y) {
                for (int x = 0; x < 32; ++x) {
                    int color = 0xFF000000;
                    if ((x + y) % 4 == 0) color = 0xFFF5F5DC;
                    else color = 0xFFE8E8D0;
                    image.setPixel(x, y, sf::Color(color >> 24, (color >> 16) & 0xFF, 
                                                       (color >> 8) & 0xFF, color & 0xFF));
                }
            }
        } else if (name == "orc") {
            // Орк - зеленый
            for (int y = 0; y < 32; ++y) {
                for (int x = 0; x < 32; ++x) {
                    int color = 0xFF000000;
                    if ((x + y) % 4 == 0) color = 0xFF228B22;
                    else color = 0xFF006400;
                    image.setPixel(x, y, sf::Color(color >> 24, (color >> 16) & 0xFF, 
                                                       (color >> 8) & 0xFF, color & 0xFF));
                }
            }
        } else if (name == "dragon") {
            // Дракон - красный с черными крыльями
            for (int y = 0; y < 32; ++y) {
                for (int x = 0; x < 32; ++x) {
                    int color = 0xFF000000;
                    if ((x + y) % 4 == 0) color = 0xFFDC143C;
                    else color = 0xFFB222FF;
                    image.setPixel(x, y, sf::Color(color >> 24, (color >> 16) & 0xFF, 
                                                       (color >> 8) & 0xFF, color & 0xFF));
                }
            }
        } else if (name == "boss") {
            // Босс - большой черный
            for (int y = 0; y < 32; ++y) {
                for (int x = 0; x < 32; ++x) {
                    int color = 0xFF000000;
                    if ((x + y) % 8 == 0) color = 0xFF2F4F4F;
                    else color = 0xFF1C1C1C;
                    image.setPixel(x, y, sf::Color(color >> 24, (color >> 16) & 0xFF, 
                                                       (color >> 8) & 0xFF, color & 0xFF));
                }
            }
        } else if (name == "empty") {
            // Пустота - прозрачная
            for (int y = 0; y < 32; ++y) {
                for (int x = 0; x < 32; ++x) {
                    image.setPixel(x, y, sf::Color(0, 0, 0, 0));
                }
            }
        }
        
        texture.loadFromImage(image);
        sprite.setTexture(texture);
    }
    
    void setOrigin(float x, float y) {
        sprite.setOrigin(x, y);
    }
    
    void setPosition(float x, float y) {
        sprite.setPosition(x, y);
    }
    
    sf::Sprite& getSprite() {
        return sprite;
    }
};

// Класс персонажа игрока
class Hero {
public:
    int health = 100;
    int maxHealth = 100;
    int attack = 10;
    int defense = 5;
    int level = 1;
    int xp = 0;
    int maxXp = 100;
    
    PixelSprite heroSprite;
    
    Hero() {
        heroSprite.loadPixelArt("hero");
        heroSprite.setOrigin(16, 16);
    }
    
    void takeDamage(int damage) {
        health -= damage;
        if (health < 0) health = 0;
    }
    
    void heal(int amount) {
        health += amount;
        if (health > maxHealth) health = maxHealth;
    }
    
    bool isAlive() const {
        return health > 0;
    }
};

// Класс врага
class Enemy {
public:
    std::string name;
    int health = 20;
    int maxHealth = 20;
    int attack = 5;
    int defense = 2;
    int xpValue = 10;
    
    PixelSprite enemySprite;
    sf::Texture deathTexture;
    
    Enemy(const std::string& type) {
        enemySprite.loadPixelArt(type);
        enemySprite.setOrigin(16, 16);
        
        // Создаем текстуру смерти (серый квадрат)
        sf::Image deathImg = sf::Image::createFromData(32, 32);
        for (int y = 0; y < 32; ++y) {
            for (int x = 0; x < 32; ++x) {
                deathImg.setPixel(x, y, sf::Color(128, 128, 128, 255));
            }
        }
        deathTexture.loadFromImage(deathImg);
    }
    
    void takeDamage(int damage) {
        health -= damage;
        if (health < 0) health = 0;
    }
    
    bool isAlive() const {
        return health > 0;
    }
};

// Класс предмета
class Item {
public:
    std::string name;
    int type = 0; // 0=potion, 1=sword, 2=shield, 3=key, 4=gem
    int value = 0;
    
    PixelSprite itemSprite;
    
    Item(const std::string& type) {
        itemSprite.loadPixelArt(type);
        itemSprite.setOrigin(16, 16);
    }
};

// Класс уровня подземелья
class DungeonLevel {
public:
    int width = 20;
    int height = 15;
    std::vector<std::string> tiles;
    sf::Texture floorTexture;
    sf::Texture wallTexture;
    sf::Texture doorTexture;
    sf::Texture stairsTexture;
    
    DungeonLevel() {
        // Загружаем текстуры тайлов
        loadTile("floor");
        loadTile("wall");
        loadTile("door");
        loadTile("stairs");
        
        // Генерируем уровень
        generateLevel();
    }
    
    void loadTile(const std::string& type) {
        sf::Image img = sf::Image::createFromData(32, 32);
        if (type == "floor") {
            for (int y = 0; y < 32; ++y) {
                for (int x = 0; x < 32; ++x) {
                    int color = 0xFF000000;
                    if ((x + y) % 4 == 0) color = 0xFF404040;
                    else color = 0xFF202020;
                    img.setPixel(x, y, sf::Color(color >> 24, (color >> 16) & 0xFF, 
                                                       (color >> 8) & 0xFF, color & 0xFF));
                }
            }
        } else if (type == "wall") {
            for (int y = 0; y < 32; ++y) {
                for (int x = 0; x < 32; ++x) {
                    int color = 0xFF000000;
                    if ((x + y) % 2 == 0) color = 0xFF808080;
                    else color = 0xFF606060;
                    img.setPixel(x, y, sf::Color(color >> 24, (color >> 16) & 0xFF, 
                                                       (color >> 8) & 0xFF, color & 0xFF));
                }
            }
        } else if (type == "door") {
            for (int y = 0; y < 32; ++y) {
                for (int x = 0; x < 32; ++x) {
                    int color = 0xFF000000;
                    if (y > 8 && y < 24 && x > 8 && x < 24) color = 0xFF8B4513;
                    else color = 0xFF654321;
                    img.setPixel(x, y, sf::Color(color >> 24, (color >> 16) & 0xFF, 
                                                       (color >> 8) & 0xFF, color & 0xFF));
                }
            }
        } else if (type == "stairs") {
            for (int y = 0; y < 32; ++y) {
                for (int x = 0; x < 32; ++x) {
                    int color = 0xFF000000;
                    if ((x + y) % 8 == 0) color = 0xFF000000;
                    else color = 0xFFFFA500;
                    img.setPixel(x, y, sf::Color(color >> 24, (color >> 16) & 0xFF, 
                                                       (color >> 8) & 0xFF, color & 0xFF));
                }
            }
        }
        
        texture.loadFromImage(img);
    }
    
    void generateLevel() {
        // Очищаем уровень
        tiles.clear();
        
        // Создаем границы из стен
        for (int y = 0; y < height; ++y) {
            std::string row;
            for (int x = 0; x < width; ++x) {
                if (x == 0 || x == width - 1 || y == 0 || y == height - 1) {
                    row += "wall";
                } else {
                    // Случайный пол или стена
                    if ((x + y) % 3 == 0) {
                        row += "floor";
                    } else {
                        row += "wall";
                    }
                }
            }
            tiles.push_back(row);
        }
        
        // Добавляем дверь и лестницу
        int doorX = width - 2;
        int doorY = height / 2;
        tiles[doorY][doorX] = "door";
        
        int stairsX = width - 2;
        int stairsY = height - 1;
        tiles[stairsY][stairsX] = "stairs";
    }
    
    sf::Sprite getTileSprite(int x, int y) const {
        if (x < 0 || x >= width || y < 0 || y >= height) {
            return sf::Sprite();
        }
        
        sf::Sprite sprite;
        std::string tileType = tiles[y][x];
        
        if (tileType == "floor") {
            sprite.setTexture(floorTexture);
        } else if (tileType == "wall") {
            sprite.setTexture(wallTexture);
        } else if (tileType == "door") {
            sprite.setTexture(doorTexture);
        } else if (tileType == "stairs") {
            sprite.setTexture(stairsTexture);
        }
        
        return sprite;
    }
    
private:
    sf::Texture texture;
};

// Основной игровой класс
class Game {
public:
    sf::RenderWindow window;
    sf::Font font;
    
    Hero hero;
    DungeonLevel currentLevel;
    std::vector<Enemy> enemies;
    std::vector<Item> items;
    
    int level = 1;
    bool gameOver = false;
    
    float lastTime = 0;
    sf::Clock clock;
    
    Game() {
        window.create(sf::VideoMode(800, 600), "RogueLike - Shattered Pixel Dungeon Style", 
                      sf::Style::Titlebar | sf::Style::Close);
        
        // Загружаем шрифт (используем стандартный)
        font.loadFromFile("arial");
        
        // Создаем первого врага
        enemies.emplace_back("spider");
    }
    
    void handleEvent() {
        sf::Event event;
        while (window.pollEvent(event)) {
            if (event.is<sf::Event::Closed>()) {
                window.close();
            }
            
            if (event.type == sf::Event::KeyPressed) {
                if (event.key.code == sf::Keyboard::Escape) {
                    window.close();
                } else if (event.key.code == sf::Keyboard::W && !gameOver) {
                    hero.move(0, -1);
                } else if (event.key.code == sf::Keyboard::S && !gameOver) {
                    hero.move(0, 1);
                } else if (event.key.code == sf::Keyboard::A && !gameOver) {
                    hero.move(-1, 0);
                } else if (event.key.code == sf::Keyboard::D && !gameOver) {
                    hero.move(1, 0);
                } else if (event.key.code == sf::Keyboard::Space && !gameOver) {
                    attackEnemy();
                } else if (event.key.code == sf::Keyboard::R && gameOver) {
                    restartGame();
                }
            }
        }
    }
    
    void update(float deltaTime) {
        // Обновление таймера
        float currentTime = clock.restart().asSeconds();
        float delta = currentTime - lastTime;
        lastTime = currentTime;
        
        // Здесь можно добавить анимации и другие обновления
    }
    
    void render() {
        sf::Texture floorTex, wallTex, doorTex, stairsTex;
        
        // Создаем текстуры тайлов для рендеринга
        createTileTextures(floorTex, wallTex, doorTex, stairsTex);
        
        // Рендерим уровень
        for (int y = 0; y < currentLevel.height; ++y) {
            for (int x = 0; x < currentLevel.width; ++x) {
                std::string tileType = currentLevel.tiles[y][x];
                
                sf::Sprite sprite;
                if (tileType == "floor") {
                    sprite.setTexture(floorTex);
                } else if (tileType == "wall") {
                    sprite.setTexture(wallTex);
                } else if (tileType == "door") {
                    sprite.setTexture(doorTex);
                } else if (tileType == "stairs") {
                    sprite.setTexture(stairsTex);
                }
                
                sprite.setPosition(x * 32, y * 32);
                window.draw(sprite);
            }
        }
        
        // Рендерим врагов
        for (const auto& enemy : enemies) {
            if (enemy.isAlive()) {
                enemy.enemySprite.setPosition((enemy.x * 32), (enemy.y * 32));
                window.draw(enemy.enemySprite.getSprite());
                
                // HP бар врага
                sf::RectangleShape hpBar(sf::Vector2f(30, 5));
                hpBar.setFillColor(sf::Color(100, 100, 100));
                window.draw(hpBar);
                
                sf::RectangleShape hpBarFill(sf::Vector2f(30 * (enemy.health / enemy.maxHealth), 5));
                hpBarFill.setFillColor(sf::Color(255, 0, 0));
                window.draw(hpBarFill);
            }
        }
        
        // Рендерим игрока
        hero.heroSprite.setPosition((hero.x * 32), (hero.y * 32));
        window.draw(hero.heroSprite.getSprite());
        
        // HP бар игрока
        sf::RectangleShape hpBar(sf::Vector2f(30, 5));
        hpBar.setFillColor(sf::Color(100, 100, 100));
        window.draw(hpBar);
        
        sf::RectangleShape hpBarFill(sf::Vector2f(30 * (hero.health / hero.maxHealth), 5));
        hpBarFill.setFillColor(sf::Color(0, 255, 0));
        window.draw(hpBarFill);
        
        // UI - информация о персонаже
        sf::Text uiText;
        std::string uiString = "HP: " + std::to_string(hero.health) + "/" + 
                               std::to_string(hero.maxHealth) + " | ATK: " + 
                               std::to_string(hero.attack) + " | LVL: " + 
                               std::to_string(hero.level);
        uiText.setFont(font);
        uiText.setString(uiString);
        uiText.setCharacterSize(14);
        uiText.setFillColor(sf::Color::White);
        uiText.setPosition(10, 10);
        window.draw(uiText);
        
        // UI - уровень подземелья
        std::string levelString = "Level: " + std::to_string(level);
        sf::Text levelText;
        levelText.setFont(font);
        levelText.setString(levelString);
        levelText.setCharacterSize(14);
        levelText.setFillColor(sf::Color::Yellow);
        levelText.setPosition(10, 35);
        window.draw(levelText);
        
        // UI - сообщение о победе/поражении
        if (gameOver) {
            std::string endString = gameOver ? "GAME OVER - Press R to Restart" : 
                                      "YOU WIN!";
            sf::Text endText;
            endText.setFont(font);
            endText.setString(endString);
            endText.setCharacterSize(24);
            endText.setFillColor(gameOver ? sf::Color::Red : sf::Color::Green);
            endText.setPosition(300, 275);
            window.draw(endText);
        }
    }
    
private:
    void createTileTextures(sf::Texture& floor, sf::Texture& wall, 
                           sf::Texture& door, sf::Texture& stairs) {
        // Создаем текстуры тайлов (упрощенно - используем один и тот же подход)
        sf::Image floorImg = sf::Image::createFromData(32, 32);
        for (int y = 0; y < 32; ++y) {
            for (int x = 0; x < 32; ++x) {
                int color = 0xFF000000;
                if ((x + y) % 4 == 0) color = 0xFF404040;
                else color = 0xFF202020;
                floorImg.setPixel(x, y, sf::Color(color >> 24, (color >> 16) & 0xFF, 
                                                   (color >> 8) & 0xFF, color & 0xFF));
            }
        }
        floor.loadFromImage(floorImg);
        
        sf::Image wallImg = sf::Image::createFromData(32, 32);
        for (int y = 0; y < 32; ++y) {
            for (int x = 0; x < 32; ++x) {
                int color = 0xFF000000;
                if ((x + y) % 2 == 0) color = 0xFF808080;
                else color = 0xFF606060;
                wallImg.setPixel(x, y, sf::Color(color >> 24, (color >> 16) & 0xFF, 
                                                   (color >> 8) & 0xFF, color & 0xFF));
            }
        }
        wall.loadFromImage(wallImg);
        
        sf::Image doorImg = sf::Image::createFromData(32, 32);
        for (int y = 0; y < 32; ++y) {
            for (int x = 0; x < 32; ++x) {
                int color = 0xFF000000;
                if (y > 8 && y < 24 && x > 8 && x < 24) color = 0xFF8B4513;
                else color = 0xFF654321;
                doorImg.setPixel(x, y, sf::Color(color >> 24, (color >> 16) & 0xFF, 
                                                   (color >> 8) & 0xFF, color & 0xFF));
            }
        }
        door.loadFromImage(doorImg);
        
        sf::Image stairsImg = sf::Image::createFromData(32, 32);
        for (int y = 0; y < 32; ++y) {
            for (int x = 0; x < 32; ++x) {
                int color = 0xFF000000;
                if ((x + y) % 8 == 0) color = 0xFF000000;
                else color = 0xFFFFA500;
                stairsImg.setPixel(x, y, sf::Color(color >> 24, (color >> 16) & 0xFF, 
                                                   (color >> 8) & 0xFF, color & 0xFF));
            }
        }
        stairs.loadFromImage(stairsImg);
    }
    
    void heroMove(int dx, int dy) {
        if (dx != 0 || dy != 0) {
            // Проверка на столкновение со стеной
            int newX = hero.x + dx;
            int newY = hero.y + dy;
            
            if (newX >= 0 && newX < currentLevel.width && 
                newY >= 0 && newY < currentLevel.height) {
                std::string tileType = currentLevel.tiles[newY][newX];
                if (tileType != "wall" && tileType != "door") {
                    hero.x = newX;
                    hero.y = newY;
                    
                    // Проверка на врагов
                    for (auto& enemy : enemies) {
                        if (!enemy.isAlive()) continue;
                        
                        int ex = enemy.x;
                        int ey = enemy.y;
                        
                        // Если враг рядом - атакуем
                        if (std::abs(hero.x - ex) + std::abs(hero.y - ey) == 1) {
                            attackEnemy();
                        }
                    }
                }
            }
        }
    }
    
    void attackEnemy() {
        // Ищем ближайшего живого врага
        for (auto& enemy : enemies) {
            if (!enemy.isAlive()) continue;
            
            int dist = std::abs(hero.x - enemy.x) + std::abs(hero.y - enemy.y);
            if (dist == 1) {
                // Атака
                enemy.takeDamage(hero.attack);
                
                // Шанс убить врага
                if (!enemy.isAlive()) {
                    int xpGained = enemy.xpValue;
                    hero.xp += xpGained;
                    
                    if (hero.xp >= hero.maxXp) {
                        levelUp();
                    }
                }
                
                // Удаляем мертвого врага
                enemies.erase(std::remove(enemies.begin(), enemies.end(), enemy), enemies.end());
            }
        }
    }
    
    void levelUp() {
        hero.level++;
        hero.maxXp *= 1.5;
        hero.maxHealth += 20;
        hero.health = hero.maxHealth;
        hero.attack += 3;
        hero.defense += 2;
        
        // Создаем нового врага для следующего уровня
        std::vector<std::string> enemyTypes = {"spider", "skeleton", "orc"};
        int randomIndex = level % enemyTypes.size();
        enemies.emplace_back(enemyTypes[randomIndex]);
    }
    
    void restartGame() {
        hero.health = 100;
        hero.maxHealth = 100;
        hero.attack = 10;
        hero.level = 1;
        hero.xp = 0;
        level = 1;
        gameOver = false;
        
        enemies.clear();
        items.clear();
        
        currentLevel.generateLevel();
    }
    
    void spawnEnemy() {
        // Спавним врага в случайном месте, не на игроке и не на стене
        int attempts = 0;
        while (attempts < 100) {
            int ex = std::rand() % currentLevel.width;
            int ey = std::rand() % currentLevel.height;
            
            if (ex > 0 && ex < currentLevel.width - 1 && 
                ey > 0 && ey < currentLevel.height - 1) {
                
                std::string tileType = currentLevel.tiles[ey][ex];
                if (tileType == "floor") {
                    // Проверка на расстояние от игрока
                    int dist = std::abs(hero.x - ex) + std::abs(hero.y - ey);
                    if (dist > 3) {
                        enemies.emplace_back("spider");
                        enemies.back().x = ex;
                        enemies.back().y = ey;
                        return;
                    }
                }
            }
            attempts++;
        }
    }
};

int main() {
    Game game;
    
    while (game.window.isOpen()) {
        float deltaTime = game.clock.restart().asSeconds();
        
        game.handleEvent();
        game.update(deltaTime);
        game.render();
    }
    
    return 0;
}
