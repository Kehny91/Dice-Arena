from core import Entity,Game,GameStat,getNIndexesRandomly,ge
from faces import addSpellByString
from random import randint
import numpy as np
import itertools


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


allFaces = level1Faces + level2Faces + level3Faces

def createAllLegitDices():
    out = []

    lvl1Combos = list(itertools.combinations(level1FacesWithMult,2))
    lvl2Combos = list(itertools.combinations(level2FacesWithMult,1))
    lvl3Combos = list(itertools.combinations(level3FacesWithMult,1))
    classCombo = list(itertools.combinations(classFaces,1))

    for lvl1 in lvl1Combos:
        for lvl2 in lvl2Combos:
            for lvl3 in lvl3Combos:
                for classFace in classCombo:
                    out.append(list(lvl1) + list(lvl2) + list(lvl3) + list(classFaces))

    tierList = [1,1,2,3,4]

    return out, tierList

def createLegitRandomPlayer(hp, name, team):
    p = Entity(hp,name,team)
    lvl1Indexes = getNIndexesRandomly(level1FacesWithMult,2,False)
    lvl2Indexes = getNIndexesRandomly(level2FacesWithMult,1,False)
    lvl3Indexes = getNIndexesRandomly(level3FacesWithMult,1,False)
    classIndex = getNIndexesRandomly(classFaces,1,False)
    addSpellByString(p, level1FacesWithMult[lvl1Indexes[0]],1)
    addSpellByString(p, level1FacesWithMult[lvl1Indexes[1]],1)
    addSpellByString(p, level2FacesWithMult[lvl2Indexes[0]],2)
    addSpellByString(p, level3FacesWithMult[lvl3Indexes[0]],3)
    addSpellByString(p, classFaces[classIndex[0]],4)
    addSpellByString(p, "Fail",0)
    return p

def createPlayer(hp, name, team, dice, tierlist):
    p = Entity(hp,name,team)
    for k,faceName in enumerate(dice):
        addSpellByString(p,faceName,tierlist[k])
    addSpellByString(p,"Fail",0)
    return p



teamOne = 1
teamTwo = 2

def preparePlayerForBattle(player, hp, team):
    player.resetEffects()
    player.hp = hp
    player.team=team

def createAllPossiblePlayers(hp):
    dices, tierlist = createAllLegitDices()
    nbPlayers = len(dices)
    players = []
    for k in range(nbPlayers):
        players.append(createPlayer(hp,"p"+str(k),0,dices[k], tierlist))
    return players

def createNrandomPlayers(hp, N):
    players = []
    for k in range(N):
        players.append(createLegitRandomPlayer(hp,"p"+str(k),0))
    return players

def battlePlayers(hp, players, minNbPlayerPerSide, maxNbPlayerPerSide=None):
    if maxNbPlayerPerSide is None:
        maxNbPlayerPerSide = minNbPlayerPerSide
    nbPlayers = len(players)
    matchPlayed = [0]*nbPlayers
    wins = [0]*nbPlayers

    nbIters = nbPlayers*300
    nbUnfinishable = 0
    nbOfThrows = [] # A list per numberOfPlayerPer side containing a list of the number of throws per match
    for nbPlayerPerSide in range(minNbPlayerPerSide,maxNbPlayerPerSide+1):
        nbOfThrows.append([])
        for i in range(nbIters):
            playerIndexes = getNIndexesRandomly(players,2*nbPlayerPerSide,True)
            teamA = [players[playerIndexes[k]] for k in range(nbPlayerPerSide)] # first ones makes team A
            teamB = [players[playerIndexes[k]] for k in range(nbPlayerPerSide,2*nbPlayerPerSide)] # second ones makes team B
            for p in  teamA:
                preparePlayerForBattle(p, hp, 1)
            for p in  teamB:
                preparePlayerForBattle(p, hp, 2)
            contestants = teamA+teamB
            
            ordering = getNIndexesRandomly(contestants,2*nbPlayerPerSide,True)
            g = Game()
            for k in ordering:
                g.entities.append(contestants[k])

            gm = GameStat()


            if randint(0,100000) == 0: #une chance sur N que la partie soit affichée
                ge.set_show_prints(True)
            g.runUntilWinner(gm)
            nbOfThrows[-1].append(gm.nbThrows)
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
            else:
                nbUnfinishable +=1

    print(nbUnfinishable, " unfinishables")
    
    return matchPlayed,wins,nbOfThrows

def giveWinrateOfEveryPlayer(players, matchPlayed, wins):
    winrate = np.array(wins)/np.array(matchPlayed)
    def hasBetterWinrate(a,b):
        return a[1] - b[1]
    results = [(players[i],winrate[i]) for i in range(len(players))]
    results = sorted(results, key = cmp_to_key(hasBetterWinrate),reverse=True)
    for r in results[0:20]:
        print(f"{r[0].facesStr()} winrate : {r[1]*100:.0f}%")


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
        plt.hist(time, bins=100, edgecolor='black', rwidth=0.8)

        # Ajout des labels
        plt.xlabel('Valeurs')
        plt.ylabel('Fréquence')
        plt.title(f'Temps de jeu a {k} joueurs par équipe')

        # Affichage
        plt.show()


from functools import cmp_to_key
if __name__ == "__main__":
    Nmax = len(createAllLegitDices()[0])
    hp = 20

    minPlays = 2
    maxPlays = 2

    players = createNrandomPlayers(hp,Nmax//10)
    matchPlayed,wins,nbThrows = battlePlayers(hp,players,minPlays,maxPlays)

    #giveWinrateOfEveryPlayer(players,matchPlayed,wins)
    giveWinrateOfEveryFace(players,matchPlayed,wins)
    analyseGameLength(nbThrows,minPlays,maxPlays)

    