cmake_minimum_required(VERSION 3.10)
project(DungeonCrawler CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Добавляем исполняемый файл
add_executable(${PROJECT_NAME} 
    game/main.cpp
    game/game.cpp
)
