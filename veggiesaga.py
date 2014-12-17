# Veggie Saga             #
# A healthier way to play #

# Requires pygame.        #

"""
This program has "veggie data structures", which are basically dictionaries
with the following keys:
  'x' and 'y' - The location of the veggie on the board. 0,0 is the top left.
                There is also a HIDDEN_ROW row that 'y' can be set to,
                to indicate that it is above the board.
  'direction' - one of the four constant variables UP, DOWN, LEFT, RIGHT.
                This is the direction the veggie is moving.
  'imageNum'  - The integer index into IMAGES to denote which image
                this veggie uses.
"""

''' Note that the game looks for PNG images for each veggie using the name format
    "veggie#.png" (# from 0 to NUM_VEGGIES - 1). '''

import random, time, pygame, sys, copy
from pygame.locals import *
from random import randint
import tkinter as tk
from tkinter import *
import os
from threading import Thread

''' Class definitions '''
class Genome(object):
    def __init__(self, moves):
        self.moves   = moves
        self.score   = None
        self.length  = None

class Environment(object):
    def __init__(self, board, item_stack):
        self.board = board
        self.item_stack = item_stack
        self.gene_pool = []

""" Constants """

DEBUG = False

FPS             = 0   # Screen refresh rate (in Frames Per Second). 0 --> No limit.
MOVE_RATE       = 75  # Animation speed (1 to 100).  100 --> Skip animation.
IMAGE_SIZE      = 64  # Tile size (px).
NUM_VEGGIES     = 7   # Number of veggie types.
MAX_GAME_LENGTH = 10000 # The number of moves until a game times out.
GENE_POOL_SIZE  = 8   # The number of genomes in each environment in the Genetic Algorithm
MUTATION_RATE   = 10  # The frequency (in generations) that a mutation will occur.

assert NUM_VEGGIES >= 5 # The game needs at least 5 veggies

# Window sizing constants
WINDOW_WIDTH  = 800 # Width of game window (px).
WINDOW_HEIGHT = 600 # Height of game window (px).
BOARD_WIDTH   = 8   # Number of columns.
BOARD_HEIGHT  = 8   # Number of rows.
X_MARGIN      = int((WINDOW_WIDTH - IMAGE_SIZE * BOARD_WIDTH) / 2)   # Margin size on the x-axis.
Y_MARGIN      = int((WINDOW_HEIGHT - IMAGE_SIZE * BOARD_HEIGHT) / 2) # Margin size on the y-axis.

# Display color constants
GRID_COLOR         = (  0,   0, 255) # Blue; Game board color.
SCORE_COLOR        = ( 85,  65,   0) # Pop-up score color.
GAME_OVER_COLOR    = (255,   0,   0) # Red; Color of the "Game over" text.
HIGHLIGHT_COLOR    = (255, 100, 100) # Reddish; Selected board space border color.
GAME_OVER_BG_COLOR = (  0,   0,   0) # Black; Background color of the "Game over" text.

# Identifier constants
UP          = 'up'
DOWN        = 'down'
LEFT        = 'left'
RIGHT       = 'right'
EMPTY_SPACE = -1       # An arbitrary, non-positive value that signifies an empty space on the board.
HIDDEN_ROW  = 'hidden' # an arbitrary, noninteger  #xxx what

run = False
showMoves = False
generationLimit = 100;

''' (Move later) button callbacks '''

def startButton(event):
    global run
    if run: run = False
    elif not run: run = True
    return

def showButton(event):
    global showMoves
    if not showMoves: showMoves = True
    elif showMoves: showMoves = False
    return

# Tkinter stuff
root = tk.Tk()
embed = tk.Frame(root, width = WINDOW_WIDTH, height = WINDOW_HEIGHT)
embed.pack()
start = tk.Button(root, text='Start/Stop')
start.bind('<Button-1>', startButton)
start.pack(side=LEFT)
stop = tk.Button(root, text='Show/Hide Animations')
stop.bind('<Button-1>', showButton)
stop.pack(side=LEFT)

genLabel = StringVar()
Label(root, textvariable=genLabel).pack()
scoreLabel = StringVar()
Label(root, textvariable=scoreLabel).pack()
statusLabel = StringVar()
Label(root, textvariable=statusLabel).pack()

#embed.grid(columnspan = 600, rowspan = 500) # Adds grid
#embed.pack(side = TOP) # packs window to the left
#buttonwin = tk.Frame(root, width = 75, height = 500)
#buttonwin.pack(side = RIGHT)
os.environ['SDL_WINDOWID'] = str(embed.winfo_id())
os.environ['SDL_VIDEODRIVER'] = 'windib'


''' Main function '''

def main():
    global gameClock, gameWindow, IMAGES, mainFont, smallFont, boardRects, bgImage, draggingPosition, draggingVeggie

    # Initial set up.
    pygame.init()
    gameClock        = pygame.time.Clock()
    gameWindow       = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption('Veggie Saga')
    mainFont         = pygame.font.Font(None, 72)
    smallFont        = pygame.font.Font(None, 36) # Used for Game Over screen.
    bgImage          = pygame.image.load("background.jpg").convert()
    draggingPosition = None
    draggingVeggie   = None

    moves = generateMoves()
    board = generateInitialLayout()
    fills = generateReplacementList()
    envir = Environment(board, fills)

    # Load the images
    IMAGES = []
    for i in range(1, NUM_VEGGIES + 1):
        img = pygame.image.load('veggie%s.png' % i)
        if img.get_size() != (IMAGE_SIZE, IMAGE_SIZE):
            img = pygame.transform.smoothscale(img, (IMAGE_SIZE, IMAGE_SIZE))
        IMAGES.append(img)

    # Create pygame.Rect objects for each board space to
    # do board-coordinate-to-pixel-coordinate conversions.
    boardRects = []
    for x in range(BOARD_WIDTH):
        boardRects.append([])
        for y in range(BOARD_HEIGHT):
            r = pygame.Rect((X_MARGIN + (x * IMAGE_SIZE),
                             Y_MARGIN + (y * IMAGE_SIZE),
                             IMAGE_SIZE,
                             IMAGE_SIZE))
            boardRects[x].append(r)



    #while True:
        #result = runGameAsAI(moves, board, fills)
    try:
        Thread(target=runAI, args=(envir, GENE_POOL_SIZE, True)).start()
    except:
        print("Failed to start thread.")

    tk.mainloop()

    idleUntilExit()


''' AI Code '''

def runAI(envir, pool_size, reset=False):
    # Initialize
    bestScore = 0
    if reset is True:
        generation = 0
        # Generate pool
        for i in range(0, pool_size):
            moves = generateMoves()
            genome = Genome(moves)
            envir.gene_pool.append(genome)

        # Perform fitness function for each
        i = 0
        for genome in envir.gene_pool:
            checkStatus() # Check thread status.
            statusLabel.set("Simulating genome " + str(i) + ".")
            genome.score, genome.length = runGameAsAI(genome.moves, envir.board, envir.item_stack, 100)
            print("Genome scored " + str(genome.score) + " in " + str(genome.length) + " moves.")
            if genome.score > bestScore: bestScore = genome.score
            i += 1
            scoreLabel.set("Best score: " + str(bestScore))

    # Run until generationLimit
    while generation < generationLimit:
        checkStatus() # Check thread status.
        genLabel.set("Generation: " + str(generation + 1))
        generation += 1

        # Pick two genomes with roulette wheel selection?
        statusLabel.set("Selecting parent genomes.")
        parentA = getNewParentIndex(envir.gene_pool)
        parentB = getNewParentIndex(envir.gene_pool)
        while parentB == parentA:
            print("Identical parents; reselecting.")
            parentB = getNewParentIndex(envir.gene_pool)

        # Crossover the selected genomes
        statusLabel.set("Crossing over.")
        childA = crossover(envir.gene_pool, parentA, parentB)
        statusLabel.set("Simulating offspring A")
        childA.score, childA.length = runGameAsAI(childA.moves, envir.board, envir.item_stack, 100)
        childB = crossover(envir.gene_pool, parentB, parentA)
        statusLabel.set("Simulating offspring B")
        childB.score, childB.length = runGameAsAI(childB.moves, envir.board, envir.item_stack, 100)
        statusLabel.set("Inserting...")

        # Find out which two are the worst (including new genomes)
        worst = -1
        i = 0
        for genome in envir.gene_pool:
            if DEBUG: print("Score of " + str(i) + ": " + str(genome.score))
            if worst == -1:
                worst = i
            elif genome.score < envir.gene_pool[worst].score:
                worst = i
            i += 1

        if childA.score < envir.gene_pool[worst].score: # Skip child A...
            if childB.score > envir.gene_pool[worst].score: # Make sure B isn't also awful
                print("Replacing genome at " + str(worst) + " with score of " + str(envir.gene_pool[worst].score))
                print("With child B with score of " + str(childB.score))
                envir.gene_pool[worst] = childB
                if childB.score > bestScore:
                    bestScore = childB.score
                    scoreLabel.set("Best score: " + str(bestScore))
        elif childB.score < envir.gene_pool[worst].score: # Skip child B...
            print("Replacing genome at " + str(worst) + " with score of " + str(envir.gene_pool[worst].score))
            print("With child A with score of " + str(childA.score))
            envir.gene_pool[worst] = childA
            if childA.score > bestScore:
                bestScore = childA.score
                scoreLabel.set("Best score: " + str(bestScore))
        else:
            print("Replacing genome at " + str(worst) + " with score of " + str(envir.gene_pool[worst].score))
            print("With child A with score of " + str(childA.score))
            envir.gene_pool[worst] = childA
            if childA.score > bestScore:
                bestScore = childA.score
                scoreLabel.set("Best score: " + str(bestScore))
            # Find the second-worst to replace it with B.
            worst2 = -1
            i = 0
            for genome in envir.gene_pool:
                if DEBUG: print("Score of " + str(i) + ": " + str(genome.score))
                if i == worst:
                    continue
                if worst2 == -1:
                    worst2 = i
                elif genome.score < envir.gene_pool[worst2].score:
                    worst2 = i
                i += 1

            if childB.score > envir.gene_pool[worst2].score: # Make sure B isn't even worse.
                print("Replacing genome at " + str(worst2) + " with score of " + str(envir.gene_pool[worst2].score))
                print("With child B with score of " + str(childB.score))
                envir.gene_pool[worst2] = childB
                if childB.score > bestScore:
                    bestScore = childB.score
                    scoreLabel.set("Best score: " + str(bestScore))

        if DEBUG: print("Worst scoring one was " + str(worst) + " with score " + str(envir.gene_pool[worst].score))

        # If it is time, then mutate.
        if generation%MUTATION_RATE == 0:
            mutate(envir.gene_pool)
    #
    #
    return()

def checkStatus():
    while not run:
        statusLabel.set("Not running.")
        time.sleep(1)

# Creates and returns a BOARD_WIDTH x BOARD_HEIGHT matrix of veggies for the initial game board.
def generateInitialLayout():
    print("Generating random game board...")
    initialLayout = [[0 for x in range(BOARD_WIDTH)] for x in range(BOARD_HEIGHT)]
    return initialLayout

# Creates and returns a list of veggies that will be used to fill in empty spaces.
def generateReplacementList():
    print("Generating list of replacement veggies...")
    veggies = [0 for x in range(MAX_GAME_LENGTH)]

    for i in range(0, MAX_GAME_LENGTH):
        veggies[i] = random.randint(1, NUM_VEGGIES)

    return veggies


# Creates and returns an array of size MAX_GAME_LENGTH that contains random AI moves
def generateMoves():
    if DEBUG: print("Generating AI moves...")

    moves = [[0 for x in range(3)] for x in range(MAX_GAME_LENGTH)]

    for i in range(0, MAX_GAME_LENGTH):
        x = randint(0,7)
        y = randint(0,7)
        moves[i][0] = x
        moves[i][1] = y
        moves[i][2] = randMove(x, y)

    if DEBUG: print(moves)
    return moves

# Randomly selects a direction for the AI's move.  By evaluating the position, it always returns a valid move.
def randMove(x, y):
    bag = list()

    if x == 0:
        if y == 0:
            # Down or Right only
            bag = list([DOWN, RIGHT])
        elif y == 7:
            # Up or Right only
            bag = list([UP, RIGHT])
        else:
            # Up, Down, or Right
            bag = list([UP, DOWN, RIGHT])
    elif x == 7:
        if y == 0:
            # Down or Left only
            bag = list([DOWN, LEFT])
        elif y == 7:
            # Up or Left only
            bag = list([UP, LEFT])
        else:
            # Up, Down, or Left
            bag = list([UP, DOWN, LEFT])
    elif y == 0:
        # Down, Left, or Right
        bag = list([DOWN, LEFT, RIGHT])
    elif y == 7:
        # Up, Left, or Right
        bag = list([UP, LEFT, RIGHT])
    else:
        # Anything
        bag = list([UP, DOWN, LEFT, RIGHT])

    return random.choice(bag)

def getNewParentIndex(gene_pool):
    sumScore = 0
    best = 0
    for genome in gene_pool:
        sumScore += genome.score

    r = randint(0, sumScore)

    i = 0
    sumScore = 0
    for genome in gene_pool:
        sumScore += genome.score
        if r < sumScore:
            return i
        else:
            i += 1

def crossover(gene_pool, a, b):
    # Note that a and b are indices
    crosspoint = randint(0, MAX_GAME_LENGTH - 1)
    x = 0
    y = 0
    dir = None

    genomeA = gene_pool[a]
    genomeB = gene_pool[b]
    movesA = genomeA.moves
    movesB = genomeB.moves

    moves = [[0 for x in range(3)] for x in range(MAX_GAME_LENGTH)]

    for i in range(0, MAX_GAME_LENGTH):
        move = None
        if i < crosspoint: # Copy from
            move = movesA[i]
        else: # Copy from B
            move = movesB[i]

        moves[i][0] = move[0]
        moves[i][1] = move[1]
        moves[i][2] = move[2]

    return Genome(moves)

# Swap two random moves on a random genome.
def mutate(gene_pool):
    i = randint(0, GENE_POOL_SIZE - 1)
    j = randint(0, MAX_GAME_LENGTH - 1)
    k = randint(0, MAX_GAME_LENGTH - 1)

    moves = gene_pool[i].moves
    x = moves[j][0]
    y = moves[j][1]
    m = moves[j][2]

    moves[j][0] = moves[k][0]
    moves[j][1] = moves[k][1]
    moves[j][2] = moves[k][2]

    moves[k][0] = x
    moves[k][1] = y
    moves[k][2] = m

# Requires moves, an array of MAX_GAME_LENGTH size that contains the AIs moves, in order.
# board, the layout of the board
# item_stack, the stack of items that will fill in empty spaces.
def runGameAsAI(moves, board, fills, speed=MOVE_RATE):
    # Plays through a single game. When the game is over, this function returns.
    global draggingPosition, draggingVeggie
    global score, turn

    # Initialize the board.
    gameBoard               = []
    for x in range(BOARD_WIDTH):
        gameBoard.append([EMPTY_SPACE] * BOARD_HEIGHT)

    # initialize variables for the start of a new game
    score                   = 0
    turn                    = 0
    move                    = None
    gameIsOver              = False
    clickContinueTextSurf   = None

    # Populate and display the initial veggies.
    fillBoardAndAnimate(gameBoard, [], speed)

    while turn < MAX_GAME_LENGTH and not gameIsOver: # Run game until there are no more possible moves or MAX_GAME_LENGTH moves made.
        checkStatus() # Check thread status.

        # Get the next veggies to swap from the moves list.
        move = moves[turn]
        turn = turn + 1;
        # Get the data structures of the veggies to try swapping.
        firstSwappingVeggie, secondSwappingVeggie = getSwappingVeggies_AI(gameBoard, move)

        # Show the swap animation on the screen.
        boardCopy = getBoardCopyMinusVeggies(gameBoard, (firstSwappingVeggie, secondSwappingVeggie))
        animateMovingVeggies(boardCopy, [firstSwappingVeggie, secondSwappingVeggie], [], speed)

        # Swap the veggies in the board data structure.
        gameBoard[firstSwappingVeggie['x']][firstSwappingVeggie['y']] = secondSwappingVeggie['imageNum']
        gameBoard[secondSwappingVeggie['x']][secondSwappingVeggie['y']] = firstSwappingVeggie['imageNum']

        # See if this is a matching move.
        matchedVeggies = findMatchingVeggies(gameBoard)
        if matchedVeggies == []:
            # Was not a matching move; swap the veggies back
            animateMovingVeggies(boardCopy, [firstSwappingVeggie, secondSwappingVeggie], [], speed)
            gameBoard[firstSwappingVeggie['x']][firstSwappingVeggie['y']] = firstSwappingVeggie['imageNum']
            gameBoard[secondSwappingVeggie['x']][secondSwappingVeggie['y']] = secondSwappingVeggie['imageNum']
        else:
            # This was a matching move.
            scoreAdd = 0
            while matchedVeggies != []:
                # Remove matched veggies, then pull down the board.

                # points is a list of dicts that tells fillBoardAndAnimate()
                # where on the screen to display text to show how many
                # points the player got. points is a list because if
                # the playergets multiple matches, then multiple points text should appear.
                points = []
                for veggieSet in matchedVeggies:
                    scoreAdd += (10 + (len(veggieSet) - 3) * 10)
                    for veggie in veggieSet:
                        gameBoard[veggie[0]][veggie[1]] = EMPTY_SPACE
                    points.append({'points': scoreAdd,
                                   'x': veggie[0] * IMAGE_SIZE + X_MARGIN,
                                   'y': veggie[1] * IMAGE_SIZE + Y_MARGIN})
                score += scoreAdd

                # Drop the new veggies.
                fillBoardAndAnimate(gameBoard, points, speed)

                # Check if there are any new matches.
                matchedVeggies = findMatchingVeggies(gameBoard)

        if not canMakeMove(gameBoard):
            gameIsOver = True

        # Redraw the board.
        if speed != 100:
            gameWindow.blit(bgImage, [0, 0]) # Draw the background.
            drawBoard(gameBoard)

        if speed != 100:
            drawScore(score)
            root.update()
            pygame.display.update()
            #gameClock.tick(FPS)

    #if not gameIsOver:
    if 0:
        drawScore(score)
        root.update()
        pygame.display.update()
        gameClock.tick(FPS)

    return score, turn

def getSwappingVeggies_AI(board, move):
    if DEBUG: print("getSwappingVeggies_AI")

    x = move[0]
    y = move[1]
    movex = 0
    movey = 0
    if move[2] == LEFT:
        movex = -1
    elif move[2] == RIGHT:
        movex = 1
    elif move[2] == DOWN:
        movey = 1
    elif move[2] == UP:
        movey = -1

    firstVeggie = {'imageNum': board[x][y],
                'x': x,
                'y': y}
    secondVeggie = {'imageNum': board[x + movex][y + movey],
                 'x': x + movex,
                 'y': y + movey}

    firstVeggie['direction'] = move[2]
    if move[2] == LEFT:
        secondVeggie['direction'] = RIGHT
    elif move[2] == RIGHT:
        secondVeggie['direction'] = LEFT
    elif move[2] == DOWN:
        secondVeggie['direction'] = UP
    elif move[2] == UP:
        secondVeggie['direction'] = DOWN

    return(firstVeggie, secondVeggie)

''' Universal Game code '''

def idleUntilExit(): # Wait for user to hit the Esc key, then exit.
    '''while True:
        for event in pygame.event.get(): # event handling loop
            if event.type == QUIT or (event.type == KEYUP and event.key == K_ESCAPE):
                pygame.quit()
                root.quit()
                sys.exit()'''
    while True:
        event = pygame.event.wait()
        if event.type == QUIT or (event.type == KEYUP and event.key == K_ESCAPE):
            pygame.quit()
            root.quit()
            sys.exit()


# Returns True if there are moves left, False otherwise.
def canMakeMove(board):
    # The patterns in oneOffPatterns represent veggies that are configured
    # in a way where it only takes one move to make a triplet.
    oneOffPatterns = (((0,1), (1,0), (2,0)),
                      ((0,1), (1,1), (2,0)),
                      ((0,0), (1,1), (2,0)),
                      ((0,1), (1,0), (2,1)),
                      ((0,0), (1,0), (2,1)),
                      ((0,0), (1,1), (2,1)),
                      ((0,0), (0,2), (0,3)),
                      ((0,0), (0,1), (0,3)))

    # The x and y variables iterate over each space on the board.
    # If we use + to represent the currently iterated space on the
    # board, then this pattern: ((0,1), (1,0), (2,0))refers to identical
    # veggies being set up like this:
    #
    #     +A
    #     B
    #     C
    #
    # That is, veggie A is offset from the + by (0,1), veggie B is offset
    # by (1,0), and veggie C is offset by (2,0). In this case, veggie A can
    # be swapped to the left to form a vertical three-in-a-row triplet.
    #
    # There are eight possible ways for the veggies to be one move
    # away from forming a triple, hence oneOffPattern has 8 patterns.

    for x in range(BOARD_WIDTH):
        for y in range(BOARD_HEIGHT):
            for pat in oneOffPatterns:
                # check each possible pattern of "match in next move" to
                # see if a possible move can be made.
                if (getVeggieAt(board, x+pat[0][0], y+pat[0][1]) == \
                    getVeggieAt(board, x+pat[1][0], y+pat[1][1]) == \
                    getVeggieAt(board, x+pat[2][0], y+pat[2][1]) != None) or \
                   (getVeggieAt(board, x+pat[0][1], y+pat[0][0]) == \
                    getVeggieAt(board, x+pat[1][1], y+pat[1][0]) == \
                    getVeggieAt(board, x+pat[2][1], y+pat[2][0]) != None):
                    return True # return True the first time you find a pattern
    return False

''' Human player code '''

def playGame():
    # Plays through a single game. When the game is over, this function returns.
    global draggingPosition, draggingVeggie
    global score

    # Initialize the board.
    gameBoard               = []
    for x in range(BOARD_WIDTH):
        gameBoard.append([EMPTY_SPACE] * BOARD_HEIGHT)

    # initialize variables for the start of a new game
    score                   = 0
    turn                    = 0
    gameIsOver              = False
    draggingPosition        = None
    lastMouseDownX          = None
    lastMouseDownY          = None
    firstSelectedVeggie     = None
    clickContinueTextSurf   = None

    # Populate and display the initial veggies.
    fillBoardAndAnimate(gameBoard, [])

    while turn < MAX_GAME_LENGTH: # Run game until there are no more possible moves or MAX_GAME_LENGTH moves made.
        clickedSpace = None

        ''' For human player input '''
        for event in pygame.event.get(): # event handling loop
            if event.type == QUIT or (event.type == KEYUP and event.key == K_ESCAPE):
                pygame.quit()
                sys.exit()
            elif event.type == KEYUP and event.key == K_BACKSPACE:
                return # start a new game

            elif event.type == MOUSEBUTTONUP:
                draggingPosition = None

                if gameIsOver:
                    return # after games ends, click to start a new game

                if event.pos == (lastMouseDownX, lastMouseDownY):
                    # This event is a mouse click, not the end of a mouse drag.
                    clickedSpace = checkForVeggieClick(event.pos)
                else:
                    # this is the end of a mouse drag
                    firstSelectedVeggie = checkForVeggieClick((lastMouseDownX, lastMouseDownY))
                    clickedSpace = checkForVeggieClick(event.pos)
                    if not firstSelectedVeggie or not clickedSpace:
                        # if not part of a valid drag, deselect both
                        firstSelectedVeggie = None
                        clickedSpace = None
            elif event.type == MOUSEBUTTONDOWN:
                # this is the start of a mouse click or mouse drag
                lastMouseDownX, lastMouseDownY = event.pos
                draggingPosition = event.pos
                draggingVeggie = checkForVeggieClick(event.pos)

                # Uncomment to highlight the veggie square while dragging.
                #firstSelectedVeggie = checkForVeggieClick((lastMouseDownX, lastMouseDownY))

        if clickedSpace and not firstSelectedVeggie:
            # This was the first veggie clicked on.
            firstSelectedVeggie = clickedSpace
        elif clickedSpace and firstSelectedVeggie:
            # Two veggies have been clicked on and selected. Swap the veggies.
            firstSwappingVeggie, secondSwappingVeggie = getSwappingVeggies_H(gameBoard, firstSelectedVeggie, clickedSpace)
            if firstSwappingVeggie == None and secondSwappingVeggie == None:
                # If both are None, then the veggies were not adjacent
                firstSelectedVeggie = None # deselect the first veggie
                continue

            # Show the swap animation on the screen.
            boardCopy = getBoardCopyMinusVeggies(gameBoard, (firstSwappingVeggie, secondSwappingVeggie))
            animateMovingVeggies(boardCopy, [firstSwappingVeggie, secondSwappingVeggie], [])

            # Swap the veggies in the board data structure.
            gameBoard[firstSwappingVeggie['x']][firstSwappingVeggie['y']] = secondSwappingVeggie['imageNum']
            gameBoard[secondSwappingVeggie['x']][secondSwappingVeggie['y']] = firstSwappingVeggie['imageNum']

            # See if this is a matching move.
            matchedVeggies = findMatchingVeggies(gameBoard)
            if matchedVeggies == []:
                # Was not a matching move; swap the veggies back
                animateMovingVeggies(boardCopy, [firstSwappingVeggie, secondSwappingVeggie], [])
                gameBoard[firstSwappingVeggie['x']][firstSwappingVeggie['y']] = firstSwappingVeggie['imageNum']
                gameBoard[secondSwappingVeggie['x']][secondSwappingVeggie['y']] = secondSwappingVeggie['imageNum']
            else:
                # This was a matching move.
                scoreAdd = 0
                while matchedVeggies != []:
                    # Remove matched veggies, then pull down the board.

                    # points is a list of dicts that tells fillBoardAndAnimate()
                    # where on the screen to display text to show how many
                    # points the player got. points is a list because if
                    # the playergets multiple matches, then multiple points text should appear.
                    points = []
                    for veggieSet in matchedVeggies:
                        scoreAdd += (10 + (len(veggieSet) - 3) * 10)
                        for veggie in veggieSet:
                            gameBoard[veggie[0]][veggie[1]] = EMPTY_SPACE
                        points.append({'points': scoreAdd,
                                       'x': veggie[0] * IMAGE_SIZE + X_MARGIN,
                                       'y': veggie[1] * IMAGE_SIZE + Y_MARGIN})
                    score += scoreAdd

                    # Drop the new veggies.
                    fillBoardAndAnimate(gameBoard, points)

                    # Check if there are any new matches.
                    matchedVeggies = findMatchingVeggies(gameBoard)
            firstSelectedVeggie = None

            if not canMakeMove(gameBoard):
                gameIsOver = True

        # Draw the board.
        gameWindow.blit(bgImage, [0, 0]) # Draw the background.
        drawBoard(gameBoard)

        if firstSelectedVeggie != None:
            highlightSpace(firstSelectedVeggie['x'], firstSelectedVeggie['y'])

        if gameIsOver:
            if clickContinueTextSurf == None:
                # Only render the text once. In future iterations, just
                # use the Surface object already in clickContinueTextSurf
                clickContinueTextSurf = smallFont.render('Final Score: %s (Press Esc to exit; Click to Continue)' % (score), 1, GAME_OVER_COLOR, GAME_OVER_BG_COLOR)
                clickContinueTextRect = clickContinueTextSurf.get_rect()
                clickContinueTextRect.center = int(GAME_WINDOW_WIDTH / 2), int(GAME_WINDOW_HEIGHT / 2)
            gameWindow.blit(clickContinueTextSurf, clickContinueTextRect)
        drawScore(score)
        root.update()
        pygame.display.update()
        gameClock.tick(FPS)

    # Ran out of turns. #xxx
        #TODO

def getSwappingVeggies(board, firstXY, secondXY):
    if DEBUG: print("getSwappingVeggies")
    # If the veggies at the (X, Y) coordinates of the two veggies are adjacent,
    # then their 'direction' keys are set to the appropriate direction
    # value to be swapped with each other.
    # Otherwise, (None, None) is returned.
    firstVeggie = {'imageNum': board[firstXY['x']][firstXY['y']],
                'x': firstXY['x'],
                'y': firstXY['y']}
    secondVeggie = {'imageNum': board[secondXY['x']][secondXY['y']],
                 'x': secondXY['x'],
                 'y': secondXY['y']}
    highlightedVeggie = None
    if firstVeggie['x'] == secondVeggie['x'] + 1 and firstVeggie['y'] == secondVeggie['y']:
        firstVeggie['direction'] = LEFT
        secondVeggie['direction'] = RIGHT
    elif firstVeggie['x'] == secondVeggie['x'] - 1 and firstVeggie['y'] == secondVeggie['y']:
        firstVeggie['direction'] = RIGHT
        secondVeggie['direction'] = LEFT
    elif firstVeggie['y'] == secondVeggie['y'] + 1 and firstVeggie['x'] == secondVeggie['x']:
        firstVeggie['direction'] = UP
        secondVeggie['direction'] = DOWN
    elif firstVeggie['y'] == secondVeggie['y'] - 1 and firstVeggie['x'] == secondVeggie['x']:
        firstVeggie['direction'] = DOWN
        secondVeggie['direction'] = UP
    else:
        # These veggies are not adjacent and can't be swapped.
        return None, None
    return firstVeggie, secondVeggie

def drawMovingVeggie(veggie, progress):
    # Draw a veggie sliding in the direction that its 'direction' key
    # indicates. The progress parameter is a number from 0 (just
    # starting) to 100 (slide complete).
    movex = 0
    movey = 0
    progress *= 0.01

    if veggie['direction'] == UP:
        movey = -int(progress * IMAGE_SIZE)
    elif veggie['direction'] == DOWN:
        movey = int(progress * IMAGE_SIZE)
    elif veggie['direction'] == RIGHT:
        movex = int(progress * IMAGE_SIZE)
    elif veggie['direction'] == LEFT:
        movex = -int(progress * IMAGE_SIZE)

    basex = veggie['x']
    basey = veggie['y']
    if basey == HIDDEN_ROW:
        basey = -1

    pixelx = X_MARGIN + (basex * IMAGE_SIZE)
    pixely = Y_MARGIN + (basey * IMAGE_SIZE)
    r = pygame.Rect( (pixelx + movex, pixely + movey, IMAGE_SIZE, IMAGE_SIZE) )
    gameWindow.blit(IMAGES[veggie['imageNum']], r)


def pullDownAllVeggies(board):
    if DEBUG: print("Pull down all veggies")
    # pulls down veggies on the board to the bottom to fill in any gaps
    for x in range(BOARD_WIDTH):
        veggiesInColumn = []
        for y in range(BOARD_HEIGHT):
            if board[x][y] != EMPTY_SPACE:
                veggiesInColumn.append(board[x][y])
        board[x] = ([EMPTY_SPACE] * (BOARD_HEIGHT - len(veggiesInColumn))) + veggiesInColumn


def getVeggieAt(board, x, y):
    #if DEBUG: print("getVeggieAt" + str(x) + "," + str(y))
    if x < 0 or y < 0 or x >= BOARD_WIDTH or y >= BOARD_HEIGHT:
        return None
    else:
        return board[x][y]


def getDropSlots(board):
    if DEBUG: print("getDropSlots")
    # Creates a "drop slot" for each column and fills the slot with a
    # number of veggies that that column is lacking. This function assumes
    # that the veggies have been gravity dropped already.
    boardCopy = copy.deepcopy(board)
    pullDownAllVeggies(boardCopy)

    dropSlots = []
    for i in range(BOARD_WIDTH):
        dropSlots.append([])

    # count the number of empty spaces in each column on the board
    for x in range(BOARD_WIDTH):
        for y in range(BOARD_HEIGHT-1, -1, -1): # start from bottom, going up
            if boardCopy[x][y] == EMPTY_SPACE:
                possibleVeggies = list(range(len(IMAGES)))
                for offsetX, offsetY in ((0, -1), (1, 0), (0, 1), (-1, 0)):
                    # Narrow down the possible veggies we should put in the
                    # blank space so we don't end up putting an two of
                    # the same veggies next to each other when they drop.
                    neighborVeggie = getVeggieAt(boardCopy, x + offsetX, y + offsetY)
                    if neighborVeggie != None and neighborVeggie in possibleVeggies:
                        possibleVeggies.remove(neighborVeggie)

                newVeggie = random.choice(possibleVeggies)
                boardCopy[x][y] = newVeggie
                dropSlots[x].append(newVeggie)
    return dropSlots


def findMatchingVeggies(board):
    veggiesToRemove = [] # a list of lists of veggies in matching triplets that should be removed
    boardCopy = copy.deepcopy(board)

    # loop through each space, checking for 3 adjacent identical veggies
    for x in range(BOARD_WIDTH):
        for y in range(BOARD_HEIGHT):
            # look for horizontal matches
            if getVeggieAt(boardCopy, x, y) == getVeggieAt(boardCopy, x + 1, y) == getVeggieAt(boardCopy, x + 2, y) and getVeggieAt(boardCopy, x, y) != EMPTY_SPACE:
                targetVeggie = boardCopy[x][y]
                offset = 0
                removeSet = []
                while getVeggieAt(boardCopy, x + offset, y) == targetVeggie:
                    # keep checking if there's more than 3 veggies in a row
                    removeSet.append((x + offset, y))
                    boardCopy[x + offset][y] = EMPTY_SPACE
                    offset += 1
                veggiesToRemove.append(removeSet)

            # look for vertical matches
            if getVeggieAt(boardCopy, x, y) == getVeggieAt(boardCopy, x, y + 1) == getVeggieAt(boardCopy, x, y + 2) and getVeggieAt(boardCopy, x, y) != EMPTY_SPACE:
                targetVeggie = boardCopy[x][y]
                offset = 0
                removeSet = []
                while getVeggieAt(boardCopy, x, y + offset) == targetVeggie:
                    # keep checking, in case there's more than 3 veggies in a row
                    removeSet.append((x, y + offset))
                    boardCopy[x][y + offset] = EMPTY_SPACE
                    offset += 1
                veggiesToRemove.append(removeSet)

    return veggiesToRemove


def highlightSpace(x, y):
    pygame.draw.rect(gameWindow, HIGHLIGHT_COLOR, boardRects[x][y], 4)


def getDroppingVeggies(board):
    if DEBUG: print("getDroppingVeggies")
    # Find all the veggies that have an empty space below them
    boardCopy = copy.deepcopy(board)
    droppingVeggies = []
    for x in range(BOARD_WIDTH):
        for y in range(BOARD_HEIGHT - 2, -1, -1):
            if boardCopy[x][y + 1] == EMPTY_SPACE and boardCopy[x][y] != EMPTY_SPACE:
                # This space drops if not empty but the space below it is
                droppingVeggies.append( {'imageNum': boardCopy[x][y], 'x': x, 'y': y, 'direction': DOWN} )
                boardCopy[x][y] = EMPTY_SPACE
    return droppingVeggies


def animateMovingVeggies(board, veggies, pointsText, speed=MOVE_RATE):
    #if DEBUG: print("animateMovingVeggies")
    global score

    # pointsText is a dictionary with keys 'x', 'y', and 'points'
    progress = 0 # progress at 0 represents beginning, 100 means finished.
    if showMoves is True: progress = 0
    elif speed == 100: progress = 100
    while progress < 100: # animation loop
        gameWindow.blit(bgImage, [0, 0])
        drawBoard(board)
        for veggie in veggies: # Draw each veggie.
            drawMovingVeggie(veggie, progress)
        drawScore(score)
        for pointText in pointsText:
            pointsSurf = mainFont.render("+" + str(pointText['points']) + "!", 1, SCORE_COLOR)
            pointsRect = pointsSurf.get_rect()
            pointsRect.center = (pointText['x'], pointText['y'])
            gameWindow.blit(pointsSurf, pointsRect)
        pygame.display.update()
        progress += speed # progress the animation a little bit more for the next frame
    root.update()
    gameClock.tick(FPS)


def moveVeggies(board, movingVeggies):
    if DEBUG: print("moveVeggies")
    # movingVeggies is a list of dicts with keys x, y, direction, imageNum
    for veggie in movingVeggies:
        if veggie['y'] != HIDDEN_ROW:
            board[veggie['x']][veggie['y']] = EMPTY_SPACE
            movex = 0
            movey = 0
            if veggie['direction'] == LEFT:
                movex = -1
            elif veggie['direction'] == RIGHT:
                movex = 1
            elif veggie['direction'] == DOWN:
                movey = 1
            elif veggie['direction'] == UP:
                movey = -1
            board[veggie['x'] + movex][veggie['y'] + movey] = veggie['imageNum']
        else:
            # veggie is located above the board (where new veggies come from)
            board[veggie['x']][0] = veggie['imageNum'] # move to top row


def fillBoardAndAnimate(board, points, speed=MOVE_RATE):
    if DEBUG: print("fillBoardAndAnimate")
    dropSlots = getDropSlots(board)
    while dropSlots != [[]] * BOARD_WIDTH:
        # do the dropping animation as long as there are more veggies to drop
        movingVeggies = getDroppingVeggies(board)
        for x in range(len(dropSlots)):
            if len(dropSlots[x]) != 0:
                # cause the lowest veggie in each slot to begin moving in the DOWN direction
                movingVeggies.append({'imageNum': dropSlots[x][0], 'x': x, 'y': HIDDEN_ROW, 'direction': DOWN})

        boardCopy = getBoardCopyMinusVeggies(board, movingVeggies)
        animateMovingVeggies(boardCopy, movingVeggies, points, speed)
        moveVeggies(board, movingVeggies)

        # Make the next row of veggies from the drop slots
        # the lowest by deleting the previous lowest veggies.
        for x in range(len(dropSlots)):
            if len(dropSlots[x]) == 0:
                continue
            board[x][0] = dropSlots[x][0]
            del dropSlots[x][0]


def checkForVeggieClick(pos):
    # See if the mouse click was on the board
    for x in range(BOARD_WIDTH):
        for y in range(BOARD_HEIGHT):
            if boardRects[x][y].collidepoint(pos[0], pos[1]):
                return {'x': x, 'y': y}
    return None # Click was not on the board.


def drawBoard(board):
    for x in range(BOARD_WIDTH):
        for y in range(BOARD_HEIGHT):
            pygame.draw.rect(gameWindow, GRID_COLOR, boardRects[x][y], 1)
            veggieToDraw = board[x][y]
            if draggingPosition != None:
                #print ("Dragging...")
                if ((x == draggingVeggie['x']) and (y == draggingVeggie['y'])):
                    # Drag the image with the mouse
                    if veggieToDraw != EMPTY_SPACE:
                        #gameWindow.blit(IMAGES[veggieToDraw], [pygame.mouse.get_pos[0], pygame.mouse.get_pos[1]])
                        #print (pygame.mouse.get_pos())
                        mouse_pos = pygame.mouse.get_pos()
                        veg_item  = boardRects[x][y]
                        gameWindow.blit(IMAGES[veggieToDraw], [mouse_pos[0] - 32, mouse_pos[1] - 32])
                else:
                    if veggieToDraw != EMPTY_SPACE:
                        gameWindow.blit(IMAGES[veggieToDraw], boardRects[x][y])
            else:
                if veggieToDraw != EMPTY_SPACE:
                    gameWindow.blit(IMAGES[veggieToDraw], boardRects[x][y])


def getBoardCopyMinusVeggies(board, veggies):
    # Creates and returns a copy of the passed board data structure,
    # with the veggies in the "veggies" list removed from it.
    #
    # Veggies is a list of dicts, with keys x, y, direction, imageNum

    boardCopy = copy.deepcopy(board)

    # Remove some of the veggies from this board data structure copy.
    for veggie in veggies:
        if veggie['y'] != HIDDEN_ROW:
            boardCopy[veggie['x']][veggie['y']] = EMPTY_SPACE
    return boardCopy


def drawScore(score):
    global turn
    if turn is None: turn = 0
    scoreImg = mainFont.render("Score: " + str(score) + "   Turn: " + str(turn), 1, SCORE_COLOR)
    scoreRect = scoreImg.get_rect()
    scoreRect.bottomleft = (10, WINDOW_HEIGHT - 6)
    gameWindow.blit(scoreImg, scoreRect)


if __name__ == '__main__':
    main()
