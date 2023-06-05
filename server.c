#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <netdb.h>
#include <stdio.h>
#include <unistd.h>
#include <stdlib.h>
#include <string.h>
#include <signal.h>
#include <threads.h>
#include <pthread.h>
#include <errno.h>

#define maxGames 25
#define sumTiles 136
#define msgLength 6

int tables [maxGames][5];   // [status, player1, player2, player3, player4]
                            // status: 0 - waiting for players, 1 - in game
                            // if player is 0: spot is empty, if its above 0 its taken

char tiles [sumTiles][3];   // empty list to be filled with mahjong tiles

void writeToRoom(int roomVal, char msg[msgLength]); // declaration of writeToRoom function

struct cln {
    int cfd;
    struct sockaddr_in caddr;
};

// read data from client cfd and put it in buf[]
// return 1 if success, 0 if error occured
int readData(int cfd, char buf[]){
    int total_n = 0;
    int n = 0;
    strcpy(buf, "");

    while(total_n != msgLength){
        n = read(cfd, buf + total_n, msgLength-total_n);
        if(n == 0 || n==-1){
            return 0;
        }
        total_n += n;
    }
    return 1;
}

// send data buf[] to client cfd
// return 1 if success, 0 if error occured
int sendData(int cfd, char buf[]){
    int sentn = 0;
    int n = 0;
    while(sentn != msgLength){
        n += write(cfd, buf+sentn, msgLength-sentn);
        if(n == 0 || n==-1){
            return 0;
        }
        sentn += n;
    }
    return 1;
}

// fill tiles array with strings representing tiles of mahjong game
void fillTiles(){
    int tilesCounter = 0;
    char tile[3];
    for(int i=0; i<4; i++){
        for(int j=1; j<10; j++){
            // Tiles: Suits - Dots
            sprintf(tile, "D%d", j);
            strcpy(tiles[tilesCounter], tile);
            tilesCounter++;

            // Tiles: Suits - Bamboo
            sprintf(tile, "B%d", j);
            strcpy(tiles[tilesCounter], tile);
            tilesCounter++;

            // Tiles: Suits - Symbols
            sprintf(tile, "S%d", j);
            strcpy(tiles[tilesCounter], tile);
            tilesCounter++;
        }
        // Tiles: Dragons
        strcpy(tiles[tilesCounter], "DR"); tilesCounter++; // red
        strcpy(tiles[tilesCounter], "DG"); tilesCounter++; // green
        strcpy(tiles[tilesCounter], "DW"); tilesCounter++; // white

        // Tiles: Winds
        strcpy(tiles[tilesCounter], "WN"); tilesCounter++; // north
        strcpy(tiles[tilesCounter], "WE"); tilesCounter++; // east
        strcpy(tiles[tilesCounter], "WS"); tilesCounter++; // south
        strcpy(tiles[tilesCounter], "WW"); tilesCounter++; // west
    }
}

// fill tables array with 0's meaning they're empty and waiting for players
void fillRooms(){
    for(int i=0; i<maxGames; i++){
        for(int j=0; j<5; j++){
            tables[i][j] = 0;
        }
    }
}

// join room: first look for an available room with room owner, if not found look for any available room.
// returns index of joined room, -1 if no available rooms found
int joinRoom(int cfd){
    for(int i=0; i<maxGames; i++){
        if(tables[i][0] == 0 && tables[i][1] > 0){
            for(int nPlayer=1; nPlayer<5; nPlayer++){
                if(tables[i][nPlayer] == 0){
                    tables[i][nPlayer] = cfd;
                    return i;
                }
            }
        }
    }
    for(int i=0; i<maxGames; i++){
        if(tables[i][0] == 0){
            for(int nPlayer=1; nPlayer<5; nPlayer++){
                if(tables[i][nPlayer] == 0){
                    tables[i][nPlayer] = cfd;
                    return i;
                }
            }
        }
    }

    return -1;
}

// notify players in room that one player has disconnected
// return amount of remaining players
int disconnect(int roomVal, int playerIndex){
    tables[roomVal][playerIndex] = 0;
    char msg[msgLength] = "exi p";
    char seat[2];
    sprintf(seat, "%d", playerIndex);
    strcat(msg, seat);
    writeToRoom(roomVal, msg);

    int playerCounter = 0;
    for(int i=1; i<5; i++){
        if(tables[roomVal][i] > 0)
            playerCounter += 1;
    }

    printf("Player in room %d disconnected.\n", roomVal);
    return playerCounter;
}

// write to all players currently in a room
void writeToRoom(int roomVal, char msg[msgLength]){
    for(int i=1; i<5; i++){
        if(tables[roomVal][i] > 0){
            sendData(tables[roomVal][i], msg);
        }
    }

}

// Handles in-game communication between players 
void playGame(int roomVal){
    tables[roomVal][0] = 1;
    char tilesQueue[sumTiles][3];
    int tilesCounter = 0;

    int playersVal = 0;
    for(int i=1; i<5; i++){
        if(tables[roomVal][i] > 0){
            playersVal++;
        }
    }

    // copy initial tiles list
    for(int i=0; i<sumTiles; i++){
        strcpy(tilesQueue[i], tiles[i]);
    }
    // shuffle tiles for current game
    char temp[3];
    for(int i=0; i<sumTiles; i++){
        int j = rand() % sumTiles;
        strcpy(temp, tilesQueue[i]);
        strcpy(tilesQueue[i], tilesQueue[j]);
        strcpy(tilesQueue[j], temp);
    }

    // notify players that the game has started, assign initial hand to players
    for(int i=1; i<playersVal+1; i++){
        if(tables[roomVal][i] > 0){
            int n = sendData(tables[roomVal][i], "bgn $$");
            if(n == 0){
                playersVal = disconnect(roomVal, i);
                if(playersVal <= 1)
                    break;
                i--;
            }
            do{
                char receiveTile[msgLength] = "rcv "; 
                strcat(receiveTile, tilesQueue[tilesCounter]);
                n = sendData(tables[roomVal][i], receiveTile);
                if(n == 0){
                    playersVal = disconnect(roomVal, i);
                    if(playersVal <= 1)
                        break;
                    i--;
                }
                else{
                    tilesCounter++;
                }
            } while(tilesCounter % 13 != 0);
        }
    }

    int playerMove = 1;     // Index of player in tables[roomVal], room owner always has 1st turn.
    int n;
    char playerMsg[msgLength+1];

    // Main loop of game. Game has two types of turns. 
    // First type is draw turn. Player receives one tile and in exchange has to choose one tile to discard
    // Second type is discard turn. Players decide if they want to make use of a discard tile 
    while(1){ 
        char drawTile[msgLength+1] = "drw ";

        if(tables[roomVal][playerMove] > 0){
            // Draw Turn
            // Player receives a tile
            strcat(drawTile, tilesQueue[tilesCounter]);
            tilesCounter++;

            n = sendData(tables[roomVal][playerMove], drawTile);
            if(n == 0){
                char dscMsg[msgLength+1] = "dsc ";
                strcat(dscMsg, tilesQueue[tilesCounter-1]);
                writeToRoom(roomVal, dscMsg);
                playersVal = disconnect(roomVal, playerMove);
                if(playersVal <= 1)
                    break;
            }
            // Player decides which tile to discard
            n = readData(tables[roomVal][playerMove], playerMsg);
            // If player leaves room before deciding on that, discard the same tile he received and disconnect.
            if(n == 0){
                char dscMsg[msgLength+1] = "dsc ";
                strcat(dscMsg, tilesQueue[tilesCounter-1]);
                writeToRoom(roomVal, dscMsg);
                playersVal = disconnect(roomVal, playerMove);
                if(playersVal <= 1)
                    break;
            }
            else{
                // If player collected mahjong, message all players who's the winner.
                if (strcmp(playerMsg, "win $$") == 0){
                    char winMsg[msgLength+1] = "win $";
                    char cplayerMove[2];
                    sprintf(cplayerMove, "%d", playerMove);
                    strcat(winMsg, cplayerMove);
                    writeToRoom(roomVal, winMsg);
                    break;
                }
                // Otherwise we received which tile to discard
                else{
                    writeToRoom(roomVal, playerMsg);
                }
            }

            // Discard Turn
            // Other players decide if they want to make use of discarded tile
            int playerDiscard = playerMove + 1;
            do{
                if(tables[roomVal][playerDiscard] > 0){
                    // Read player's decision
                    n = readData(tables[roomVal][playerDiscard], playerMsg);
                    if(n == 0){
                        // If player left before making decision, message players that tile is still not taken and disconnect.
                        writeToRoom(roomVal, "tkn nn");
                        playersVal = disconnect(roomVal, playerDiscard);
                        if(playersVal <= 1)
                            break;
                        else
                            continue;
                    }
                    // if player decides to take that tile, stop the discard turns and begin next draw turn.
                    if(strcmp(playerMsg, "tkn yy") == 0){
                        writeToRoom(roomVal, "tkn yy");
                        break;
                    }
                    else{
                        writeToRoom(roomVal, "tkn nn");
                    }
                }
                playerDiscard = 1 + playerDiscard % 4;

            } while(playerDiscard != playerMove);

            if(playersVal <= 1)
                break;

            writeToRoom(roomVal, "nxt $$");
            if(tilesCounter == sumTiles - 1){
                writeToRoom(roomVal, "tie $$");
                printf("Game ended with a draw!\n");
                break;
            }
        }
        playerMove = 1 + playerMove % 4;
    }

    for(int i=0; i<5; i++){
        tables[roomVal][i] = 0;
    }
}

// inform players which seat in room is his and which seats are taken by other players
void setupGame(int roomVal){

    // notify players about incoming game information. 
    writeToRoom(roomVal, "set $$");
    // message players which seats are taken
    for(int i=1; i<5; i++){
        char msg[msgLength+1] = "set p";
        if(tables[roomVal][i] > 0){
            char seat[2];
            sprintf(seat, "%d", i);
            strcat(msg, seat);
            writeToRoom(roomVal, msg);
        }
    }
    // message players which seat in room is his
    for(int i=1; i<5; i++){
        char msg[msgLength] = "ure p";
        char seat[2];
        if(tables[roomVal][i] > 0){
            sprintf(seat, "%d", i);
            strcat(msg, seat);
            sendData(tables[roomVal][i], msg);
        }
    }
}

// Handle players joining rooms. Split them into regular clients and room owners
void* cthread(void* arg) {
    struct cln* c = (struct cln*)arg;
    printf("New connection: %s\n", inet_ntoa((struct in_addr)c->caddr.sin_addr));

    int roomVal = joinRoom(c->cfd);
    printf("%d joined room: %d\n", c->cfd, roomVal);
    if(roomVal < 0){
        sendData(c->cfd, "den $$");
    } else {

        // if player takes first seat in room - he's a room owner and only he can start the game
        if(c->cfd == tables[roomVal][1]){
            int n = sendData(c->cfd, "own $$");
            if(n == 0){
                disconnect(roomVal, 1);
                close(c->cfd);
                free(c);
                return EXIT_SUCCESS;
            }

            char playerInput[msgLength+1];
            while( readData(c->cfd, playerInput) > 0 ){

                // if owner commands start of the game, check if room is not in game and if there is more than 1 player in room.
                if(strcmp(playerInput, "bgn $$") == 0 && tables[roomVal][0] == 0){
                    int playersCount = 0;
                    for(int i=1; i<5; i++){
                        if(tables[roomVal][i] > 0)
                            playersCount++;
                    }

                    if(playersCount > 1){
                        setupGame(roomVal);
                        playGame(roomVal);
                        tables[roomVal][0] = 0;
                        break;
                    }
                    else{
                        n = sendData(c->cfd, "err 01");
                        if(n == 0)
                            break;
                    }
                }
            }
            disconnect(roomVal, 1);
        }
        // if client is a regular player, notify room owner about new player joining room
        else{
            int roomOwner = tables[roomVal][1];
            
            int n = sendData(roomOwner, "acc $$");
            if(n == 0){
                disconnect(roomVal, 1);
            }
            else{
                // heartbeat, continuously check if client is still reading data.
                while(sendData(c->cfd, "chk $$") > 0){
                    sleep(1);
                }
                // if player left before starting the game, manage the disconnection here
                if(tables[roomVal][0] == 0){
                    for(int i=1; i<5; i++){
                        if(tables[roomVal][i] == c->cfd){
                            disconnect(roomVal, i);
                        }
                    }
                }
            }
        }
    }
    // close sockets.
    close(c->cfd);
    free(c);
    return EXIT_SUCCESS;
}

int main(int argc, char* argv[]) {
    signal(SIGPIPE, SIG_IGN);
    fillRooms();
    fillTiles();

    pthread_t tid;
    socklen_t slt;
    int sfd, on = 1;
    struct sockaddr_in saddr;

    saddr.sin_family = AF_INET;
    saddr.sin_addr.s_addr = INADDR_ANY;
    saddr.sin_port = htons(1234);

    sfd = socket(AF_INET, SOCK_STREAM, 0);
    setsockopt(sfd, SOL_SOCKET, SO_REUSEADDR, (char*)&on, sizeof(on));
    bind(sfd, (struct sockaddr*)&saddr, sizeof(saddr));
    listen(sfd, 10);
    for(;;) {
        struct cln* c = malloc(sizeof(struct cln));
        slt = sizeof(c->caddr);
        c->cfd = accept(sfd, (struct sockaddr*)&c->caddr, &slt);
        pthread_create(&tid, NULL, cthread, c);
        pthread_detach(tid);

    }
    close(sfd);
    return EXIT_SUCCESS;
}