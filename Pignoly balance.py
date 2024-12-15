from core import Entity,Game,GameStat,getNIndexesRandomly,ge
from faces import addSpellByString
import faces
from random import randint
import numpy as np
import itertools
import multiprocessing as mp

# UPGRADE IS NOT IMPLEMENTED

def getListWithMultiplicity(faces, multi):
    out = []
    for k in range(len(faces)):
        out  += [faces[k]]*multi[k]
    return out

level1Faces =        ["Attack2","Heal1","Sweep1","Fireball1","Armor2"]
level1multiplicity = [3        ,1      ,1       ,1          ,2       ]
level1FacesWithMult = getListWithMultiplicity(level1Faces,level1multiplicity)

level2Faces =        ["Attack4","Heal3","Sweep2","Armor6","Concentration","Fireball3"]
level2multiplicity = [3       ,1      ,2       ,2       ,2              ,2            ]
level2FacesWithMult = getListWithMultiplicity(level2Faces,level2multiplicity)

level3Faces =        ["Attack6","Fireball5","Sweep4"]
level3multiplicity = [3       ,1           ,2       ]
level3FacesWithMult = getListWithMultiplicity(level3Faces,level3multiplicity)
classFaces = ["Tank", "Vampire", "King", "Paladin", "Lich"]

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

def preparePlayerForBattle(player, hp, team):
    player.resetEffects()
    player.hp = hp
    player.initialHp = hp
    player.team=team
    player.restoreFaces()

def battlePlayers(hp, players, minNbPlayerPerSide, maxNbPlayerPerSide, maxTime_min):
    nbPlayers = len(players)
    matchPlayed = [0]*nbPlayers
    wins = [0]*nbPlayers
    nbOfThrows = [] # A list per numberOfPlayerPer side containing a list of the number of throws per match

    nbIters = nbPlayers*300
    nbUnfinishable = 0
    for nbPlayerPerSide in range(minNbPlayerPerSide,maxNbPlayerPerSide+1):
        nbOfThrows.append([])
        for i in range(nbIters):
            if i%10000 ==0:
                print(f"{i/nbIters*100:.2f}%")
            playerIndexes = getNIndexesRandomly(players,2*nbPlayerPerSide,True)
            ok = battleOnce(hp, players, playerIndexes, maxTime_min, nbOfThrows, matchPlayed, wins)
            if not ok:
                nbUnfinishable +=1

    print(nbUnfinishable, " unfinishables")
    
    return matchPlayed,wins,nbOfThrows

def battleOnce(hp, players, playerIndexes, maxTime_min, nbOfThrows, matchPlayed, wins):
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
    nbOfThrows[-1].append(gs.nbThrows)
    ge.print("")
    ge.set_show_prints(False)

    if g.winningTeam() is not None:
        for k in range(2*nbPlayerPerSide):
            matchPlayed[playerIndexes[k]] += 1 # Si personne n'a gagné, on ne compte pas la partie
        teamAWon = g.winningTeam() == teamA[0].team
        if teamAWon:
            for k in range(nbPlayerPerSide):
                wins[playerIndexes[k]] += 1
        else:
            for k in range(nbPlayerPerSide,2*nbPlayerPerSide):
                wins[playerIndexes[k]] += 1
        return True
    else:
        return False
    
def battlePlayersOnPredefinedMatchs(hp, players, playerIndexesArray, maxTime_min, matchPlayed, wins): # Does not support nb of throws stat
    # As a process have its own separate memory, players are copied. There is no risk of race conditions
    nbPlayers = len(players)
    localMatchPlayed = [0]*nbPlayers
    localWins = [0]*nbPlayers
    localNbOfThrows = [[]] # Dummy array -> will not use
    i = 0
    for playerIndexes in playerIndexesArray:
        if i%1000 == 0:
            print(f"{i}/{len(playerIndexesArray)}")
        battleOnce(hp, players, playerIndexes, maxTime_min, localNbOfThrows, localMatchPlayed, localWins)
        i += 1
    
    for k in range(nbPlayers):
        matchPlayed[k] += localMatchPlayed[k]
        wins[k] += localWins[k]


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


def battlePlayersMultiproc(hp, players, minNbPlayerPerSide, maxNbPlayerPerSide, maxTime_min):
    """ Does not count nb of throws"""

    nbPlayers = len(players)

    manager = mp.Manager()
    matchPlayed = manager.list([0]*nbPlayers)
    wins = manager.list([0]*nbPlayers)
   

    nbIters = nbPlayers*300
    matches = []
    for nbPlayerPerSide in range(minNbPlayerPerSide,maxNbPlayerPerSide+1):
        matches += generate_matches(players, nbPlayerPerSide, nbIters)
    
    proc = 8
    matchBatches = divide_matches(matches, proc)
    args = [ (hp, players, matchBatches[i], maxTime_min, matchPlayed, wins) for i in range(proc) ]

    with mp.Pool(proc) as pool:
        pool.map(workerWrapper, args)
    
    return list(matchPlayed),list(wins),[[]]


def giveWinrateOfEveryFace(players, matchPlayed, wins):
    # On compte combien de fois un spell s'est retrouvé sur le dé du vainqueur
    # Problème, certains spells sont moins fréquent que d'autres donc il faut pondérer
    # On crée un dictionnaire ou pour chaque spell on stock un couple [win, matchPlayed]
    dico = {}
    for k in range(len(players)):
        for face in players[k].faces:
            if not face.faceName in dico.keys():
                dico.update({face.faceName : [0,0]})
            dico[face.faceName][0] += wins[k]
            dico[face.faceName][1] += matchPlayed[k]

    results = []
    for k in dico.keys():
        if dico[k][1]>0:
            results.append((k,dico[k][0]/dico[k][1]))
    def hasBetterWinrate(a,b):
        return a[1] - b[1]
    results = sorted(results, key = cmp_to_key(hasBetterWinrate),reverse=True)

    for cl in range(4):
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


from functools import cmp_to_key
if __name__ == "__main__":
    Nmax = nbOfDifferentDices1123CF
    hp = 20

    minPlayersPerSide = 1
    maxPlayersPerSide = 3

    players = createNrandomPlayers(hp,Nmax//2,"F112CU")

    # matchPlayed,wins,nbThrows = battlePlayers(hp,players,minPlayersPerSide,maxPlayersPerSide,60) # => 9 minutes

    matchPlayed,wins,nbThrows = battlePlayersMultiproc(hp,players,minPlayersPerSide,maxPlayersPerSide,60) # => 3 minutes



    #giveWinrateOfEveryPlayer(players,matchPlayed,wins)
    giveWinrateOfEveryFace(players,matchPlayed,wins)
    #analyseGameLength(nbThrows,minPlays,maxPlays)