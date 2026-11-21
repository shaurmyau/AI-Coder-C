cmake_minimum_required(VERSION 3.10)
project(DungeonCrawler LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

add_executable(game main.cpp game.cpp)

# Свойства для Windows
set_target_properties(game PROPERTIES
    LINK_FLAGS "/SUBSYSTEM:WINDOWS"
)
