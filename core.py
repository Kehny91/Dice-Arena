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

    canOverHeal = False
    vampireStealInitialHealth = True
    ghoulsAreEnraged = True
    canGhoulAttackImmediatly = True

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
            if entity.isGhoul() and (not entity.alive() or not entity.parent.alive()): # Remove ghoul if lich is dead
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
        
    def runUntilWinner(self, maxTime_min, gameStat = None):
        if gameStat is None:
            gameStat = GameStat()
        while self.winningTeam() is None:
            self.newTurn(gameStat)
            timePerThrow_min = 10/60
            actualTime_min = gameStat.nbThrows*timePerThrow_min
            if actualTime_min > maxTime_min:
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
        self.initialHp = hp
        self.name = name
        self.activeArmor = 0
        self.immune = False
        self.concentration = 1
        self.stunning = None
        self.playedThisTurn = False
        self.team = team
        self.taunting = False
        self.facesBackup = []

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
        if not Game.canOverHeal:
            self.hp = min(self.hp, self.initialHp)
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

    def backupFaces(self):
        for f in self.faces:
            self.facesBackup.append(f)

    def restoreFaces(self):
        self.faces = []
        for f in self.facesBackup:
            self.faces.append(f)

class Face(ABC):
    def __init__(self, name, owner : Entity, tier, isRemovable):
        self.faceName = name
        self.owner = owner
        self.tier = tier
        self.isRemovable = isRemovable
    
    @abstractmethod
    def defaultTarget(self, game):
        pass

    @abstractmethod
    def apply(self, game, target : Entity):
        """ Apply must set playedThisTurn to True unless it is concentration"""
        pass

    def _selectWeakestOpp(self, game : Game):
        """ Prefer not to select ghouls as it is better to kill the Lich"""
        taunter = self.owner.isTauntedBy(game)
        if taunter is not None:
            return taunter

        bestTarget = None
        bestTargetHealth = None

        for entity in game.entities:
            if entity.alive() and entity.team != self.owner.team:
                malus = 20 if entity.isGhoul() else 0
                if bestTarget is None or entity.hp + malus < bestTarget.hp:
                    bestTarget = entity
                    bestTargetHealth = entity.hp
        
        return bestTarget

    def _selectWeakestOppWithoutTooMuchArmor(self, game : Game):
        """Avoid hitting someone under armor. Prefer not to select ghouls as it is better to kill the Lich"""
        taunter = self.owner.isTauntedBy(game)
        if taunter is not None:
            return taunter
    
        bestTarget = None
        bestTargetHealth = None

        for entity in game.entities:
            if entity.alive() and entity.team != self.owner.team:
                tooMuchArmor = entity.activeArmor >= self.dmg
                malus = 20 if entity.isGhoul() else 0
                if bestTarget is None or (entity.hp + malus < bestTarget.hp and not tooMuchArmor):
                    # Check if under too much armor
                    bestTarget = entity
                    bestTargetHealth = entity.hp
        
        return bestTarget
    
    def _selectWeakestFriend(self, game : Game):
        """ Does not select ghoul as they can't be healed. Also dpes not select entity at max health (if cannot overheal) """
        taunter = self.owner.isTauntedBy(game)
        if taunter is not None:
            return taunter

        bestTarget = self.owner
        bestTargetHealth = self.owner.hp

        for entity in game.entities:
            if entity.alive() and entity.team == self.owner.team and not entity.isGhoul():
                if not Game.canOverHeal and entity.hp < entity.initialHp:
                    if bestTarget is None or entity.hp < bestTarget.hp:
                        bestTarget = entity
                        bestTargetHealth = entity.hp
        
        return bestTarget
    
    def _selectNone(self, game : Game):
        return None
    
    def _selectSelf(self, game : Game):
        return self.owner
    
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