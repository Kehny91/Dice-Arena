from abc import ABC, abstractmethod
from random import randint
import numpy as np

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

            i += 1
            if i>=len(self.entities):
                stop = True

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
            if turn > 1000:
                # print("")
                # for p in self.entities:
                #     p.debug()
                print("GAME TOO LONG")
                break

                

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

    def alive(self):
        return self.hp > 0
    
    def resetEffects(self):
        """Called before rerolling the dice. DO NOT CALL WHEN REROLLING AFTER CONCENTRATION"""
        self.activeArmor = 0
        self.immune = False
        self.concentration = 1
        self.stunning = None

    def canPlay(self, game : Game):
        for entity in game.entities:
            if entity.stunning == self:
                return False
        return not self.playedThisTurn and self.alive()

    def handleAttack(self, dmg, magic):
        if not self.immune:
            hpLost = 0
            if magic:
                hpLost = dmg
            else:
                hpLost = max(0, dmg-self.activeArmor)
            self.hp -= hpLost
            ge.print(f"{self.name} looses {hpLost} hp")
        else:
            ge.print(f"{self.name} is immune")

    def handleHeal(self, heal):
        self.hp += heal
        ge.print(f"{self.name} heals {heal} hp")

    def facesStr(self):
        return"|".join([f.faceName for f in self.faces])

    def debug(self):
        print(f"{self.name} : HP {self.hp} faces : ",end="")
        self.printFaces()

class Face(ABC):
    def __init__(self, name, owner : Entity):
        self.faceName = name
        self.owner = owner
    
    @abstractmethod
    def defaultTarget(self, game):
        pass

    @abstractmethod
    def apply(self, game, target : Entity):
        """ Apply must set playedThisTurn to True unless it is concentration"""
        pass

    def _selectWeakestOpp(self, game : Game):
        bestTarget = None
        bestTargetHealth = None

        for entity in game.entities:
            if entity.alive() and entity.team != self.owner.team:
                if bestTarget is None or entity.hp < bestTarget.hp:
                    bestTarget = entity
                    bestTargetHealth = entity.hp
        
        return bestTarget
    
    def _selectWeakestFriend(self, game : Game):
        bestTarget = None
        bestTargetHealth = None

        for entity in game.entities:
            if entity.alive() and entity.team == self.owner.team:
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
        super().__init__("FAIL", owner)

    def apply(self, game, target : Entity):
        ge.print("nothing happens")
        self.owner.playedThisTurn = True

    def defaultTarget(self, game):
        return self._selectNone(game)

class Attack(Face):
    def __init__(self, owner : Entity, dmg):
        super().__init__("ATTACK"+str(dmg), owner)
        self.dmg = dmg

    def apply(self, game, target : Entity):
        """target must be the one to attack"""
        if target is None:
            ge.print("No one to attack")
        else:
            target.handleAttack(self.owner.concentration*self.dmg,False)
        self.owner.playedThisTurn = True

    def defaultTarget(self, game):
        return self._selectWeakestOpp(game)

class Heal(Face):
    def __init__(self, owner : Entity, heal):
        super().__init__("HEAL"+str(heal), owner)
        self.heal = heal

    def apply(self, game, target : Entity):
        """target must be the one to heal"""
        # Target can't be None as the caster is alive
        target.handleHeal(self.owner.concentration*self.heal)
        self.owner.playedThisTurn = True

    def defaultTarget(self, game):
        return self._selectWeakestFriend(game)

class Armor(Face):
    def __init__(self, owner : Entity, armor):
        super().__init__("ARMOR"+str(armor), owner)
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
    def __init__(self, owner : Entity):
        super().__init__("CONCENTRATION", owner)

    def apply(self, game, target: Entity):
        """target is ignored"""
        self.owner.concentration *= 2
        ge.print(f"{self.owner.name} concentrates")
        assert target is None, "WEIRD"
        # Do not set self.owner.playedThisTurn to True
            
    def defaultTarget(self, game):
        return self._selectNone(game)

class Stun(Face):
    def __init__(self, owner : Entity):
        super().__init__("STUN", owner)
    
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
    def __init__(self, owner: Entity, dmg):
        super().__init__("SWEEP"+str(dmg), owner)
        self.dmg = dmg

    def apply(self, game, target: Entity):
        """Target is ignored"""
        for entity in game.entities:
            if entity.team != self.owner.team:
                entity.handleAttack(self.owner.concentration*self.dmg,False)
        self.owner.playedThisTurn = True

    def defaultTarget(self, game):
        return self._selectNone(game)

class Fireball(Face):
    def __init__(self, owner : Entity, dmg):
        super().__init__("FIREBALL"+str(dmg), owner)
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

# UPGRADE IS NOT IMPLEMENTED
        
level1Faces = ["Attack1","Attack2","Heal1","Sweep1","Sweep2","Fireball1","Armor2","Armor3"]
#level2Faces = ["Attack3","Attack4","Heal2","Sweep3","Armor6"]
#level3Faces = ["Attack5","Attack6","Heal3","Concentration","Fireball3"]
level2Faces = ["Attack3","Attack4","Heal2","Sweep3","Armor6","Concentration"]
level3Faces = ["Attack5","Attack6","Fireball3"]


def addSpellByString(player, string):
    if string[0:3] == "Att":
        player.faces.append(Attack(player,int(string[-1])))
    elif string[0:3] == "Hea":
        player.faces.append(Heal(player,int(string[-1])))
    elif string[0:3] == "Swe":
        player.faces.append(Sweep(player,int(string[-1])))
    elif string[0:3] == "Fir":
        player.faces.append(Fireball(player,int(string[-1])))
    elif string[0:3] == "Arm":
        player.faces.append(Armor(player,int(string[-1])))
    elif string[0:3] == "Con":
        player.faces.append(Concentration(player))
    else:
        assert False, "WEIRD"

def addAllSpellsToPlayer(player, spells):
    for spell in spells:
        addSpellByString(player, spell)


def createLegitPlayer(hp, name, team):
    p = Entity(hp,name,team)
    lvl1Indexes = getNIndexesRandomly(level1Faces,2,False)
    lvl2Indexes = getNIndexesRandomly(level2Faces,1,False)
    lvl3Indexes = getNIndexesRandomly(level3Faces,1,False)
    addSpellByString(p,level1Faces[lvl1Indexes[0]])
    addSpellByString(p,level1Faces[lvl1Indexes[1]])
    addSpellByString(p,level2Faces[lvl2Indexes[0]])
    addSpellByString(p,level3Faces[lvl3Indexes[0]])
    p.faces.append(Fail(p))
    return p

teamOne = 1
teamTwo = 2

def preparePlayerForBattle(player, hp, team):
    player.resetEffects()
    player.hp = hp
    player.team=team

def battleOfPlayerMissingOneSpell(listOfSpells, nbPlayerPerSide):
    hp = 20
    nbOfSpells = len(listOfSpells)
    nbPlayers = nbOfSpells + 1
    players = []
    victories = [0]*nbPlayers
    gamePlayed = [0]*nbPlayers
    for i in range(nbOfSpells):
        p = Entity(20,"unassigned",0)
        addAllSpellsToPlayer(p, listOfSpells)
        facesRemoved = p.faces.pop(i)
        p.name = "no"+facesRemoved.faceName
        players.append(p)

    p = Entity(20,"everything",0)
    addAllSpellsToPlayer(p, listOfSpells)
    players.append(p)

    alliesI = []
    alliesJ = []

    for k in range(nbPlayerPerSide-1):
        alliesI.append(Entity(hp,"allyI",0))
        addAllSpellsToPlayer(alliesI[-1],listOfSpells)
        alliesJ.append(Entity(hp,"allyJ",0))
        addAllSpellsToPlayer(alliesJ[-1],listOfSpells)

    for i in range(len(players)-1):
        for j in range(i+1,len(players)):

            for _ in range(1000):
                # get them ready to fight
                players[i].resetEffects()
                players[i].hp = hp
                players[i].team=1
                gamePlayed[i] += 1

                for k in range(nbPlayerPerSide-1):
                    alliesI[k].resetEffects()
                    alliesI[k].hp = hp
                    alliesI[k].team = 1

                players[j].resetEffects()
                players[j].hp = hp
                players[j].team=2
                gamePlayed[j] += 1

                for k in range(nbPlayerPerSide-1):
                    alliesJ[k].resetEffects()
                    alliesJ[k].hp = hp
                    alliesJ[k].team = 2

                g = Game()

                thisGameParticipants = [players[i],players[j]]+alliesI+alliesJ
                ordering = getNIndexesRandomly(thisGameParticipants,2*nbPlayerPerSide,True)

                for k in ordering:
                    g.entities.append(thisGameParticipants[k])

                g.runUntilWinner()
                winningTeam = g.winningTeam()
                if winningTeam == players[i].team:
                    victories[i] += 1
                if winningTeam == players[j].team:
                    victories[j] += 1

    for k,player in enumerate(players):
        print(f"{player.name} \t {victories[k]/gamePlayed[k]*100:.0f} %")


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


def battleOfRandomLegitPlayers(nbPlayerPerSide):
    hp = 20
    nbTeams = 1000
    nbPlayers = nbTeams*nbPlayerPerSide
    players = []
    matchPlayed = [0]*nbPlayers
    wins = [0]*nbPlayers
    for k in range(nbPlayers):
        players.append(createLegitPlayer(hp,"p"+str(k),0))

    nbIters = 100000
    # Sans heal 3 => 963  / 100000
    # Avec heal 3 => 2174 / 100000 
    nbUnfinishable = 0
    for i in range(nbIters):
        playerIndexes = getNIndexesRandomly(players,2*nbPlayerPerSide,True)
        teamA = [players[playerIndexes[k]] for k in range(nbPlayerPerSide)]
        teamB = [players[playerIndexes[k]] for k in range(nbPlayerPerSide,2*nbPlayerPerSide)]
        for p in  teamA:
            preparePlayerForBattle(p, hp, 1)
        for p in  teamB:
            preparePlayerForBattle(p, hp, 2)
        contestants = teamA+teamB
        
        ordering = getNIndexesRandomly(contestants,2*nbPlayerPerSide,True)
        g = Game()
        for k in ordering:
            g.entities.append(contestants[k])

        g.runUntilWinner()
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
    
    return players,matchPlayed,wins


        

import matplotlib.pyplot as plt
from functools import cmp_to_key
if __name__ == "__main__":
    players,matchPlayed,wins = battleOfRandomLegitPlayers(1)
    winrate = np.array(wins)/np.array(matchPlayed)

    def hasBetterWinrate(a,b):
        return a[1] - b[1]
    
    results = [(players[i],winrate[i]) for i in range(len(players))]
    results = sorted(results, key = cmp_to_key(hasBetterWinrate),reverse=True)
    for r in results[0:20]:
        print(f"{r[0].facesStr()} winrate : {r[1]*100:.0f}%")

    # On compte combien de fois un spell s'est retrouvé sur le dé du vainqueur
    # Problème, certains spells sont moins fréquent que d'autres donc il faut pondérer