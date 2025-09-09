from core import Entity,Game,getNIndexesRandomly,ge
from faces import addSpellByString
import faces
from random import randint
import multiprocessing as mp
import cProfile
import os
from rules import Deck

def createPlayer(hp, name, team, dice):
    p = Entity(hp,name,team)
    for k,faceName in enumerate(dice):
        addSpellByString(p,faceName,Deck.getTier(faceName))
    return p

def createRandomPlayer(hp, name, team, repartition : str):
    """
        1 - Tier 1
        2 - Tier 2
        3 - Tier 3
        4 - Tier 4
        F - Fail
        C - Class
        U - Upgrade
    """
    nbLevel1 = repartition.count("1")
    nbLevel2 = repartition.count("2")
    nbLevel3 = repartition.count("3")
    nbLevel4 = repartition.count("4")
    nbClass = repartition.count("C")
    nbPerTier = [nbLevel1,nbLevel2,nbLevel3,nbLevel4,nbClass] #classes is counted as tier 4

    nbFail = repartition.count("F")
    nbUpgrade = repartition.count("U")

    p = Entity(hp,name,team)
    for tierIndex in [4,0,1,2,3]: #Start with class
        facesWithMult = Deck.getFacesWithMult(tierIndex+1)
        faceIndexes = getNIndexesRandomly(facesWithMult, nbPerTier[tierIndex], True)
        for i in faceIndexes:
            addSpellByString(p, facesWithMult[i],tierIndex+1)
    
    for i in range(nbFail):
        p.faces.append(faces.Fail(p))
    
    for i in range(nbUpgrade):
        p.faces.append(faces.Upgrade(p))
    
    p.backupFaces()
    return p

def createNrandomPlayers(hp, N,repartition):
    players = []
    for k in range(N):
        players.append(createRandomPlayer(hp,"p"+str(k),0,repartition))
    return players

def preparePlayerForBattle(player : Entity, hp, team):
    """ This should be called to allow a player to play another game """
    player.resetEffects()
    player.restoreHP(hp)
    player.team=team
    player.restoreFaces()
    player.bombs = 0
    player.poisons = 0


def battleOnce(hp, players, playerIndexes, maxTime_min, dictOfSpellWinrate, matchTimes_s):
    """ Make the indexed player fight a match. updates spell winrate and append the time taken for the match """
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

    if randint(0,100000) == -1: #une chance sur N que la partie soit affichée
        ge.set_show_prints(True)

    ge.print("\nNew match\n")
    g.runUntilWinner(maxTime_min)
    ge.print("")
    #ge.set_show_prints(False)

    updateDictOfSpellWinrate(g, dictOfSpellWinrate)
    matchTimes_s.append((nbPlayerPerSide, g.getMatchTime_s()))
    
def battlePlayersOnPredefinedMatchs(hp, players, playerIndexesArray, maxTime_min, dictOfSpellWinrate, matchTimes_s):
    # As a process have its own separate memory, players are copied. There is no risk of race conditions
    # This function will be called multiple times by different threads, on different matches
    nbPlayers = len(players)
    localdictOfSpellWinrate = {}
    localmatchTimes_s = []
    i = 0
    for playerIndexes in playerIndexesArray:
        if i%1000 == 0:
            print(f"{i}/{len(playerIndexesArray)}")
        battleOnce(hp, players, playerIndexes, maxTime_min, localdictOfSpellWinrate, localmatchTimes_s)
        i += 1
    
    for k in localdictOfSpellWinrate.keys():
        if not k in dictOfSpellWinrate.keys():
            print(f"dictOfSpellWinrate does not have key {k}")
            dictOfSpellWinrate.update({k: [0,0]})
        dictOfSpellWinrate[k][0] += localdictOfSpellWinrate[k][0]
        dictOfSpellWinrate[k][1] += localdictOfSpellWinrate[k][1]
    
    matchTimes_s += localmatchTimes_s


def generate_matches(players, minNbPlayerPerSide, maxNbPlayerPerSide, nbMatchesPerNbOfPlayers):
    """Generate a list of matches, each match is a tuple of player indexes."""
    matchesByNbOfPlayers = []
    # generate matches for all number of players per matches
    for nbPlayerPerSide in range(minNbPlayerPerSide, maxNbPlayerPerSide+1):
        matchesForThisNbOfPlayers = []
        for _ in range(nbMatchesPerNbOfPlayers):
            playerIndexes = getNIndexesRandomly(players, 2 * nbPlayerPerSide, True)
            matchesForThisNbOfPlayers.append(playerIndexes)
        matchesByNbOfPlayers.append(matchesForThisNbOfPlayers)
    
    # Flatten the array by interleaving elements
    # interleaving the elements to avoid having all the longest matches stacked at the end, and the simplest at the front
    nbCategories = maxNbPlayerPerSide-minNbPlayerPerSide+1
    totalNbOfMatchs = nbMatchesPerNbOfPlayers*nbCategories
    matches = [matchesByNbOfPlayers[i%nbCategories][i//nbCategories] for i in range(totalNbOfMatchs)]

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
    print("Worker finished")

def profilingWorkerWrapper(args):
    """Wrapper to profile the worker."""
    profiler = cProfile.Profile()
    profiler.enable()

    workerWrapper(args)  # Call the actual worker function

    profiler.disable()
    profiler.dump_stats(f"worker_profile_{os.getpid()}.prof")

def battlePlayersMultiproc(hp, players, minNbPlayerPerSide, maxNbPlayerPerSide, maxTime_min):
    nbPlayers = len(players)

    manager = mp.Manager()
    dictOfSpellWinrate = manager.dict()
    matchTimes_s = manager.list()

    for spell in Deck.allSpellsAndClass:
        dictOfSpellWinrate[spell] = manager.list([0,0])

    nbIters = nbPlayers*200
    matches = generate_matches(players, minNbPlayerPerSide, maxNbPlayerPerSide, nbIters)

    proc = 7

    matchBatches = divide_matches(matches, proc)
    args = [ (hp, players, matchBatches[i], maxTime_min, dictOfSpellWinrate, matchTimes_s) for i in range(proc) ]

    with mp.Pool(proc) as pool:
        pool.map(workerWrapper, args)
        #pool.map(profilingWorkerWrapper, args)

    for spell in Deck.allSpellsAndClass:
        dictOfSpellWinrate[spell] = list(dictOfSpellWinrate[spell])
    
    return dict(dictOfSpellWinrate), list(matchTimes_s)

def battlePlayers(hp, players, minNbPlayerPerSide, maxNbPlayerPerSide, maxTime_min):
    nbPlayers = len(players)

    dictOfSpellWinrate = {}
    matchTimes_s = []

    for spell in Deck.allSpellsAndClass:
        dictOfSpellWinrate[spell] = [0,0]

    nbIters = nbPlayers*200
    matches = generate_matches(players, minNbPlayerPerSide, maxNbPlayerPerSide, nbIters)

    battlePlayersOnPredefinedMatchs(hp, players, matches, maxTime_min, dictOfSpellWinrate, matchTimes_s)
    
    return dictOfSpellWinrate, matchTimes_s

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

    def fillWithBlanks(originalStr, width):
        return originalStr+" "*(width-len(originalStr))
    
    maxWidth = 0
    for spell in Deck.allSpellsAndClass:
        if len(spell) > maxWidth:
            maxWidth =  len(spell)

    for tier in [1,2,3,4,5]:
        print("")
        for r in results:
            if r[0] in Deck.getFaces(tier):
                if tier == 4:
                    print("[Class] ",end="")
                else:
                    print(f"[Tier{tier}] ",end="")
                print(f"{fillWithBlanks(r[0], maxWidth)} winrate : {r[1]*100:.0f}%")
            

import matplotlib.pyplot as plt
def analyseGameLength(matchTimes_s, minPlayer, maxPlayer):
    for k in range(minPlayer,maxPlayer+1):
        secondsPerThrow = 10
        times = [nbP_time[1]/60 for nbP_time in matchTimes_s if nbP_time[0] == k]
        plt.hist(times, bins=120, edgecolor='black', rwidth=0.8)

        # Ajout des labels
        plt.xlabel('Temps (min)')
        plt.ylabel('Fréquence (nb parties)')
        plt.title(f'Temps de jeu a {k} joueurs par équipe')

        # Affichage
        plt.show()


def testSpecificMatchup():
    ge.set_show_prints(True)
    hp = 20
    dice1 = ["Tank", "Attack2", "Attack4", "Concentration","Poison","Revive", "Sweep1"]
    player1 = createPlayer(40, "p1", 1, dice1)

    dice2 = ["Thief", "Attack2", "Attack4", "Concentration","Poison","Bomb", "Sweep1"]
    player2 = createPlayer(20, "p2", 1, dice2)

    dice3 = ["Lich", "Attack2", "Attack4", "Armor2","Poison","Concentration", "Sweep1"]
    player3 = createPlayer(20, "p3", 2, dice3)

    dice4 = ["Judge", "Attack2", "Attack4", "Armor2","Concentration","Mummyfy", "Sweep1"]
    player4 = createPlayer(40, "p4", 2, dice4)
    # Upgrade need a specific call (cannot init by string)
    
    
    game = Game()
    game.entities.append(player1)
    game.entities.append(player2)
    game.entities.append(player3)
    game.entities.append(player4)
    game.runUntilWinner(60)
    assert False, "end"


from functools import cmp_to_key
if __name__ == "__main__":
    # profiler = cProfile.Profile()
    # profiler.enable()
    # testSpecificMatchup()
    
    
    Nmax = Deck.nbOfDifferentDices1123CF
    hp = 20

    minPlayersPerSide = 3
    maxPlayersPerSide = 3

    players = createNrandomPlayers(hp,Nmax//2,"F112CU")
    # players = createNrandomPlayers(hp,Nmax//2,"F124CU") # Test tier 4
    #players = createNrandomPlayers(hp,Nmax,"C11223") # No upgrade.
    
    dictOfSpellWinrate, matchTimes_s = battlePlayersMultiproc(hp,players,minPlayersPerSide,maxPlayersPerSide,60) 
    #dictOfSpellWinrate, matchTimes_s = battlePlayers(hp,players,minPlayersPerSide,maxPlayersPerSide,60) 
    #ge.set_show_prints(True)

    # profiler.disable()
    # profiler.dump_stats("main_profile.prof")

    print("Finished battles")
    giveWinrateOfEveryFace(dictOfSpellWinrate)
    analyseGameLength(matchTimes_s,minPlayersPerSide,maxPlayersPerSide)