cmake_minimum_required(VERSION 3.16)
project(BackupRestoreTool VERSION 1.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(Qt6 REQUIRED COMPONENTS Core Widgets Network)

qt6_standard_project_setup()

set(SOURCES
    src/main.cpp
    src/mainapp.cpp
    src/utils.cpp
    src/session.cpp
    src/settings.cpp
    src/workers.cpp
    src/docker_app.cpp
    src/image_manager.cpp
    src/login_dialog.cpp
    src/tab_manager.cpp
    src/ui_components.cpp
    src/game_manager.cpp
)

set(HEADERS
    include/mainapp.h
    include/utils.h
    include/session.h
    include/settings.h
    include/workers.h
    include/docker_app.h
    include/image_manager.h
    include/login_dialog.h
    include/tab_manager.h
    include/ui_components.h
    include/game_manager.h
)

qt6_add_executable(BackupRestoreTool ${SOURCES} ${HEADERS})

target_include_directories(BackupRestoreTool PRIVATE include)

target_link_libraries(BackupRestoreTool Qt6::Core Qt6::Widgets Qt6::Network)

# Copy JSON configuration files to build directory
configure_file(${CMAKE_CURRENT_SOURCE_DIR}/../active_users.json ${CMAKE_CURRENT_BINARY_DIR}/active_users.json COPYONLY)
configure_file(${CMAKE_CURRENT_SOURCE_DIR}/../custom_buttons.json ${CMAKE_CURRENT_BINARY_DIR}/custom_buttons.json COPYONLY)
configure_file(${CMAKE_CURRENT_SOURCE_DIR}/../game_destinations.json ${CMAKE_CURRENT_BINARY_DIR}/game_destinations.json COPYONLY)
configure_file(${CMAKE_CURRENT_SOURCE_DIR}/../games_data.json ${CMAKE_CURRENT_BINARY_DIR}/games_data.json COPYONLY)
configure_file(${CMAKE_CURRENT_SOURCE_DIR}/../recent_destinations.json ${CMAKE_CURRENT_BINARY_DIR}/recent_destinations.json COPYONLY)
configure_file(${CMAKE_CURRENT_SOURCE_DIR}/../tabs_config.json ${CMAKE_CURRENT_BINARY_DIR}/tabs_config.json COPYONLY)
configure_file(${CMAKE_CURRENT_SOURCE_DIR}/../tag_settings.json ${CMAKE_CURRENT_BINARY_DIR}/tag_settings.json COPYONLY)
configure_file(${CMAKE_CURRENT_SOURCE_DIR}/../time.txt ${CMAKE_CURRENT_BINARY_DIR}/time.txt COPYONLY)
configure_file(${CMAKE_CURRENT_SOURCE_DIR}/../user_session.json ${CMAKE_CURRENT_BINARY_DIR}/user_session.json COPYONLY)

# Copy images directory
file(COPY ${CMAKE_CURRENT_SOURCE_DIR}/../images DESTINATION ${CMAKE_CURRENT_BINARY_DIR})

# Set output directory
set_target_properties(BackupRestoreTool PROPERTIES
    RUNTIME_OUTPUT_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}
)

# Install target
install(TARGETS BackupRestoreTool DESTINATION bin)
install(FILES
    active_users.json
    custom_buttons.json
    game_destinations.json
    games_data.json
    recent_destinations.json
    tabs_config.json
    tag_settings.json
    time.txt
    user_session.json
    DESTINATION bin
)
install(DIRECTORY images DESTINATION bin)