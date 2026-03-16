from ursina import *
from ursina.prefabs.first_person_controller import FirstPersonController
from ursina.prefabs.input_field import InputField
import socket
import threading
import json
import time

app = Ursina()

# --- НАСТРОЙКИ ОКНА ---
window.title = ''
window.borderless = True
window.fullscreen = True
window.fps_counter.enabled = False
window.exit_button.visible = False

# --- ВЫБОР РЕЖИМА (меню в начале) ---
mode_text = Text('Ты будешь сервером или клиентом?', position=(0, 0.3), scale=1.5, origin=(0,0))
server_button = Button('🖥️ Я СЕРВЕР', color=color.blue, scale=(0.3, 0.1), position=(0, 0.1))
client_button = Button('💻 Я КЛИЕНТ', color=color.green, scale=(0.3, 0.1), position=(0, -0.1))

# --- ПЕРЕМЕННЫЕ ---
is_server = None
SERVER_IP = '0.0.0.0'
PORT = 5555
clients = []
players = {}
player_color = None

# --- ВВОД IP (для клиента) - создаём простые кнопки вместо InputField ---
ip_text = Text('Введи IP сервера:', position=(0, -0.2), scale=1, origin=(0,0))
ip_display = Text('192.168.1.', position=(0, -0.3), scale=1.5, color=color.yellow, origin=(0,0))
ip_input_active = False
ip_value = '192.168.1.'

connect_button = Button('🔌 ПОДКЛЮЧИТЬСЯ', color=color.orange, scale=(0.3, 0.1), position=(0, -0.4))

# Инструкция по вводу


# Скрываем поля ввода IP (покажем только для клиента)
ip_text.visible = False
ip_display.visible = False
connect_button.visible = False


# --- ФУНКЦИИ ВЫБОРА РЕЖИМА ---
def set_server():
    global is_server
    is_server = True
    # Прячем меню выбора
    destroy(mode_text)
    destroy(server_button)
    destroy(client_button)
    # Показываем меню выбора цвета
    show_color_menu()

def set_client():
    global is_server
    is_server = False
    # Прячем меню выбора
    destroy(mode_text)
    destroy(server_button)
    destroy(client_button)
    # Показываем поля для ввода IP
    ip_text.visible = True
    ip_display.visible = True
    connect_button.visible = True


server_button.on_click = set_server
client_button.on_click = set_client

# --- ФУНКЦИЯ ВВОДА IP С КЛАВИАТУРЫ ---
def input(key):
    global ip_value, ip_input_active
    
    if ip_text.visible and key == 'enter':
        ip_input_active = not ip_input_active
        if ip_input_active:
            ip_display.color = color.lime
        else:
            ip_display.color = color.yellow
    
    if ip_input_active and len(key) == 1 and key.isdigit() or key == '.':
        ip_value += key
        ip_display.text = ip_value
    
    if ip_input_active and key == 'backspace':
        ip_value = ip_value[:-1]
        ip_display.text = ip_value

# --- МЕНЮ ВЫБОРА ЦВЕТА ---
color_text = Text('Выбери цвет:', position=(0, 0.2), scale=2, origin=(0,0))
red_button = Button('🔴 КРАСНЫЙ', color=color.red, scale=(0.3, 0.1), position=(0, 0))
blue_button = Button('🔵 СИНИЙ', color=color.blue, scale=(0.3, 0.1), position=(0, -0.15))

# Скрываем меню цвета (покажем после выбора роли)
color_text.visible = False
red_button.visible = False
blue_button.visible = False

def show_color_menu():
    color_text.visible = True
    red_button.visible = True
    blue_button.visible = True

def set_red():
    global player_color
    player_color = 'red'
    destroy(color_text)
    destroy(red_button)
    destroy(blue_button)
    start_game()

def set_blue():
    global player_color
    player_color = 'blue'
    destroy(color_text)
    destroy(red_button)
    destroy(blue_button)
    start_game()

red_button.on_click = set_red
blue_button.on_click = set_blue

# --- ФУНКЦИЯ ПОДКЛЮЧЕНИЯ КЛИЕНТА ---
def connect_to_server():
    global SERVER_IP
    SERVER_IP = ip_value
    print(f"🔌 Подключаемся к серверу: {SERVER_IP}")
    
    # Прячем поля ввода
    ip_text.visible = False
    ip_display.visible = False
    connect_button.visible = False

    
    # Показываем меню цвета
    show_color_menu()

connect_button.on_click = connect_to_server
# --- ФУНКЦИЯ ЗАПУСКА ИГРЫ ---
def start_game():
    global player
    
    # --- ОГРОМНАЯ ПЛОЩАДКА ---
    ground = Entity(
        model='plane',
        texture='grass',
        scale=(1000, 1, 1000),
        color=color.rgb(100, 200, 100),
        collider='mesh'
    )

    # --- НЕБО ---
    sky = Sky()
    sky.color = color.rgb(100, 150, 255)

    # --- ГРАНИЦЫ ---
    size = 500
    Entity(model='cube', color=color.clear, scale=(1, 20, 1000), position=(-size, 10, 0), collider='box', visible=False)
    Entity(model='cube', color=color.clear, scale=(1, 20, 1000), position=(size, 10, 0), collider='box', visible=False)
    Entity(model='cube', color=color.clear, scale=(1000, 20, 1), position=(0, 10, size), collider='box', visible=False)
    Entity(model='cube', color=color.clear, scale=(1000, 20, 1), position=(0, 10, -size), collider='box', visible=False)

    # --- ИГРОК (СВОЙ) ---
    player = FirstPersonController()
    player.base_speed = 20
    player.jump_height = 10
    player.speed = player.base_speed
    player.gravity = 3.0
    player.scale = 5
    player.position = (0, 2, 0)
    player.cursor.visible = False

    # --- ТЕЛО ИГРОКА (сфера выбранного цвета) ---
    player_body = Entity(
        model='sphere',
        color=color.red if player_color == 'red' else color.blue,
        scale=(1, 1.5, 1),
        position=(0, 1, 0),
        parent=player
    )

    # --- ЗАПУСК СЕРВЕРА ИЛИ ПОДКЛЮЧЕНИЕ КЛИЕНТА ---
    if is_server:
        print("🖥️ Запускаем сервер...")
        threading.Thread(target=server_thread, daemon=True).start()
    else:
        print("💻 Запускаем клиент...")
        threading.Thread(target=client_thread, daemon=True).start()

# --- СЕРВЕР ---
def server_thread():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(('0.0.0.0', PORT))
    server.listen(5)
    print(f"🖥️ Сервер запущен на порту {PORT}")

    while True:
        client, address = server.accept()
        print(f"✅ Подключился игрок: {address}")
        clients.append(client)
        threading.Thread(target=handle_client, args=(client, address), daemon=True).start()

# --- КЛИЕНТ ---
def client_thread():
    try:
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect((SERVER_IP, PORT))
        clients.append(client)
        print(f"✅ Подключились к серверу {SERVER_IP}")
        
        while True:
            data = client.recv(1024).decode()
            if not data:
                break
            # Обработка данных от сервера
            # (тут нужно добавить логику)
            
    except Exception as e:
        print(f"❌ Ошибка подключения: {e}")

def handle_client(client, address):
    addr_str = f"{address[0]}:{address[1]}"
    
    player_sphere = Entity(
        model='sphere',
        color=color.red,  # временно
        scale=5,
        position=(0, 2, 0)
    )
    players[addr_str] = (player_sphere, 'red')

    try:
        while True:
            data = client.recv(1024).decode()
            if not data:
                break
            pos_data = json.loads(data)
            player_sphere.position = (pos_data['x'], 2, pos_data['z'])
            broadcast(pos_data, addr_str)
    except:
        pass
    finally:
        clients.remove(client)
        if addr_str in players:
            destroy(players[addr_str][0])
            del players[addr_str]
        client.close()

def broadcast(data, sender_addr):
    for client in clients[:]:
        try:
            client.send(json.dumps({'type': 'update', 'addr': sender_addr, 'x': data['x'], 'z': data['z']}).encode())
        except:
            clients.remove(client)

def update():
    if 'player' in globals():
        pos_data = {'x': player.x, 'z': player.z}
        for client in clients[:]:
            try:
                client.send(json.dumps(pos_data).encode())
            except:
                clients.remove(client)
        
        if held_keys['shift']:
            player.speed = player.base_speed * 3
        else:
            player.speed = player.base_speed

app.run()