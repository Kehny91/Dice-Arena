from abc import ABC, abstractmethod
from random import randint
import random
import numpy as np
import math
import itertools
class GameEngine:
    def __init__(self):
        self.showPrints = False
        self.print = self._inactive_print if not self.showPrints else self._active_print

    def _active_print(self, string, end=" "):
        print(string, end=end)

    def _inactive_print(self, string, end=" "):
        pass

    def set_show_prints(self, showPrints):
        self.showPrints = showPrints
        self.print = self._active_print if showPrints else self._inactive_print

ge = GameEngine()

class GameStat:
    def __init__(self):
        self.nbThrows = 0

class Game:
    def __init__(self):
        self.entities = []

    def newTurn(self, gameStat= None):
        ge.print("\nNew Turn. HP left: ",end="")
        ge.print("|".join([f"{entity.name}: {entity.hp}" for entity in self.entities]))

        for entity in self.entities:
            entity.playedThisTurn = False

        # Selection alétoire des joueurs
        # TODO
        stop = False
        i = 0
        while not stop:
            entityPlaying : Entity = self.entities[i]
            entityPlaying.resetEffects()
            while entityPlaying.canPlay(self):
                rolledFace = entityPlaying.faces[randint(0,len(entityPlaying.faces)-1)]
                if gameStat is not None:
                    gameStat.nbThrows += 1
                target = rolledFace.defaultTarget(self)
                if target is not None:
                    ge.print(f"{entityPlaying.name} uses {rolledFace.faceName} on {target.name}, ",end="")
                else:
                    ge.print(f"{entityPlaying.name} uses {rolledFace.faceName}, ",end="")
                rolledFace.apply(self, rolledFace.defaultTarget(self))
                self.clearDeadGhouls()

            i += 1
            if i>=len(self.entities):
                stop = True

    def clearDeadGhouls(self):
        toClear = []
        for entity in self.entities:
            if entity.isGhoul() and not entity.alive():
                toClear.append(entity)
        for cl in toClear:
            self.entities.remove(cl)

    def clearGhouls(self):
        toClear = []
        for entity in self.entities:
            if entity.isGhoul():
                toClear.append(entity)
        for cl in toClear:
            self.entities.remove(cl)

    def canSpawnGhoul(self):
        ghoulCount = 0
        maxGhoulCount = 4
        for entity in self.entities:
            if entity.isGhoul():
                ghoulCount += 1
        return ghoulCount<maxGhoulCount

    def winningTeam(self):
        """Returns None is there is no winner yet, or the winning team"""
        inGameTeams = set()
        for entity in self.entities:
            if entity.alive():
                inGameTeams.add(entity.team)

        if len(inGameTeams) == 1:
            return list(inGameTeams)[0]
        else:
            return None
        
    def runUntilWinner(self, gameStat = None):
        turn = 0
        while self.winningTeam() is None:
            self.newTurn(gameStat)
            turn +=1
            timePerTurn_min = len(self.entities)*10/60 # Chacun prend 10 s pour lancer
            if turn*timePerTurn_min > 40:
                print("")
                for p in self.entities:
                    p.debug()
                print("GAME TOO LONG")
                break

        self.clearGhouls()

                

class Entity:
    def __init__(self, hp, name, team, parent = None):
        self.parent = parent
        self.faces = []
        self.hp = hp
        self.name = name
        self.activeArmor = 0
        self.immune = False
        self.concentration = 1
        self.stunning = None
        self.playedThisTurn = False
        self.team = team
        self.taunting = False

    def alive(self):
        return self.hp > 0
    
    def isGhoul(self):
        return self.parent is not None
    
    def resetEffects(self):
        """Called before rerolling the dice. DO NOT CALL WHEN REROLLING AFTER CONCENTRATION"""
        self.activeArmor = 0
        self.immune = False
        self.concentration = 1
        self.stunning = None
        self.taunting = False

    def canPlay(self, game : Game):
        for entity in game.entities:
            if entity.stunning == self:
                return False
        return not self.playedThisTurn and self.alive()

    def handleAttack(self, dmg, magic):
        """Take armor into account. Returns hp lost"""
        hpLost = 0
        if not self.immune:
            if magic:
                hpLost = dmg
            else:
                hpLost = max(0, dmg-self.activeArmor)
            if self.hp<hpLost:
                hpLost = self.hp
            self.hp -= hpLost
            ge.print(f"{self.name} looses {hpLost} hp")
        else:
            ge.print(f"{self.name} is immune")
        self.hp = max(self.hp, 0)
        return hpLost

    def handleHeal(self, heal):
        self.hp += heal
        ge.print(f"{self.name} heals {heal} hp")

    def isTauntedBy(self, game : Game):
        """Returns None or the player taunting"""
        for entity in game.entities:
            if entity.alive() and entity.team != self.team:
                if entity.taunting:
                    return entity
        return None

    def facesStr(self):
        return"|".join([f.faceName for f in self.faces])

    def debug(self):
        print(f"{self.name} : Team {self.team} HP {self.hp} faces : ",end="")
        print(self.facesStr())

class Face(ABC):
    def __init__(self, name, owner : Entity, tier):
        self.faceName = name
        self.owner = owner
        self.tier = tier
    
    @abstractmethod
    def defaultTarget(self, game):
        pass

    @abstractmethod
    def apply(self, game, target : Entity):
        """ Apply must set playedThisTurn to True unless it is concentration"""
        pass

    def _selectWeakestOpp(self, game : Game):
        taunter = self.owner.isTauntedBy(game)
        if taunter is not None:
            return taunter

        bestTarget = None
        bestTargetHealth = None

        for entity in game.entities:
            if entity.alive() and entity.team != self.owner.team:
                if bestTarget is None or entity.hp < bestTarget.hp:
                    bestTarget = entity
                    bestTargetHealth = entity.hp
        
        return bestTarget

    def _selectWeakestOppWithoutTooMuchArmor(self, game : Game):
        """Special case : avoid hitting someone under armor"""
        taunter = self.owner.isTauntedBy(game)
        if taunter is not None:
            return taunter
    
        bestTarget = None
        bestTargetHealth = None

        for entity in game.entities:
            if entity.alive() and entity.team != self.owner.team:
                tooMuchArmor = entity.activeArmor >= self.dmg
                if bestTarget is None or (entity.hp < bestTarget.hp and not tooMuchArmor):
                    # Check if under too much armor
                    bestTarget = entity
                    bestTargetHealth = entity.hp
        
        return bestTarget
    
    def _selectWeakestFriend(self, game : Game):
        """ Does not select ghoul """
        taunter = self.owner.isTauntedBy(game)
        if taunter is not None:
            return taunter

        bestTarget = None
        bestTargetHealth = None

        for entity in game.entities:
            if entity.alive() and entity.team == self.owner.team and not entity.isGhoul():
                if bestTarget is None or entity.hp < bestTarget.hp:
                    bestTarget = entity
                    bestTargetHealth = entity.hp
        
        return bestTarget
    
    def _selectNone(self, game : Game):
        return None
    
    def _selectSelf(self, game : Game):
        return self.owner

class Fail(Face):
    def __init__(self, owner : Entity):
        super().__init__("FAIL", owner, 0)

    def apply(self, game, target : Entity):
        ge.print("nothing happens")
        self.owner.playedThisTurn = True

    def defaultTarget(self, game):
        return self._selectNone(game)

class Attack(Face):
    def __init__(self, owner : Entity, dmg, tier):
        super().__init__("Attack"+str(dmg), owner, tier)
        self.dmg = dmg

    def apply(self, game, target : Entity):
        """target must be the one to attack"""
        if target is None:
            ge.print("No one to attack")
        else:
            target.handleAttack(self.owner.concentration*self.dmg,False)
        self.owner.playedThisTurn = True

    def defaultTarget(self, game):
        return self._selectWeakestOppWithoutTooMuchArmor(game)

class Heal(Face):
    def __init__(self, owner : Entity, heal, tier):
        super().__init__("Heal"+str(heal), owner, tier)
        self.heal = heal

    def apply(self, game, target : Entity):
        """target must be the one to heal"""
        # Target can't be None as the caster is alive
        target.handleHeal(self.owner.concentration*self.heal)
        self.owner.playedThisTurn = True

    def defaultTarget(self, game):
        return self._selectWeakestFriend(game)

class Armor(Face):
    def __init__(self, owner : Entity, armor, tier):
        super().__init__("Armor"+str(armor), owner, tier)
        self.armor = armor

    def apply(self, game, target: Entity):
        """target must be the one to armor"""
        # Target can't be None as the caster is alive
        target.activeArmor = self.owner.concentration*self.armor
        self.owner.playedThisTurn = True
        
        ge.print(f"{target.name} gains {self.owner.concentration*self.armor} armor")

    def defaultTarget(self, game):
        return self._selectSelf(game)

class Concentration(Face):
    def __init__(self, owner : Entity, tier):
        super().__init__("Concentration", owner, tier)

    def apply(self, game, target: Entity):
        """target is ignored"""
        self.owner.concentration *= 2
        ge.print(f"{self.owner.name} concentrates")
        assert target is None, "WEIRD"
        # Do not set self.owner.playedThisTurn to True
            
    def defaultTarget(self, game):
        return self._selectNone(game)

class Stun(Face):
    def __init__(self, owner : Entity, tier):
        super().__init__("Stun", owner, tier)
    
    def apply(self, game, target: Entity):
        """Target is stunned"""
        if target is None:
            ge.print("No one to stun")
        else:
            self.owner.stunning = target
            ge.print(f"{target.name} is stunned")
        self.owner.playedThisTurn = True
        

    def defaultTarget(self, game):
        return self._selectWeakestOpp(game)

class Sweep(Face):
    def __init__(self, owner: Entity, dmg, tier):
        super().__init__("Sweep"+str(dmg), owner, tier)
        self.dmg = dmg

    def apply(self, game, target: Entity):
        """Target is ignored"""
        for entity in game.entities:
            if entity.team != self.owner.team and entity.alive():
                entity.handleAttack(self.owner.concentration*self.dmg,False)
        self.owner.playedThisTurn = True

    def defaultTarget(self, game):
        return self._selectNone(game)

class Fireball(Face):
    def __init__(self, owner : Entity, dmg, tier):
        super().__init__("Fireball"+str(dmg), owner, tier)
        self.dmg = dmg

    def apply(self, game, target : Entity):
        """target must be the one to attack"""
        if target is None:
            ge.print("No one to fireball")
        else:
            target.handleAttack(self.owner.concentration*self.dmg,True)
        self.owner.playedThisTurn = True

    def defaultTarget(self, game):
        return self._selectWeakestOpp(game)

class Upgrade(Face):
    def __init__(self, owner : Entity, tier1Stack, tier2Stack, tier3Stack):
        super().__init__("Upgrade", owner)
        self.tier1Stack = tier1Stack
        self.tier2Stack = tier2Stack
        self.tier3Stack = tier3Stack

    def apply(self, game, target: Entity):
        """Target is ignored. always upgrade the weakest face"""
        weakestFaceIndex = None
        weakestFaceTier = None
        for k,v in enumerate(self.owner.faces):
            if weakestFaceTier is None or v.tier < weakestFaceTier:
                weakestFaceIndex = k
                weakestFaceTier = v.tier

        def defaultTarget(self, game):
            return self._selectSelf(game)


class Tank(Face):
    def __init__(self, owner : Entity):
        super().__init__("Tank", owner, 4)
        self.armor = 4

    def apply(self, game, target: Entity):
        """Target is ignored"""
        self.owner.taunting = True
        self.owner.activeArmor = self.owner.concentration*self.armor
        ge.print(f"{target.name} gains {self.owner.concentration*self.armor} armor")
        self.owner.playedThisTurn = True

    def defaultTarget(self, game):
        return self._selectSelf(game)

class Vampire(Face):
    def __init__(self, owner):
        super().__init__("Vampire", owner, 4)

    def apply(self, game, target):
        hpLost = 0
        if target is None:
            ge.print("No one to Vampireise")
        else:
            hpLost = target.handleAttack(2*self.owner.concentration,True)
        self.owner.handleHeal(hpLost)
        self.owner.playedThisTurn = True

    def defaultTarget(self, game):
        return self._selectWeakestOpp(game)

class King(Face):
    def __init__(self, owner):
        super().__init__("King", owner, 4)
        self.dmg = 2 # Needed for _selectWeakestOppWithoutTooMuchArmor
        self.heal = 1
        self.armor = 1

    def apply(self, game, target):
        if target is None:
            ge.print("No one to attack")
        else:
            target.handleAttack(self.dmg*self.owner.concentration,False)
        self.owner.handleHeal(self.heal*self.owner.concentration)
        self.owner.activeArmor = self.armor*self.owner.concentration
        ge.print(f"{self.owner.name} gains {self.owner.concentration*self.armor} armor")
        self.owner.playedThisTurn = True

    def defaultTarget(self, game):
        return self._selectWeakestOppWithoutTooMuchArmor(game)


class Paladin(Face):
    def __init__(self, owner):
        super().__init__("Paladin", owner, 4)

    def apply(self, game, target):
        self.owner.immune = True
        self.owner.playedThisTurn = True

    def defaultTarget(self, game):
        return self._selectSelf(game)

class Lich(Face):
    def __init__(self, owner):
        super().__init__("Lich", owner, 4)

    def apply(self, game : Game, target):
        """target is ignored"""
        nbOfGhoulsToSpawn = 1*self.owner.concentration
        for k in range(nbOfGhoulsToSpawn):
            if game.canSpawnGhoul():
                ghoul = createGhoul(self.owner)
                ghoul.playedThisTurn = True # Ghoul cannot play immediatly
                ge.print("ghoul spawned")
                game.entities.append(ghoul)
            else:
                ge.print("too many ghouls")
        self.owner.playedThisTurn = True

    def defaultTarget(self, game):
        return self._selectSelf(game)


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

level3Faces =        ["Attack6","Fireball5","Sweep5"]
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

def addSpellByString(player, string, tier):
    if string[0:3] == "Att":
        player.faces.append(Attack(player,int(string[-1]), tier))
    elif string[0:3] == "Hea":
        player.faces.append(Heal(player,int(string[-1]), tier))
    elif string[0:3] == "Swe":
        player.faces.append(Sweep(player,int(string[-1]), tier))
    elif string[0:3] == "Fir":
        player.faces.append(Fireball(player,int(string[-1]), tier))
    elif string[0:3] == "Arm":
        player.faces.append(Armor(player,int(string[-1]), tier))
    elif string[0:3] == "Con":
        player.faces.append(Concentration(player, tier))
    elif string[0:3] == "Tan":
        player.faces.append(Tank(player))
    elif string[0:3] == "Vam":
        player.faces.append(Vampire(player))
    elif string[0:3] == "Kin":
        player.faces.append(King(player))
    elif string[0:3] == "Pal":
        player.faces.append(Paladin(player))
    elif string[0:3] == "Lic":
        player.faces.append(Lich(player))
    else:
        assert False, "WEIRD"

def addAllSpellsToPlayer(player, spells, tier):
    for spell in spells:
        addSpellByString(player, spell, tier)


def createLegitRandomPlayer(hp, name, team):
    p = Entity(hp,name,team)
    lvl1Indexes = getNIndexesRandomly(level1FacesWithMult,2,False)
    lvl2Indexes = getNIndexesRandomly(level2FacesWithMult,1,False)
    lvl3Indexes = getNIndexesRandomly(level3FacesWithMult,1,False)
    classIndex = getNIndexesRandomly(classFaces,1,False)
    addSpellByString(p,level1FacesWithMult[lvl1Indexes[0]],1)
    addSpellByString(p,level1FacesWithMult[lvl1Indexes[1]],1)
    addSpellByString(p,level2FacesWithMult[lvl2Indexes[0]],2)
    addSpellByString(p,level3FacesWithMult[lvl3Indexes[0]],3)
    addSpellByString(p,classFaces[classIndex[0]],4)
    p.faces.append(Fail(p))
    return p

def createPlayer(hp, name, team, dice, tierlist):
    p = Entity(hp,name,team)
    for k,faceName in enumerate(dice):
        addSpellByString(p,faceName,tierlist[k])
    p.faces.append(Fail(p))
    return p


def createGhoul(father : Entity):
    ghoulHp = 1
    p = Entity(ghoulHp, "Ghoul", father.team, father)
    p.faces.append(Fail(p))
    p.faces.append(Fail(p))
    p.faces.append(Fail(p))
    p.faces.append(Fail(p))
    p.faces.append(Attack(p,2,1))
    p.faces.append(Attack(p,1,1))
    return p

teamOne = 1
teamTwo = 2

def preparePlayerForBattle(player, hp, team):
    player.resetEffects()
    player.hp = hp
    player.team=team

def getNIndexesRandomly(elements, N, mustBeDifferent):
    """elements is passed but really, we just need its length"""
    pickedIndexes = []
    allIndexes = list(range(len(elements)))
    for k in range(N):
        if mustBeDifferent:
            pickedIndexes.append(allIndexes.pop(randint(0,len(allIndexes)-1)))
        else:
            pickedIndexes.append(allIndexes[randint(0,len(allIndexes)-1)])
    return pickedIndexes

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

    minPlays = 1
    maxPlays = 2

    players = createNrandomPlayers(hp,Nmax//10)
    matchPlayed,wins,nbThrows = battlePlayers(hp,players,minPlays,maxPlays)

    #giveWinrateOfEveryPlayer(players,matchPlayed,wins)
    giveWinrateOfEveryFace(players,matchPlayed,wins)
    analyseGameLength(nbThrows,minPlays,maxPlays)

    