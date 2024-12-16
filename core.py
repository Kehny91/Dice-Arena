from abc import ABC, abstractmethod
from random import randint, sample
import numpy as np


class GameEngine:
    def __init__(self):
        self.showPrints = False
        self.print = self._inactive_print if not self.showPrints else self._active_print

    def _active_print(self, string, end=" "):
        #print(string, end=end)
        with open("log.txt","a") as file:
            file.write(string+end)

    def _inactive_print(self, string, end=" "):
        pass

    def set_show_prints(self, showPrints):
        self.showPrints = showPrints
        self.print = self._active_print if showPrints else self._inactive_print
        self.print("\nPRINT ACTIVATED")

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
        # import multiprocessing as mp
        # print(f"{mp.current_process().pid} new turn")
        ge.print("\nNew Turn. HP left: ",end="")
        ge.print("|".join([f"{entity.name}: {entity.getHP()}" for entity in self.entities]))

        for entity in self.entities:
            entity.playedThisTurn = False

        stop = False
        i = 0
        while not stop and (self.winningTeam() is None):
            entityPlaying : Entity = self.entities[i]
            entityPlaying.resetEffects()
       
            # Handle bombs and poisons
            if entityPlaying.alive() and not entityPlaying.isGhoul():
                results = entityPlaying.rollBombs() # RollBombs already self clear the attribute bombs.
                for res in results:
                    if res == "left":
                        newVictim = self._findLeftEntityForBomb(entityPlaying)
                        newVictim.bombs += 1
                    elif res == "right":
                        newVictim = self._findRightEntityForBomb(entityPlaying)
                        newVictim.bombs += 1
                entityPlaying.rollPoisons()

            # Play
            while entityPlaying.canPlay(self): # Check if we are stunned and if we did not die from poison/bomb
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
    
    def canSpawnPoison(self):
        poisonCount = 0
        maxPoisonCount = 4
        for entity in self.entities:
            poisonCount += entity.poisons
        return poisonCount<maxPoisonCount
    
    def canSpawnBomb(self):
        bombCount = 0
        maxBombCount = 4
        for entity in self.entities:
            bombCount += entity.bombs
        return bombCount<maxBombCount

    def winningTeam(self):
        """Returns None if there is no winner yet, or the winning team."""
        winner = None  # Variable pour stocker la première équipe trouvée

        for entity in self.entities:
            if entity.alive() and not entity.isGhoul():  # Vérifier les conditions
                if winner is None:
                    winner = entity.team  # Première équipe trouvée
                elif winner != entity.team:
                    return None  # Plus d'une équipe vivante, pas de gagnant

        return winner  # Retourner l'équipe gagnante ou None s'il n'y en a pas
        
    def runUntilWinner(self, maxTime_min, gameStat = None):
        if gameStat is None:
            gameStat = GameStat()
        while self.winningTeam() is None:

            nbPlayersAlive = 0
            for e in self.entities:
                if e.alive() and not e.isGhoul():
                    nbPlayersAlive += 1
            if nbPlayersAlive == 0:
                ge.set_show_prints(False)

            self.newTurn(gameStat)
            timePerThrow_min = 10/60
            actualTime_min = gameStat.nbThrows*timePerThrow_min
            if actualTime_min > maxTime_min:
                print("")
                for p in self.entities:
                    p.debug()
                print("GAME TOO LONG")
                break
        ge.print("END GAME")

        self.clearGhouls()

    def _findLeftEntityForBomb(self, passingPlayer):
        i = self.entities.index(passingPlayer)
        nbEntities = len(self.entities)
        while True:
            i = (i-1)%(nbEntities)
            if self.entities[i].alive() and not self.entities[i].isGhoul():
                return self.entities[i]
            
    def _findRightEntityForBomb(self, passingPlayer):
        i = self.entities.index(passingPlayer)
        nbEntities = len(self.entities)
        while True:
            i = (i+1)%(nbEntities)
            if self.entities[i].alive() and not self.entities[i].isGhoul():
                return self.entities[i]


                

class Entity:
    def __init__(self, hp, name, team, parent = None):
        self.parent = parent
        self.faces = []
        self._hp = hp
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
        self.bombs = 0
        self.poisons = 0

    def restoreHP(self, initialHp):
        self._hp = initialHp
        self.initialHp = initialHp

    def getHP(self): # We protect from direct hp manipulation. (allow to take armor in consideration and track when entity dies)
        return self._hp

    def alive(self):
        return self._hp > 0
    
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
    
    # def _onDie(self, game : Game):
    #     # KILL THE CHILDREN
    #     toClear = []
    #     for entity in game.entities:
    #         if entity.parent == self:
    #             toClear.append(entity)
    #     for cl in toClear:
    #         self.entities.remove(cl)


    def handleAttack(self, dmg, magic):
        """Take armor into account. Returns hp lost"""
        hpLost = 0
        if not self.immune:
            if magic:
                hpLost = dmg
            else:
                hpLost = max(0, dmg-self.activeArmor)
            if self._hp<hpLost:
                hpLost = self._hp
            self._hp -= hpLost
            ge.print(f"{self.name} looses {hpLost} hp")
        else:
            ge.print(f"{self.name} is immune")
        self._hp = max(self._hp, 0)

        # if self._hp == 0 and hpLost>0:
        #     self._onDie(game)

        return hpLost

    def handleHeal(self, heal):
        assert self.alive(), "WEIRD"
        self._hp += heal
        if not Game.canOverHeal:
            self._hp = min(self._hp, self.initialHp)
        ge.print(f"{self.name} heals {heal} hp")

    def isTauntedBy(self, game : Game):
        """Returns None or the player taunting"""
        for entity in game.entities:
            if entity.alive() and entity.team != self.team:
                if entity.taunting:
                    return entity
        return None
    
    _poisonCuredFaces = 2
    _poisonDamage = 1
    _poisonIsMagic = True
    def rollPoisons(self):
        """ handle damage and curing """
        if self.poisons > 0:
            poisonsThisTurn = self.poisons
            for _ in range(poisonsThisTurn):
                facesRolled = randint(0,5)
                if facesRolled < Entity._poisonCuredFaces:
                    # We are cured
                    self.poisons -= 1
                    ge.print(f"{self.name} cured from poison")
                else:
                    # Get damages
                    ge.print(f"{self.name} is poisoned")
                    self.handleAttack(Entity._poisonDamage,Entity._poisonIsMagic)

    _bombExplosionFaces = 2
    _bombLeftFaces = 2
    _bombRightFaces = 2
    _bombDamage = 6
    _bombIsMagic = False
    def rollBombs(self):
        """ handle damages and return left, right or exploded depending on face rolled """
        results = []
        if self.bombs > 0:
            for _ in range(self.bombs):
                facesRolled = randint(0,5)
                if facesRolled < Entity._bombExplosionFaces:
                    # We exploded
                    ge.print(f"{self.name} exploded")
                    self.handleAttack(Entity._bombDamage,Entity._bombIsMagic)
                    results.append("explosion")
                elif facesRolled < Entity._bombExplosionFaces + Entity._bombLeftFaces:
                    # Pass bomb left
                    ge.print(f"{self.name} passes bomb left")
                    results.append("left")
                else:
                    # Pass bomb right
                    ge.print(f"{self.name} passes bomb right")
                    results.append("right")
            self.bombs = 0 # Bomb exploded or got passed
        return results
        


    def facesStr(self):
        return"|".join([f.faceName for f in self.faces])

    def debug(self):
        print(f"{self.name} : Team {self.team} HP {self._hp} faces : ",end="")
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
                if bestTarget is None or entity.getHP() + malus < bestTarget.getHP():
                    bestTarget = entity
                    bestTargetHealth = entity.getHP()
        
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
                if bestTarget is None or (entity.getHP() + malus < bestTarget.getHP() and not tooMuchArmor):
                    # Check if under too much armor
                    bestTarget = entity
                    bestTargetHealth = entity.getHP()
        
        return bestTarget
    
    def _selectWeakestFriend(self, game : Game):
        """ Does not select ghoul as they can't be healed. Also dpes not select entity at max health (if cannot overheal) """
        taunter = self.owner.isTauntedBy(game)
        if taunter is not None:
            return taunter

        bestTarget = self.owner
        bestTargetHealth = self.owner.getHP()

        for entity in game.entities:
            if entity.alive() and entity.team == self.owner.team and not entity.isGhoul():
                if not Game.canOverHeal and entity.getHP() < entity.initialHp:
                    if bestTarget is None or entity.getHP() < bestTarget.getHP():
                        bestTarget = entity
                        bestTargetHealth = entity.getHP()
        
        return bestTarget
    
    def _selectNone(self, game : Game):
        return None
    
    def _selectSelf(self, game : Game):
        return self.owner


def getNIndexesRandomly(elements, N, mustBeDifferent):
    """elements is passed but really, we just need its length."""
    if mustBeDifferent:
        return sample(range(len(elements)), N)  # Efficient for unique indexes
    else:
        return [randint(0, len(elements) - 1) for _ in range(N)]  # Repeats allowed