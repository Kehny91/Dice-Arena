from abc import ABC, abstractmethod
from random import randint

class Game:
    def __init__(self):
        self.entities = []

    def newTurn(self):
        print("\nNew Turn. HP left : ",end="")
        for entity in self.entities:
            entity.playedThisTurn = False
            print(entity.name, " : ", entity.hp,end=" ")
        print("")

        # Selection alétoire des joueurs
        # TODO
        stop = False
        i = 0
        while not stop:
            entityPlaying : Entity = self.entities[i]
            entityPlaying.resetEffects()
            while entityPlaying.canPlay(self):
                rolledFace = entityPlaying.faces[randint(0,len(entityPlaying.faces)-1)]
                target = rolledFace.defaultTarget(self)
                if target is not None:
                    print(entityPlaying.name," uses ",rolledFace.faceName, " on ", target.name, end=", ")
                else:
                    print(entityPlaying.name," uses ",rolledFace.faceName, end=", ")
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
            if magic:
                self.hp -= dmg
                print(self.name," looses ", dmg, " hp")
            else:
                hpLost = max(0, dmg-self.activeArmor)
                self.hp -= hpLost
                print(self.name," looses ", hpLost, " hp")
        else:
            print(self.name," is immune")

    def handleHeal(self, heal):
        self.hp += heal
        print(self.name," heals ", heal)

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

class Fail(Face):
    def __init__(self, owner : Entity):
        super().__init__("FAIL", owner)

    def apply(self, game, target : Entity):
        print("nothing happens")
        self.owner.playedThisTurn = True

    def defaultTarget(self, game):
        return self._selectNone(game)

class Attack(Face):
    def __init__(self, owner : Entity, dmg):
        super().__init__("ATTACK"+str(dmg), owner)
        self.dmg = dmg

    def apply(self, game, target : Entity):
        """target must be the one to attack"""
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
        target.activeArmor = self.owner.concentration*self.armor
        self.owner.playedThisTurn = True
        print(target.name, " gain ", self.owner.concentration*self.armor, " armor")

    def defaultTarget(self, game):
        return self._selectWeakestFriend(game)

class Concentration(Face):
    def __init__(self, owner : Entity):
        super().__init__("CONCENTRATION", owner)

    def apply(self, game, target: Entity):
        """target is ignored"""
        self.owner.concentration *= 2
        print(self.owner.name, " concentrates")
        if target is not None:
            print("WEIRD1")
        # Do not set self.owner.playedThisTurn to True
            
    def defaultTarget(self, game):
        return self._selectNone(game)

class Stun(Face):
    def __init__(self, owner : Entity):
        super().__init__("STUN", owner)
    
    def apply(self, game, target: Entity):
        """Target is stunned"""
        self.owner.stunning = target
        self.owner.playedThisTurn = True
        print(target.name, " is stunned ")

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
        target.handleAttack(self.owner.concentration*self.dmg,True)
        self.owner.playedThisTurn = True

    def defaultTarget(self, game):
        return self._selectWeakestOpp(game)

# UPGRADE IS NOT IMPLEMENTED
        
def addEveryFace(player : Entity):
    player.faces.append(Fail(player))
    player.faces.append(Attack(player,4))
    player.faces.append(Heal(player,2))
    player.faces.append(Armor(player,4))
    player.faces.append(Concentration(player))
    player.faces.append(Stun(player))
    player.faces.append(Sweep(player,2))
    player.faces.append(Fireball(player,2))

teamOne = 1
teamTwo = 2

def init1V1_everyFaces():
    g = Game()

    p1 = Entity(50,"P1",teamOne)
    addEveryFace(p1)
    g.entities.append(p1)

    p2 = Entity(50,"P2",teamTwo)
    addEveryFace(p2)
    g.entities.append(p2)
    return g

def init2V2_everyFaces():
    g = Game()

    p1_BLUE = Entity(50,"P1_BLUE",teamOne)
    addEveryFace(p1_BLUE)
    g.entities.append(p1_BLUE)

    p2_BLUE = Entity(50,"P2_BLUE",teamOne)
    addEveryFace(p2_BLUE)
    g.entities.append(p2_BLUE)

    p1_RED = Entity(50,"P1_RED",teamTwo)
    addEveryFace(p1_RED)
    g.entities.append(p1_RED)

    p2_RED = Entity(50,"P2_RED",teamTwo)
    addEveryFace(p2_RED)
    g.entities.append(p2_RED)
    return g

def runGame(game):
    nbTours = 0
    while game.winningTeam() is None:
        game.newTurn()
        nbTours += 1

    print("Terminé en ",nbTours," tours, soit ", nbTours*20/60, " minutes") #20 sec par tours
    
if __name__ == "__main__":
    #g = init1V1_everyFaces()
    g = init2V2_everyFaces()
    runGame(g)
