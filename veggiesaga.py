# Veggie Saga             #
# A healthier way to play #

# Requires pygame.        #

"""
This program has "veggie data structures", which are basically dictionaries
with the following keys:
  'x' and 'y' - The location of the veggie on the board. 0,0 is the top left.
                There is also a ROWABOVEBOARD row that 'y' can be set to,
                to indicate that it is above the board.
  'direction' - one of the four constant variables UP, DOWN, LEFT, RIGHT.
                This is the direction the veggie is moving.
  'imageNum'  - The integer index into IMAGES to denote which image
                this veggie uses.
"""

import random, time, pygame, sys, copy
from pygame.locals import *

FPS = 30 # Screen refresh rate (in Frames Per Second).
GAME_WINDOW_WIDTH = 800  # Width of game window (px).
GAME_WINDOW_HEIGHT = 600 # Height of game window (px).

BOARD_WIDTH = 8 # Number of columns.
BOARD_HEIGHT = 8 # Number of rows.
IMAGE_SIZE = 64 # Tile size (px).

MAX_GAME_LENGTH = 10000 # The number of moves until a game times out.

# Note that the game looks for PNG images for each veggie using the
# name format "veggie#.png" (# from 0 to N-1).
NUM_VEGGIES = 7 # Number of veggie types.
assert NUM_VEGGIES >= 5 # The game needs at least 5 veggies

#xxx
MOVE_RATE = 10 # 1 to 100, larger num means faster animations
DEDUCTSPEED = 0.8 # reduces score by 1 point every DEDUCTSPEED seconds.

#             R    G    B
PURPLE    = (255,   0, 255)
LIGHTBLUE = (170, 190, 255)
BLUE      = (  0,   0, 255)
RED       = (255, 100, 100)
BLACK     = (  0,   0,   0)
BROWN     = ( 85,  65,   0)

# Display color constants
HIGHLIGHTCOLOR = RED # color of the selected veggie's border
BGCOLOR = BLACK # background color on the screen
GRIDCOLOR = BLUE # color of the game board
GAMEOVERCOLOR = RED # color of the "Game over" text.
GAMEOVERBGCOLOR = BLACK # background color of the "Game over" text.
SCORECOLOR = BROWN # color of the text for the player's score

# The amount of space to the sides of the board to the edge of the window
# is used several times, so calculate it once here and store in variables.
XMARGIN = int((GAME_WINDOW_WIDTH - IMAGE_SIZE * BOARD_WIDTH) / 2)
YMARGIN = int((GAME_WINDOW_HEIGHT - IMAGE_SIZE * BOARD_HEIGHT) / 2)

# constants for direction values
UP = 'up'
DOWN = 'down'
LEFT = 'left'
RIGHT = 'right'

EMPTY_SPACE = -1 # an arbitrary, nonpositive value
ROWABOVEBOARD = 'row above board' # an arbitrary, noninteger value

def main():
    global FPSCLOCK, DISPLAYSURF, IMAGES, BASICFONT, SMALLFONT, BOARDRECTS, BG_IMAGE, DRAGGING_POS, DRAGGING_VEG

    # Initial set up.
    pygame.init()
    FPSCLOCK = pygame.time.Clock()
    DISPLAYSURF = pygame.display.set_mode((GAME_WINDOW_WIDTH, GAME_WINDOW_HEIGHT))
    pygame.display.set_caption('Veggie Saga')
    BASICFONT = pygame.font.Font('freesansbold.ttf', 72)
    SMALLFONT = pygame.font.Font('freesansbold.ttf', 36) # Used for Game Over screen.
    BG_IMAGE        = pygame.image.load("background.jpg").convert()
    DRAGGING_POS = None

    # Load the images
    IMAGES = []
    for i in range(1, NUM_VEGGIES + 1):
        img = pygame.image.load('veggie%s.png' % i)
        if img.get_size() != (IMAGE_SIZE, IMAGE_SIZE):
            img = pygame.transform.smoothscale(img, (IMAGE_SIZE, IMAGE_SIZE))
        IMAGES.append(img)

    # Create pygame.Rect objects for each board space to
    # do board-coordinate-to-pixel-coordinate conversions.
    BOARDRECTS = []
    for x in range(BOARD_WIDTH):
        BOARDRECTS.append([])
        for y in range(BOARD_HEIGHT):
            r = pygame.Rect((XMARGIN + (x * IMAGE_SIZE),
                             YMARGIN + (y * IMAGE_SIZE),
                             IMAGE_SIZE,
                             IMAGE_SIZE))
            BOARDRECTS[x].append(r)

    while True:
        runGame()


def runGame():
    # Plays through a single game. When the game is over, this function returns.
    global DRAGGING_POS, DRAGGING_VEG
    
    # Initialize the board.
    gameBoard               = []
    for x in range(BOARD_WIDTH):
        gameBoard.append([EMPTY_SPACE] * BOARD_HEIGHT)

    # initialize variables for the start of a new game
    score                   = 0
    gameIsOver              = False
    DRAGGING_POS            = None
    lastMouseDownX          = None
    lastMouseDownY          = None
    lastScoreDeduction      = time.time()
    firstSelectedVeggie     = None
    clickContinueTextSurf   = None

    # Populate and display the initial veggies.
    fillBoardAndAnimate(gameBoard, [], score)

    while True: # main game loop
        clickedSpace = None
        for event in pygame.event.get(): # event handling loop
            if event.type == QUIT or (event.type == KEYUP and event.key == K_ESCAPE):
                pygame.quit()
                sys.exit()
            elif event.type == KEYUP and event.key == K_BACKSPACE:
                return # start a new game

            elif event.type == MOUSEBUTTONUP:
                DRAGGING_POS = None
                
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
                DRAGGING_POS = event.pos
                DRAGGING_VEG = checkForVeggieClick(event.pos)
                
                # Uncomment to highlight the veggie square while dragging.
                #firstSelectedVeggie = checkForVeggieClick((lastMouseDownX, lastMouseDownY))

        if clickedSpace and not firstSelectedVeggie:
            # This was the first veggie clicked on.
            firstSelectedVeggie = clickedSpace
        elif clickedSpace and firstSelectedVeggie:
            # Two veggies have been clicked on and selected. Swap the veggies.
            firstSwappingVeggie, secondSwappingVeggie = getSwappingVeggies(gameBoard, firstSelectedVeggie, clickedSpace)
            if firstSwappingVeggie == None and secondSwappingVeggie == None:
                # If both are None, then the veggies were not adjacent
                firstSelectedVeggie = None # deselect the first veggie
                continue

            # Show the swap animation on the screen.
            boardCopy = getBoardCopyMinusVeggies(gameBoard, (firstSwappingVeggie, secondSwappingVeggie))
            animateMovingVeggies(boardCopy, [firstSwappingVeggie, secondSwappingVeggie], [], score)

            # Swap the veggies in the board data structure.
            gameBoard[firstSwappingVeggie['x']][firstSwappingVeggie['y']] = secondSwappingVeggie['imageNum']
            gameBoard[secondSwappingVeggie['x']][secondSwappingVeggie['y']] = firstSwappingVeggie['imageNum']

            # See if this is a matching move.
            matchedVeggies = findMatchingVeggies(gameBoard)
            if matchedVeggies == []:
                # Was not a matching move; swap the veggies back
                animateMovingVeggies(boardCopy, [firstSwappingVeggie, secondSwappingVeggie], [], score)
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
                                       'x': veggie[0] * IMAGE_SIZE + XMARGIN,
                                       'y': veggie[1] * IMAGE_SIZE + YMARGIN})
                    score += scoreAdd

                    # Drop the new veggies.
                    fillBoardAndAnimate(gameBoard, points, score)

                    # Check if there are any new matches.
                    matchedVeggies = findMatchingVeggies(gameBoard)
            firstSelectedVeggie = None

            if not canMakeMove(gameBoard):
                gameIsOver = True

        # Draw the board.
        #DISPLAYSURF.fill(BGCOLOR) # Uncomment to draw a black background.
        DISPLAYSURF.blit(BG_IMAGE, [0, 0]) # Draw the background.
        drawBoard(gameBoard)
        
        if firstSelectedVeggie != None:
            highlightSpace(firstSelectedVeggie['x'], firstSelectedVeggie['y'])
            
        if gameIsOver:
            if clickContinueTextSurf == None:
                # Only render the text once. In future iterations, just
                # use the Surface object already in clickContinueTextSurf
                clickContinueTextSurf = SMALLFONT.render('Final Score: %s (Click to continue)' % (score), 1, GAMEOVERCOLOR, GAMEOVERBGCOLOR)
                clickContinueTextRect = clickContinueTextSurf.get_rect()
                clickContinueTextRect.center = int(GAME_WINDOW_WIDTH / 2), int(GAME_WINDOW_HEIGHT / 2)
            DISPLAYSURF.blit(clickContinueTextSurf, clickContinueTextRect)
        elif score > 0 and time.time() - lastScoreDeduction > DEDUCTSPEED:
            # score drops over time
            score -= 1
            lastScoreDeduction = time.time()
        drawScore(score)
        pygame.display.update()
        FPSCLOCK.tick(FPS)


def getSwappingVeggies(board, firstXY, secondXY):
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


def canMakeMove(board):
    # Return True if the board is in a state where a matching
    # move can be made on it. Otherwise return False.

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
    if basey == ROWABOVEBOARD:
        basey = -1

    pixelx = XMARGIN + (basex * IMAGE_SIZE)
    pixely = YMARGIN + (basey * IMAGE_SIZE)
    r = pygame.Rect( (pixelx + movex, pixely + movey, IMAGE_SIZE, IMAGE_SIZE) )
    DISPLAYSURF.blit(IMAGES[veggie['imageNum']], r)


def pullDownAllVeggies(board):
    # pulls down veggies on the board to the bottom to fill in any gaps
    for x in range(BOARD_WIDTH):
        veggiesInColumn = []
        for y in range(BOARD_HEIGHT):
            if board[x][y] != EMPTY_SPACE:
                veggiesInColumn.append(board[x][y])
        board[x] = ([EMPTY_SPACE] * (BOARD_HEIGHT - len(veggiesInColumn))) + veggiesInColumn


def getVeggieAt(board, x, y):
    if x < 0 or y < 0 or x >= BOARD_WIDTH or y >= BOARD_HEIGHT:
        return None
    else:
        return board[x][y]


def getDropSlots(board):
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
    pygame.draw.rect(DISPLAYSURF, HIGHLIGHTCOLOR, BOARDRECTS[x][y], 4)


def getDroppingVeggies(board):
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


def animateMovingVeggies(board, veggies, pointsText, score, speed=MOVE_RATE):
    # pointsText is a dictionary with keys 'x', 'y', and 'points'
    progress = 0 # progress at 0 represents beginning, 100 means finished.
    while progress < 100: # animation loop
        DISPLAYSURF.blit(BG_IMAGE, [0, 0])
        drawBoard(board)
        for veggie in veggies: # Draw each veggie.
            drawMovingVeggie(veggie, progress)
        drawScore(score)
        for pointText in pointsText:
            pointsSurf = BASICFONT.render("+" + str(pointText['points']) + "!", 1, PURPLE)
            pointsRect = pointsSurf.get_rect()
            pointsRect.center = (pointText['x'], pointText['y'])
            DISPLAYSURF.blit(pointsSurf, pointsRect)

        pygame.display.update()
        FPSCLOCK.tick(FPS)
        progress += speed # progress the animation a little bit more for the next frame


def moveVeggies(board, movingVeggies):
    # movingVeggies is a list of dicts with keys x, y, direction, imageNum
    for veggie in movingVeggies:
        if veggie['y'] != ROWABOVEBOARD:
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


def fillBoardAndAnimate(board, points, score):
    dropSlots = getDropSlots(board)
    while dropSlots != [[]] * BOARD_WIDTH:
        # do the dropping animation as long as there are more veggies to drop
        movingVeggies = getDroppingVeggies(board)
        for x in range(len(dropSlots)):
            if len(dropSlots[x]) != 0:
                # cause the lowest veggie in each slot to begin moving in the DOWN direction
                movingVeggies.append({'imageNum': dropSlots[x][0], 'x': x, 'y': ROWABOVEBOARD, 'direction': DOWN})

        boardCopy = getBoardCopyMinusVeggies(board, movingVeggies)
        animateMovingVeggies(boardCopy, movingVeggies, points, score, MOVE_RATE * 3)
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
            if BOARDRECTS[x][y].collidepoint(pos[0], pos[1]):
                return {'x': x, 'y': y}
    return None # Click was not on the board.


def drawBoard(board):
    for x in range(BOARD_WIDTH):
        for y in range(BOARD_HEIGHT):
            pygame.draw.rect(DISPLAYSURF, GRIDCOLOR, BOARDRECTS[x][y], 1)
            veggieToDraw = board[x][y]
            if DRAGGING_POS != None:
                #print ("Dragging...")
                if ((x == DRAGGING_VEG['x']) and (y == DRAGGING_VEG['y'])):
                    # Drag the image with the mouse
                    if veggieToDraw != EMPTY_SPACE:
                        #DISPLAYSURF.blit(IMAGES[veggieToDraw], [pygame.mouse.get_pos[0], pygame.mouse.get_pos[1]])
                        #print (pygame.mouse.get_pos())
                        mouse_pos = pygame.mouse.get_pos()
                        veg_item  = BOARDRECTS[x][y]
                        DISPLAYSURF.blit(IMAGES[veggieToDraw], [mouse_pos[0] - 32, mouse_pos[1] - 32])
                else:
                    if veggieToDraw != EMPTY_SPACE:
                        DISPLAYSURF.blit(IMAGES[veggieToDraw], BOARDRECTS[x][y])
            else:
                if veggieToDraw != EMPTY_SPACE:
                    DISPLAYSURF.blit(IMAGES[veggieToDraw], BOARDRECTS[x][y])


def getBoardCopyMinusVeggies(board, veggies):
    # Creates and returns a copy of the passed board data structure,
    # with the veggies in the "veggies" list removed from it.
    #
    # Veggies is a list of dicts, with keys x, y, direction, imageNum

    boardCopy = copy.deepcopy(board)

    # Remove some of the veggies from this board data structure copy.
    for veggie in veggies:
        if veggie['y'] != ROWABOVEBOARD:
            boardCopy[veggie['x']][veggie['y']] = EMPTY_SPACE
    return boardCopy


def drawScore(score):
    scoreImg = BASICFONT.render(str(score), 1, SCORECOLOR)
    scoreRect = scoreImg.get_rect()
    scoreRect.bottomleft = (10, GAME_WINDOW_HEIGHT - 6)
    DISPLAYSURF.blit(scoreImg, scoreRect)


if __name__ == '__main__':
    main()
