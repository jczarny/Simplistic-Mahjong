import socket
import sys
import threading
import time
import math
from tkinter import *
import tkinter as tk
from PIL import Image, ImageTk

msg_length = 6

# Return index of next player's turn based on index of previous player's turn
def next_move(prev_turn):
    next_turn = (prev_turn + 1) % 4
    while not players_info[next_turn][0]:
        next_turn = (next_turn + 1) % 4
    return next_turn


# Check if selected (with checkboxes) tiles can make up to a set
def check_sets():
    global collected_sets
    global temp_collected_sets

    if len(collected_sets) > 4:
        label_my_info["text"] = "You can't get more than 4 sets by discarding!"
        return

    checkedTiles = []
    for i in range(len(checkboxes)):
        if checkboxes[i].get() == 1:
            checkedTiles.append(hand[i])

    # if player's turn state is "take_discarded":
    # 1) check if he selected two tiles
    # 2) check if these two tiles and last discarded tile make up to a set
    # 3) write to server that tile has been taken, remove used tiles from hand and discarded pile
    found_set = False
    if turn_state == "take_discarded":
        if len(checkedTiles) == 2:
            checkedTiles.append(last_discarded_tile)
            checkedTiles.sort()

            # Look for three identical tiles
            if checkedTiles[0] == checkedTiles[1] == checkedTiles[2]:
                found_set = True

            # Look for sequence of three tiles from the same suit
            if checkedTiles[0] not in ["DG", "DR", "DW", "WE", "WN", "WS", "WW"]:
                if checkedTiles[0][0] == checkedTiles[1][0] == checkedTiles[2][0]:
                    if int(checkedTiles[0][1]) + 2 == int(checkedTiles[1][1]) + 1 == int(checkedTiles[2][1]):
                        found_set = True
        else:
            label_my_info["text"] = "Select 2 tiles for a set!"

        if found_set:
            write_to_server("tkn yy")
            collected_sets.append(checkedTiles)
            label_my_sets["text"] = "Collected sets: " + str(len(collected_sets))
            # Remove tiles used in forming a set from hand
            checkedTiles.remove(last_discarded_tile)
            for tile in checkedTiles:
                hand.remove(tile)
            refresh_hand()

            for i in range(len(checkboxes)):
                checkboxes[i].set(0)
        else:
            label_my_info["text"] = "No set found."

    # if player's turn state is "picking_mahjong":
    # 1) check if he selected two or three tiles
    # 2) check if these tiles make up to a set or a pair
    # 3) continue until he collects this way 4 sets and a pair, then he wins
    elif turn_state == "picking_mahjong":
        checkedTiles.sort()
        if len(checkedTiles) == 3:
            # Look for three identical tiles
            if checkedTiles[0] == checkedTiles[1] == checkedTiles[2]:
                found_set = True

            # Look for sequence of three tiles from the same suit
            if checkedTiles[0] not in ["DG", "DR", "DW", "WE", "WN", "WS", "WW"]:
                if checkedTiles[0][0] == checkedTiles[1][0] == checkedTiles[2][0]:
                    if int(checkedTiles[0][1]) + 2 == int(checkedTiles[1][1]) + 1 == int(checkedTiles[2][1]):
                        found_set = True
        elif len(checkedTiles) == 2:
            if checkedTiles[0] == checkedTiles[1]:
                found_set = True
        else:
            label_my_info["text"] = "Select 3 tiles for a set or 2 tiles for a pair!"

        if found_set:
            temp_collected_sets.append(checkedTiles)
            label_my_sets["text"] = "Collected sets: " + str(len(temp_collected_sets) + len(collected_sets))
            for tile in checkedTiles:
                hand.remove(tile)
            refresh_hand()

            for i in range(len(checkboxes)):
                checkboxes[i].set(0)
        else:
            label_my_info["text"] = "No set found."

        if len(temp_collected_sets) + len(collected_sets) == 5:
            pair_count = 0
            for temp_set in temp_collected_sets:
                if len(temp_set) == 2:
                    pair_count += 1
            if pair_count == 1:
                # win condition fulfilled
                write_to_server("win $$")
            else:
                label_my_info["text"] = "You have to have precisely 1 pair and 4 sets!"


# Flip turn_state from "draw" to "picking_mahjong" or the other way around
def pick_mahjong():
    global temp_collected_sets

    if turn_state == "draw":
        config_turn_state("picking_mahjong")
    elif turn_state == "picking_mahjong":
        config_turn_state("draw")
        # If picking_mahjong didn't end with success, insert all sets back to hand
        for temp_set in temp_collected_sets:
            for tile in temp_set:
                hand.append(tile)
        temp_collected_sets.clear()
        label_my_sets["text"] = "Collected sets: " + str(len(collected_sets))
        refresh_hand()
    else:
        print("Mahjong button error!")


# Configure the current state of player's turn. Depending on state, different buttons may be clicked
def config_turn_state(new_turn_state):
    global turn_state

    if new_turn_state == "draw":
        turn_state = "draw"

        btnCheckSet["state"] = "disabled"
        btnPass["state"] = "disabled"
        btnMahjong["state"] = "active"
        btnMahjong["text"] = "MAHJONG"
        btnDiscard["state"] = "active"

        label_my_info["text"] = "Your draw turn!"
    elif new_turn_state == "take_discarded":
        turn_state = "take_discarded"

        btnCheckSet["state"] = "active"
        btnPass["state"] = "active"
        btnMahjong["state"] = "disabled"
        btnDiscard["state"] = "disabled"

        label_my_info["text"] = "Your discard turn!"
    elif new_turn_state == "wait":
        turn_state = "wait"

        btnCheckSet["state"] = "disabled"
        btnPass["state"] = "disabled"
        btnMahjong["state"] = "disabled"
        btnDiscard["state"] = "disabled"

        label_my_info["text"] = "Wait for your turn!"
    elif new_turn_state == "picking_mahjong":
        turn_state = "picking_mahjong"

        btnCheckSet["state"] = "active"
        btnPass["state"] = "disabled"
        btnMahjong["state"] = "active"
        btnMahjong["text"] = "CANCEL"
        btnDiscard["state"] = "disabled"

        label_my_info['text'] = "Select consecutively your sets!"
    else:
        print("Error: Unknown turn state.")


# Refresh player's images of tiles in hand. (only visual)
def refresh_hand():
    for i in range(14):
        try:
            image_source = "Tiles/" + hand[i] + ".png"
            image = ImageTk.PhotoImage(Image.open(image_source))
        except:
            image = ImageTk.PhotoImage(Image.open("Tiles/BLANK.png"))
        image_label = Label(tableMyTiles, bg="green")
        image_label.configure(image=image)
        image_label.image = image
        image_label.grid(row=0, column=i)


# Place 13 blank tiles to opponent's seat (only visual)
def insert_blank_tiles(player_seat):

    # If player's seat is 1, he's on the other side of board.
    if player_seat == 1:
        imgsrc = "Tiles/BLANK.png"
        img = Image.open(imgsrc)
        img = img.resize((60, 80), Image.Resampling.LANCZOS)
        img = ImageTk.PhotoImage(img)
        for column in range(13):
            png = Label(opponents_labels[player_seat][3], bg="green")
            png.configure(image=img)
            png.image = img
            png.grid(row=0, column=column)
    # If player's seat is other than 1, his seat is on the sides. Make his tiles smaller and rotate by 90 degrees.
    else:
        imgsrc = "Tiles/BLANK_ROTATED.png"
        img = Image.open(imgsrc)
        img = img.resize((32, 24), Image.Resampling.LANCZOS)
        img = ImageTk.PhotoImage(img)
        for row in range(13):
            png = Label(opponents_labels[player_seat][3], bg="green")
            png.configure(image=img)
            png.image = img
            png.grid(row=row, column=0)


# Refresh labels about other players: their turn states, id, and amount of collected sets (only visual)
def refresh_board():
    player_index = (your_seat_index + 1) % 4  # seat spot in server's perspective
    seat_index = 0                            # seat spot in player's perspective
    while in_game and player_index != your_seat_index:

        if players_info[player_index][0] is True:
            opponents_labels[seat_index][0]["text"] = "P" + str(seat_index)
            opponents_labels[seat_index][1]["text"] = "Sets: " + str(players_info[player_index][1])
            if player_index == player_discard_turn:
                opponents_labels[seat_index][2]["text"] = "DISCARD"
            elif player_index == player_draw_turn:
                opponents_labels[seat_index][2]["text"] = "DRAW"
            else:
                opponents_labels[seat_index][2]["text"] = "WAIT"

            insert_blank_tiles(seat_index)
            seat_index += 1

        player_index = (player_index + 1) % 4
    # Clear all labels in empty seats in case someone left the game
    for i in range(seat_index, 3):
        for widget in opponents_labels[i][3].winfo_children():
            widget.destroy()
        opponents_labels[i][0]["text"] = ""
        opponents_labels[i][1]["text"] = ""
        opponents_labels[i][2]["text"] = ""


# Add a tile to discarded pile.
def insert_to_discarded_pile(tile):
    global discarded_tiles_count
    global last_discarded_tile

    imgsrc = "Tiles/" + tile + ".png"

    img = Image.open(imgsrc)
    img = img.resize((45, 60), Image.Resampling.LANCZOS)
    img = ImageTk.PhotoImage(img)

    png = Label(table11, bg="green")
    png.configure(image=img)
    png.image = img
    png.grid(row=math.floor(discarded_tiles_count / 20), column=discarded_tiles_count % 20)

    last_discarded_tile = tile
    discarded_tiles_count += 1


# Remove selected tile from player's hand
def discard_tile():
    checkboxIndex = -1
    for i in range(len(checkboxes)):
        if checkboxes[i].get() != 0 and checkboxIndex == -1:
            checkboxIndex = i
        elif checkboxes[i].get() != 0 and checkboxIndex != -1:
            label_my_info["text"] = "You can discard only one tile at a time!"
            return "error"

    if checkboxIndex == -1:
        label_my_info["text"] = "Select a tile to discard!"
        return "error"

    try:
        tile = hand.pop(checkboxIndex)
        for i in range(len(checkboxes)):
            checkboxes[i].set(0)
        refresh_hand()
        return tile
    except IndexError:
        label_my_info["text"] = "Error: couldn't pop a tile"


# Connect to a server using ip, port. If success, exit connection window.
def connect_to_server(ip, port, conn_window):
    global s
    global connected
    try:
        port = int(port)
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((ip, port))
        connected = True
        conn_window.destroy()
    except (ConnectionRefusedError, ValueError, TimeoutError):
        lInfo = Label(conn_window, text='Wrong IP/Port', font=('Helvetica', 10, 'bold'), fg='#ff0000')
        lInfo.place(relx=0.65, rely=0.75)


# Disconnect from server, exits game screen
def disconnect():
    global connected
    try:
        connected = False
        s.close()
        root.destroy()
    except:
        print("You can't disconnect if you're not connected!")


# Read complete data from server
def read_data():
    global msg_length

    data = ""
    while len(data) != msg_length:
        data_part = s.recv(msg_length).decode('utf-8', 'strict')

        if len(data_part) == 0:
            raise ValueError
        data += data_part

    try:
        cmd, val = data.split()
        return cmd, val
    except ValueError:
        print("Invalid input: " + data)
        raise ValueError


# Send complete data from server
def send_data(msg):
    sent_n = 0
    n = 0
    while sent_n != msg_length:
        n = s.send(msg.encode())
        if n == 0 or n == -1:
            print("Sending Error!")
            return 0
        sent_n += n
    return 1


# Client in loop reads data from server and responds accordingly:
# "bgn $$" - signal of beginning the game
# "exi pn" - signal that player n left the game
# "err nn" - signal that an error occurred
# "den $$" - signal of denied access to server (because server is full)
# "own $$" - signal that client became owner of the room
# "set $$" - signal of starting the sequence of messages preparing for the game
# "acc $$" - signal of another player joining room
# "bgn $$" - signal of starting the game, and starting the sequence of receiving initial tiles to hand
# "nxt $$" - signal of starting next turn of the game
# "drw nn" - signal of drawing tile by player, where nn is a string representing a tile
# "dsc nn" - signal of discarding a tile, where nn is a string representing a tile
# "tkn yy/nn" - signals whether player took discarded tile or not
# "win pn" - signal of player reaching win condition, where n is winner's seat
# "tie $$" - signal that all tiles were used and no winner was found
# "chk $$" - signal from server to know we're active
def read_from_server():
    global hand
    global your_seat_index
    global players_info
    global room_owner
    global connected
    global in_game
    global player_draw_turn
    global player_discard_turn
    global players_count

    while connected:
        try:
            cmd, val = read_data()
        except:
            if connected:
                config_turn_state("wait")
                print("Connection lost!")
                label_my_info["text"] = "Connection with server lost! Try connecting again."
                connected = False
            break

        # Heartbeat from server
        if cmd == "chk":
            continue
        # Opponent exits room
        elif cmd == "exi":
            val = int(val[-1])
            players_count -= 1
            # If game has not yet started: if room owner leaves, disconnect all players.
            # If other player leaves, refresh room owner's label about current player in lobby
            if not in_game:
                if val-1 == 0:
                    label_my_info["text"] = "Room owner has left. Look for another room."
                    connected = False
                elif room_owner:
                    label_my_info["text"] = "Currently players: " + str(players_count)
            # If game has already started, make changes in players_info
            elif in_game:
                players_info[val - 1] = [False, 0]
                refresh_board()
                if players_count == 1:
                    config_turn_state("wait")
                    label_my_info["text"] = "Game has ended. You're the only person in the room."
                    connected = False
        # Errors sent by server during connection
        elif cmd == "err":
            # Error sent when room owner tries to start the game when he's alone in the room
            if val == "01":
                label_my_info["text"] = "You're the only person in room."
        # When in lobby
        elif not in_game:
            # Denies access to player
            if cmd == "den":
                label_my_info["text"] = "Server is currently full. Try again later."
            # Notify player that he's room owner
            elif cmd == "own":
                room_owner = True
            # Begin the sequence of messages about setting up the game
            elif cmd == "set":
                players_count = 0
                if room_owner:
                    btnStart.pack_forget()
                # Receive messages "set pn" about players until "ure pn" which inform player which seat is his.
                while True:
                    try:
                        cmd, val = read_data()
                    except:
                        if connected:
                            config_turn_state("wait")
                            print("Connection lost!")
                            label_my_info["text"] = "Connection with server lost! Try connecting again."
                            connected = False
                        break
                    val = int(val[-1])
                    if cmd == "set":
                        players_info[val-1][0] = True
                        players_count += 1
                    elif cmd == "ure":
                        your_seat_index = val - 1
                        break
                in_game = True
            # Notify that new player joined the room
            elif cmd == "acc":
                players_count += 1
                label_my_info["text"] = "Currently players: " + str(players_count)

        # When in game
        elif in_game:
            # Begin the sequence of messages about tiles in hand
            if cmd == "bgn":
                while len(hand) < 13:
                    try:
                        cmd, tile = read_data()
                    except:
                        if connected:
                            config_turn_state("wait")
                            print("Connection lost!")
                            label_my_info["text"] = "Connection with server lost! Try connecting again."
                            connected = False
                        break
                    if cmd == "rcv":
                        hand.append(tile)
                    else:
                        print("Unknown error when receiving initial hand!")

                config_turn_state("wait")

                hand.sort()
                refresh_hand()
                refresh_board()

            # Next turn
            elif cmd == "nxt":
                player_draw_turn = next_move(player_draw_turn)
                player_discard_turn = -1
                refresh_board()
            # Draw tile
            elif cmd == "drw":
                config_turn_state("draw")
                tile = val
                hand.append(tile)

                hand.sort()
                refresh_hand()
            # Discarded tile
            elif cmd == "dsc":
                tile = val
                insert_to_discarded_pile(tile)
                player_discard_turn = next_move(player_draw_turn)
                if player_discard_turn == your_seat_index:
                    config_turn_state("take_discarded")
                refresh_board()
            # Notification if other player took discarded tile or not
            elif cmd == "tkn":
                if val == "nn":
                    player_discard_turn = next_move(player_discard_turn)
                    if player_draw_turn == player_discard_turn:
                        continue
                    elif player_discard_turn == your_seat_index:
                        config_turn_state("take_discarded")
                elif val == "yy":
                    players_info[player_discard_turn][1] += 1
                    # delete last tile from discarded pile
                    for tile in table11.grid_slaves():
                        if int(tile.grid_info()["row"]) == math.floor((discarded_tiles_count - 1) / 20):
                            if int(tile.grid_info()["column"]) == (discarded_tiles_count - 1) % 20:
                                tile.grid_forget()
                refresh_board()

            # Notification that someone won the game
            elif cmd == "win":
                val = int(val[-1]) - 1
                in_game = False
                connected = False
                label_my_info["text"] = "Game has ended."
                if val == your_seat_index:
                    show_end_screen("Congratulations!\n You Won!", font_color="green")
                else:
                    show_end_screen("Player " + str(val) + " won!", font_color="red")

            # Notification that game ended with draw
            elif cmd == "tie":
                in_game = False
                connected = False
                label_my_info["text"] = "Game has ended."
                show_end_screen("A Tie!\n", font_color="#8B8000")
        else:
            print("Unknown command: " + cmd + " " + val)

# Client is able to write under certain circumstances few messages:
# "bgn $$" - which signals beginning of the game
# "dsc nn" - where nn is text representing ??, which signals which tile has player discarded
# "tkn yy/nn" - which signals whether player took discarded tile or not
# "win $$" - which signals that player met win conditions
def write_to_server(msg):
    global player_draw_turn
    global player_discard_turn
    global your_seat_index

    try:
        cmd, val = msg.split()
    except ValueError:
        print("Badly constructed message!")
        return

    # If room owner is not yet in game, he can only send signal to start the game
    if room_owner and not in_game:
        if cmd == "bgn":
            if players_count > 1:
                result = send_data(msg)
                if result == 0:
                    config_turn_state("wait")
                    label_my_info["text"] = "Connection with server lost! Try connecting again."

            else:
                label_my_info["text"] = "You're the only person in room."
    elif in_game:
        # If player's turn is draw, he can only signal which tile he discarded or signal that he win
        if player_draw_turn == your_seat_index:
            if cmd == "dsc":
                tile = discard_tile()
                if tile != "error":
                    msg = cmd + " " + tile
                    result = send_data(msg)
                    if result == 0:
                        config_turn_state("wait")
                        label_my_info["text"] = "Connection with server lost! Try connecting again."
                    else:
                        config_turn_state("wait")
                else:
                    return -1

            elif cmd == "win":
                result = send_data(msg)
                if result == 0:
                    config_turn_state("wait")
                    label_my_info["text"] = "Connection with server lost! Try connecting again."
        # If player's turn is discard, he can only send answer if he took and used last discarded tile
        elif player_discard_turn == your_seat_index:
            if cmd == "tkn":
                result = send_data(msg)
                config_turn_state("wait")
                if result == 0:
                    label_my_info["text"] = "Connection with server lost! Try connecting again."

        else:
            print("Wait for your turn!")
    else:
        print("Error: You can't send anything to server right now.")


# Show screen in which you connect to server
def show_connection_screen(connectionWindow):
    connectionWindow.title("Join Room")
    connectionWindow.geometry("300x135")
    connectionWindow.resizable(False, False)

    lIP = Label(connectionWindow, text="IP address", font=('Helvetica', 12, 'bold'))
    lIP.pack()
    eIP = Entry(connectionWindow, text='IP address', font=('Helvetica', 12, 'bold'))
    eIP.insert(0, '192.168.0.5')
    eIP.pack()

    lPort = Label(connectionWindow, text='Port', font=('Helvetica', 12, 'bold'))
    lPort.pack()
    ePort = Entry(connectionWindow, text='Port', font=('Helvetica', 12, 'bold'))
    ePort.insert(0, '1234')
    ePort.pack()

    btnEnter = Button(connectionWindow, text="Connect!", font=('Helvetica', 12, 'bold'), command=lambda: connect_to_server(eIP.get(), ePort.get(), connectionWindow))
    btnEnter.pack()


# If player closes ending screen, close also game screen
def delete_end_screen(endWindow):
    endWindow.destroy()
    root.destroy()


# Show screen in which you're informed who won the game
def show_end_screen(message, font_color):
    endWindow = Toplevel(root)
    endWindow.geometry("200x75")
    endWindow.protocol("WM_DELETE_WINDOW", root.destroy)
    labelGameResult = Label(endWindow, text=message, font=('Helvetica', 16, 'bold'), fg=font_color)
    labelGameResult.pack()

    labelEndGameButton = Button(endWindow, text="Exit", command=lambda: delete_end_screen(endWindow))
    labelEndGameButton.pack()


# Show tutorial screen
def show_tutorial_screen():
    tutWindow = Toplevel(root)
    FrameInstruction1 = tk.Frame(tutWindow)
    FrameInstruction1.pack()

    Label(FrameInstruction1, text="Aby wygrać grę, gracz musi skompletować mahjonga"
                                  ", to znaczy skompletować cztery zestawy trzech płytek oraz parę\n").pack()

    FrameGraphics1 = tk.Frame(tutWindow)
    FrameGraphics1.pack()

    rowcount = 0
    for tile_type in ["B", "D", "S"]:
        for i in range(1, 10):
            img_source = "Tiles/" + tile_type + str(i) + ".png"
            image = ImageTk.PhotoImage(Image.open(img_source))
            label_image = Label(FrameGraphics1)
            label_image.configure(image=image)
            label_image.image = image
            label_image.grid(row=rowcount, column=i)
        rowcount += 1

    FrameInstruction2 = tk.Frame(tutWindow)
    FrameInstruction2.pack()

    Label(FrameInstruction2, text="Gra zawiera dwa typy zestawów płytek:\n Pierwszy to trzy identyczne płytki").pack()

    FrameGraphics2 = tk.Frame(tutWindow)
    FrameGraphics2.pack()

    for i in range(3):
        img_source = "Tiles/B3.png"
        image = ImageTk.PhotoImage(Image.open(img_source))
        label_image = Label(FrameGraphics2)
        label_image.configure(image=image)
        label_image.image = image
        label_image.grid(row=0, column=i)

    Label(FrameGraphics2, text="lub").grid(row=0, column=3)

    for i in range(4, 7):
        img_source = "Tiles/S7.png"
        image = ImageTk.PhotoImage(Image.open(img_source))
        label_image = Label(FrameGraphics2)
        label_image.configure(image=image)
        label_image.image = image
        label_image.grid(row=0, column=i)

    FrameInstruction3 = tk.Frame(tutWindow)
    FrameInstruction3.pack()

    Label(FrameInstruction3, text="Drugim typem jest sekwencja płytek tego samego typu").pack()

    FrameGraphics3 = tk.Frame(tutWindow)
    FrameGraphics3.pack()

    counter = 0
    for i in range(3, 6):
        img_source = "Tiles/D" + str(i) + ".png"
        image = ImageTk.PhotoImage(Image.open(img_source))
        label_image = Label(FrameGraphics3)
        label_image.configure(image=image)
        label_image.image = image
        label_image.grid(row=0, column=counter)
        counter += 1

    Label(FrameGraphics3, text="lub").grid(row=0, column=3)
    counter += 1

    for i in range(7, 10):
        img_source = "Tiles/S" + str(i) + ".png"
        image = ImageTk.PhotoImage(Image.open(img_source))
        label_image = Label(FrameGraphics3)
        label_image.configure(image=image)
        label_image.image = image
        label_image.grid(row=0, column=counter)
        counter += 1

    FrameInstruction4 = tk.Frame(tutWindow)
    FrameInstruction4.pack()
    Label(FrameInstruction4, text="Uproszczona wersja gry mahjong dla początkujących.\n"
                                  "Gra jest podzielona na dwa typy tur: Draw i Discard\n"
                                  "W turze Draw otrzymujesz jedną płytkę oraz wybierasz jedną płytkę którą chcesz odrzucić\n"
                                  "W turze Discard spoglądasz na ostatnią odrzuconą płytkę leżącą na stole "
                                  "i możesz ją wykorzystać do skompletowania zestawu (Wybierasz 2 swoje płytki i klikasz \"Check Set\"\n"
                                  "W turze Draw możesz również spróbować skończyć mahjonga, polega to na kolejnym wybieraniu "
                                  "zestawów (3 płytek) oraz jednej pary. W momencie uzbieraniu 4 zestawów oraz jednej pary wygrywasz.\n"
                                  "Powodzenia!").pack()


# Client loop which may be exited only by closing connection window
while True:
    s = socket.socket()
    hand = []
    discarded_tiles_count = 0
    last_discarded_tile = ""
    collected_sets = []  # sets collected permanently in discard turn
    temp_collected_sets = []  # sets collected temporarily while looking for mahjong
    players_info = [[False, 0], [False, 0], [False, 0], [False, 0]]  # info if seat is taken(True/False) and if yes - how many sets has he collected.
    opponents_labels = [[], [], []]  # for each opponent: label No. Player, label Collected sets, label turn state, label for blank tiles images.

    players_count = 1
    player_draw_turn = 0
    player_discard_turn = -1
    your_seat_index = -1

    in_game = False
    room_owner = False
    connected = False
    turn_state = "wait"

    join_window = Tk()
    show_connection_screen(join_window)
    join_window.mainloop()

    if not connected:
        sys.exit()

    # Create a thread waiting for data from server
    tRead = threading.Thread(target=read_from_server)
    tRead.daemon = True
    tRead.start()

    #############################
    # DRAWING GAME WINDOW SECTION
    root = Tk()
    root.geometry("1366x768")
    root.resizable(False, False)

    # Table is divided into 9 frames
    # --------------------------------
    # | table00 || table01 || table02 |
    # | ----------------------------- |
    # | table10 || table11 || table12 |
    # |------------------------------ |
    # | table20 || table21 || table22 |
    # |_______________________________|
    # table01, table10, table12, table21 holds players tiles
    # table11 holds all discarded tiles during the game

    table00 = tk.Frame(root, bg="green")
    table00.place(relx=0.00, rely=0.00, relwidth=0.05, relheight=0.8)
    table01 = tk.Frame(root, bg="green")
    table01.place(relx=0.05, rely=0.0, relwidth=0.9, relheight=0.8)
    table02 = tk.Frame(root, bg="green")
    table02.place(relx=0.95, rely=0.0, relwidth=0.05, relheight=0.8)

    table10 = tk.Frame(root, bg="green")
    table10.place(relx=0.00, rely=0.1, relwidth=0.05, relheight=0.7)
    table11 = tk.Frame(root, bg="green")
    table11.place(relx=0.05, rely=0.1, relwidth=0.9, relheight=0.7)
    table12 = tk.Frame(root, bg="green")
    table12.place(relx=0.95, rely=0.1, relwidth=0.05, relheight=0.7)

    table20 = tk.Frame(root, bg="green")
    table20.place(relx=0.00, rely=0.8, relwidth=0.05, relheight=0.2)
    table21 = tk.Frame(root, bg="green")
    table21.place(relx=0.05, rely=0.8, relwidth=0.9, relheight=0.2)
    table22 = tk.Frame(root, bg="green")
    table22.place(relx=0.95, rely=0.8, relwidth=0.05, relheight=0.2)

    # Creating labels for informing player about the current state of the game
    opponent_label = tk.Label(table12, text="", bg="green", fg="red", font="Helvetica 10 bold")
    opponent_label.place(relx=0, rely=0)
    opponents_labels[0].append(opponent_label)
    opponent_label = tk.Label(table12, text="", bg="green", fg="red", font="Helvetica 10 bold")
    opponent_label.place(relx=0, rely=0.03)
    opponents_labels[0].append(opponent_label)
    opponent_label = tk.Label(table12, text="", bg="green", fg="red", font="Helvetica 10 bold")
    opponent_label.place(relx=0, rely=0.06)
    opponents_labels[0].append(opponent_label)

    opponent_label = tk.Label(table01, text="", bg="green", fg="red", font="Helvetica 10 bold")
    opponent_label.place(relx=0.0, rely=0.0)
    opponents_labels[1].append(opponent_label)
    opponent_label = tk.Label(table01, text="", bg="green", fg="red", font="Helvetica 10 bold")
    opponent_label.place(relx=0.0, rely=0.03)
    opponents_labels[1].append(opponent_label)
    opponent_label = tk.Label(table01, text="", bg="green", fg="red", font="Helvetica 10 bold")
    opponent_label.place(relx=0.0, rely=0.06)
    opponents_labels[1].append(opponent_label)

    opponent_label = tk.Label(table10, text="", bg="green", fg="red", font="Helvetica 10 bold")
    opponent_label.place(relx=0, rely=0)
    opponents_labels[2].append(opponent_label)
    opponent_label = tk.Label(table10, text="", bg="green", fg="red", font="Helvetica 10 bold")
    opponent_label.place(relx=0, rely=0.03)
    opponents_labels[2].append(opponent_label)
    opponent_label = tk.Label(table10, text="", bg="green", fg="red", font="Helvetica 10 bold")
    opponent_label.place(relx=0, rely=0.06)
    opponents_labels[2].append(opponent_label)

    # Creating frames for opponents blank tiles
    tiles_frame = tk.Frame(table12, bg="green")
    tiles_frame.place(relx=0, rely=0.2)
    opponents_labels[0].append(tiles_frame)

    tiles_frame = tk.Frame(table01, bg="green")
    tiles_frame.place(relx=0.15, rely=0.0)
    opponents_labels[1].append(tiles_frame)

    tiles_frame = tk.Frame(table10, bg="green")
    tiles_frame.place(relx=0, rely=0.2)
    opponents_labels[2].append(tiles_frame)

    # Drawing client's tiles
    tableMyTiles = tk.Frame(table21, bg="green")
    tableMyTiles.place(relx=0, rely=0, relwidth=0.9, relheight=1)

    checkboxes = []

    img = ImageTk.PhotoImage(Image.open("Tiles/BLANK.png"))
    for i in range(14):
        png = Label(tableMyTiles, bg="green")
        png.configure(image=img)
        png.image = img
        png.grid(row=0, column=i)

        checkboxes.append(tk.IntVar())
        c = Checkbutton(tableMyTiles, bg="green", width=3, height=3, variable=checkboxes[i])
        c.grid(row=1, column=i)

    # Drawing client's options and information
    frame_options = tk.Frame(table21, bg="green")
    frame_options.place(relx=0.9, rely=0, relwidth=0.1, relheight=1)

    label_my_info = tk.Label(table11, text="Waiting for game to start", bg="green", fg="red", font='Helvetica 18 bold')
    label_my_info.place(relx=0.0, rely=0.945)

    label_my_sets = tk.Label(table11, text="Collected sets: " + str(len(collected_sets)), bg="green", fg="red", font='Helvetica 18 bold')
    label_my_sets.place(relx=0.84, rely=0.945)

    btnCheckSet = Button(frame_options, text="CHECK SET", width=17, command=lambda: check_sets())
    btnCheckSet.grid(row=0, column=14)
    btnPass = Button(frame_options, text="PASS", width=17, command=lambda: write_to_server("tkn nn"))
    btnPass.grid(row=1, column=14)
    btnMahjong = Button(frame_options, text="MAHJONG", width=17, command=lambda: pick_mahjong())
    btnMahjong.grid(row=2, column=14)
    btnDiscard = Button(frame_options, text="DISCARD", width=17, command=lambda: write_to_server("dsc $$"))
    btnDiscard.grid(row=3, column=14)
    btnTutorial = Button(frame_options, text="TUTORIAL", width=17, command=lambda: show_tutorial_screen())
    btnTutorial.grid(row=4, column=14)

    btnCheckSet["state"] = "disabled"
    btnPass["state"] = "disabled"
    btnMahjong["state"] = "disabled"
    btnDiscard["state"] = "disabled"

    # Show special button for room_owner to decide when to start the game
    if room_owner:
        btnStart = Button(table02, text="Start game!", width=9, height=5, command=lambda: write_to_server("bgn $$"))
        btnStart.pack()

        label_my_info["text"] = "Currently players: 1"

    root.protocol("WM_DELETE_WINDOW", disconnect)
    root.mainloop()
