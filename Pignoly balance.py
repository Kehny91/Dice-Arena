from core import Entity,Game,GameStat,getNIndexesRandomly,ge
from faces import addSpellByString
import faces
from random import randint
import numpy as np
import itertools
import multiprocessing as mp
import cProfile
import os

# UPGRADE IS NOT IMPLEMENTED

def getListWithMultiplicity(faces, multi):
    out = []
    for k in range(len(faces)):
        out  += [faces[k]]*multi[k]
    return out

level1Faces =        ["Attack2","Heal1","Sweep1","Fireball1","Armor2"]
level1multiplicity = [3        ,1      ,1       ,1          ,2       ]
level1FacesWithMult = getListWithMultiplicity(level1Faces,level1multiplicity)

level2Faces =        ["Attack4","Heal3","Sweep2","Armor6","Concentration","Fireball3", "Poison", "Bomb"]
level2multiplicity = [3       ,1      ,2       ,2       ,2              ,2            ,2       ,2      ]
level2FacesWithMult = getListWithMultiplicity(level2Faces,level2multiplicity)

level3Faces =        ["Attack6","Fireball5","Sweep4"]
level3multiplicity = [3       ,1           ,2       ]
level3FacesWithMult = getListWithMultiplicity(level3Faces,level3multiplicity)
classFaces = ["Tank", "Vampire", "King", "Paladin", "Lich"]

allSpellsAndClass = level1Faces + level2Faces + level3Faces + classFaces

def getTier(faceName):
    if faceName in level1Faces:
        return 1
    elif faceName in level2Faces:
        return 2
    elif faceName in level3Faces:
        return 3
    else:
        assert False, f"unknown tier for {faceName}"

nbOfDifferentDices1123CF = sum(level1multiplicity)*sum(level2multiplicity)*sum(level3multiplicity)*len(classFaces)

def createPlayer(hp, name, team, dice, tierlist):
    p = Entity(hp,name,team)
    for k,faceName in enumerate(dice):
        addSpellByString(p,faceName,tierlist[k])
    return p

def createRandomPlayer(hp, name, team, repartition : str):
    """
        1 - Tier 1
        2 - Tier 2
        3 - Tier 3
        F - Fail
        C - Class
        U - Upgrade
    """
    nbLevel1 = repartition.count("1")
    nbLevel2 = repartition.count("2")
    nbLevel3 = repartition.count("3")
    nbFail = repartition.count("F")
    nbClass = repartition.count("C")
    nbUpgrade = repartition.count("U")

    p = Entity(hp,name,team)
    lvl1Indexes = getNIndexesRandomly(level1FacesWithMult,nbLevel1,False)
    lvl2Indexes = getNIndexesRandomly(level2FacesWithMult,nbLevel2,False)
    lvl3Indexes = getNIndexesRandomly(level3FacesWithMult,nbLevel3,False)
    classIndex = getNIndexesRandomly(classFaces,nbClass,False)
    for i in lvl1Indexes:
        addSpellByString(p, level1FacesWithMult[i],1)
    for i in lvl2Indexes:
        addSpellByString(p, level2FacesWithMult[i],2)
    for i in lvl3Indexes:
        addSpellByString(p, level3FacesWithMult[i],3)
    for i in classIndex:
        addSpellByString(p, classFaces[i],4)
    for i in range(nbFail):
        p.faces.append(faces.Fail(p))
    for i in range(nbUpgrade):
        p.faces.append(faces.Upgrade(p,level1FacesWithMult,level2FacesWithMult,level3FacesWithMult))
    p.backupFaces()
    return p

def createNrandomPlayers(hp, N,repartition):
    players = []
    for k in range(N):
        players.append(createRandomPlayer(hp,"p"+str(k),0,repartition))
    return players

teamOne = 1
teamTwo = 2

def preparePlayerForBattle(player : Entity, hp, team):
    player.resetEffects()
    player.restoreHP(hp)
    player.team=team
    player.restoreFaces()
    player.bombs = 0
    player.poisons = 0

def battlePlayers(hp, players, minNbPlayerPerSide, maxNbPlayerPerSide, maxTime_min):
    nbPlayers = len(players)
    dictOfSpellWinrate = {}
    nbOfThrows = [] # A list per numberOfPlayerPer side containing a list of the number of throws per match

    nbIters = nbPlayers*300
    nbUnfinishable = 0
    for nbPlayerPerSide in range(minNbPlayerPerSide,maxNbPlayerPerSide+1):
        nbOfThrows.append([])
        for i in range(nbIters):
            if i%100 ==0:
                print(f"{i/nbIters*100:.2f}%")
            playerIndexes = getNIndexesRandomly(players,2*nbPlayerPerSide,True)
            throws = battleOnce(hp, players, playerIndexes, maxTime_min,dictOfSpellWinrate)
            if throws>60*10/60: #TODO
                nbUnfinishable +=1

    print(nbUnfinishable, " unfinishables")
    
    return dictOfSpellWinrate,nbOfThrows

def battleOnce(hp, players, playerIndexes, maxTime_min, dictOfSpellWinrate):
    nbPlayerPerSide = len(playerIndexes)//2
    teamA = [players[playerIndexes[k]] for k in range(nbPlayerPerSide)] # first ones makes team A
    teamB = [players[playerIndexes[k]] for k in range(nbPlayerPerSide,2*nbPlayerPerSide)] # second ones makes team B
    contestants = teamA+teamB
    
    ordering = getNIndexesRandomly(contestants,2*nbPlayerPerSide,True)
    g = Game()
    for k in ordering:
        g.entities.append(contestants[k])

    for p in  teamA:
        preparePlayerForBattle(p, hp, 1)
    for p in  teamB:
        preparePlayerForBattle(p, hp, 2)

    gs = GameStat()
    if randint(0,100000) == -1: #une chance sur N que la partie soit affichée
        ge.set_show_prints(True)
    g.runUntilWinner(maxTime_min, gs)
    ge.print("")
    #ge.set_show_prints(False)

    updateDictOfSpellWinrate(g, dictOfSpellWinrate)
    return gs.nbThrows
    
def battlePlayersOnPredefinedMatchs(hp, players, playerIndexesArray, maxTime_min, dictOfSpellWinrate): # Does not support nb of throws stat
    # As a process have its own separate memory, players are copied. There is no risk of race conditions
    nbPlayers = len(players)
    localdictOfSpellWinrate = {}
    i = 0
    for playerIndexes in playerIndexesArray:
        if i%1000 == 0:
            print(f"{i}/{len(playerIndexesArray)}")
        battleOnce(hp, players, playerIndexes, maxTime_min, localdictOfSpellWinrate)
        i += 1
    
    for k in localdictOfSpellWinrate.keys():
        if not k in dictOfSpellWinrate.keys():
            print(f"dictOfSpellWinrate does not have key {k}")
            dictOfSpellWinrate.update({k: [0,0]})
        dictOfSpellWinrate[k][0] += localdictOfSpellWinrate[k][0]
        dictOfSpellWinrate[k][1] += localdictOfSpellWinrate[k][1]


def generate_matches(players, nbPlayerPerSide, nbMatches):
    """Generate a list of matches, each match is a tuple of player indexes."""
    matches = []
    for _ in range(nbMatches):
        playerIndexes = getNIndexesRandomly(players, 2 * nbPlayerPerSide, True)
        matches.append(playerIndexes)
    return matches

def divide_matches(matches, n):
    """Divide matches into n roughly equal-sized chunks."""
    chunk_size = len(matches) // n
    remainder = len(matches) % n
    chunks = []
    start = 0

    for i in range(n):
        end = start + chunk_size + (1 if i < remainder else 0)
        chunks.append(matches[start:end])
        start = end

    return chunks

def workerWrapper(args):
    battlePlayersOnPredefinedMatchs(*args)

def interleave_elements(lst, category):
    """
    Mixes a list such that grouped elements like [1, 1, 1, 1, 2, 2, 2, 2, 3, 3, 3, 3]
    are interleaved into [1, 2, 3, 1, 2, 3, 1, 2, 3, 1, 2, 3].
    """
    n = len(lst) // category  # Assuming the list can be divided into 3 equal groups
    groups = [lst[i * n: (i + 1) * n] for i in range(category)]  # Split into 3 groups
    
    result = []
    for i in range(n):
        for group in groups:
            result.append(group[i])
    return result

def profilingWorkerWrapper(args):
    """Wrapper to profile the worker."""
    profiler = cProfile.Profile()
    profiler.enable()

    workerWrapper(args)  # Call the actual worker function

    profiler.disable()
    profiler.dump_stats(f"worker_profile_{os.getpid()}.prof")

def battlePlayersMultiproc(hp, players, minNbPlayerPerSide, maxNbPlayerPerSide, maxTime_min):
    """ Does not count nb of throws"""

    nbPlayers = len(players)

    manager = mp.Manager()
    dictOfSpellWinrate = manager.dict()
    for spell in allSpellsAndClass:
        dictOfSpellWinrate[spell] = manager.list([0,0])

    nbIters = nbPlayers*300
    matches = []
    for nbPlayerPerSide in range(minNbPlayerPerSide,maxNbPlayerPerSide+1):
        matches += generate_matches(players, nbPlayerPerSide, nbIters)
    
    # interleaving the elements to avoid having all the longest matches stacked at the end, and the simplest at the front
    matches = interleave_elements(matches, maxNbPlayerPerSide-minNbPlayerPerSide +1)

    proc = 10

    matchBatches = divide_matches(matches, proc)
    args = [ (hp, players, matchBatches[i], maxTime_min, dictOfSpellWinrate) for i in range(proc) ]

    with mp.Pool(proc) as pool:
        pool.map(workerWrapper, args)
        #pool.map(profilingWorkerWrapper, args)

    for spell in allSpellsAndClass:
        dictOfSpellWinrate[spell] = list(dictOfSpellWinrate[spell])
    
    return dict(dictOfSpellWinrate),[[]]

def updateDictOfSpellWinrate(game : Game, dictOfSpellWinrate): 
    # This function must be called after each game, before restoring to initial faces.
    # For each keys, the dict contains a tuple (numberOfWins, numberOfMatchPlayed)
    nbPlayerPerSide = len(game.entities)//2
    winningTeam = game.winningTeam()
    if winningTeam is not None:    
        for player in game.entities: # Ghouls are cleared by "Game.runUntilWinner"
            for face in player.faces:
                if face.faceName != "Upgrade" and  face.faceName != "Fail":
                    if not face.faceName in dictOfSpellWinrate.keys():
                        dictOfSpellWinrate.update({face.faceName : [0,0]})
                    if player.team == winningTeam:
                        dictOfSpellWinrate[face.faceName][0] += 1
                    dictOfSpellWinrate[face.faceName][1] += 1

def giveWinrateOfEveryFace(dictOfSpellWinrate):
    results = []
    for k in dictOfSpellWinrate.keys():
        if dictOfSpellWinrate[k][1]>0:
            results.append((k,dictOfSpellWinrate[k][0]/dictOfSpellWinrate[k][1]))
    def hasBetterWinrate(a,b):
        return a[1] - b[1]
    results = sorted(results, key = cmp_to_key(hasBetterWinrate),reverse=True)

    for cl in range(4):
        print("")
        for r in results:
            if r[0] in level1Faces and cl == 0:
                print("[Tier1] ",end="")
                print(f"{r[0]} winrate : {r[1]*100:.0f}%")
            elif r[0] in level2Faces and cl == 1:
                print("[Tier2] ",end="")
                print(f"{r[0]} winrate : {r[1]*100:.0f}%")
            elif r[0] in level3Faces and cl == 2:
                print("[Tier3] ",end="")
                print(f"{r[0]} winrate : {r[1]*100:.0f}%")
            elif r[0] in classFaces and cl == 3:
                print("[Class] ",end="")
                print(f"{r[0]} winrate : {r[1]*100:.0f}%")
            

import matplotlib.pyplot as plt
def analyseGameLength(nbOfThrows, minPlayer, maxPlayer):
    for k in range(minPlayer,maxPlayer+1):
        secondsPerThrow = 10
        time = [throws*secondsPerThrow/60 for throws in nbOfThrows[k-minPlayer]]
        plt.hist(time, bins=120, edgecolor='black', rwidth=0.8)

        # Ajout des labels
        plt.xlabel('Valeurs')
        plt.ylabel('Fréquence')
        plt.title(f'Temps de jeu a {k} joueurs par équipe')

        # Affichage
        plt.show()


def testSpecificMatchup():
    ge.set_show_prints(True)
    hp = 20
    dice1 = ["King", "Attack2", "Attack4", "Armor2","Poison","Bomb"]
    dice1TierList = [4,4]+[getTier(f) for f in dice1[2:]]
    player1 = createPlayer(20, "player1", 1, dice1,dice1TierList)
    player1.faces.append(faces.Upgrade(player1,level1FacesWithMult,level2FacesWithMult,level3FacesWithMult))

    player2 = createPlayer(20, "player2", 2, dice1,dice1TierList)
    player2.faces.append(faces.Upgrade(player2,level1FacesWithMult,level2FacesWithMult,level3FacesWithMult))
    # Upgrade need a specific call (cannot init by string)
    
    
    game = Game()
    game.entities.append(player1)
    game.entities.append(player2)
    game.runUntilWinner(60)
    import time
    time.sleep(1)
    #ge.set_show_prints(False)


from functools import cmp_to_key
if __name__ == "__main__":
    profiler = cProfile.Profile()
    profiler.enable()
    #testSpecificMatchup()
    
    
    Nmax = nbOfDifferentDices1123CF
    hp = 20

    minPlayersPerSide = 1
    maxPlayersPerSide = 2

    players = createNrandomPlayers(hp,Nmax//2,"F112CU")
    
    dictOfSpellWinrate, nbThrows = battlePlayersMultiproc(hp,players,minPlayersPerSide,maxPlayersPerSide,60) # => 3 minutes
    #ge.set_show_prints(True)
    #dictOfSpellWinrate, nbThrows = battlePlayers(hp,players,minPlayersPerSide,maxPlayersPerSide,60) # => 3 minutes

    profiler.disable()
    profiler.dump_stats("main_profile.prof")

    #giveWinrateOfEveryPlayer(players,matchPlayed,wins)
    giveWinrateOfEveryFace(dictOfSpellWinrate)
    #analyseGameLength(nbThrows,minPlays,maxPlays)