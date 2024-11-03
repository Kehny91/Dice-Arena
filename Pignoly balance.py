from abc import ABC, abstractmethod
from random import randint


showPrints = False
def toggleablePrint(string,end=" "):
    if showPrints:
        print(string, end)

class GameStat:
    def __init__(self):
        self.nbThrows = 0

class Game:
    def __init__(self):
        self.entities = []

    def newTurn(self, gameStat= None):
        toggleablePrint("\nNew Turn. HP left: ",end="")
        toggleablePrint("|".join([f"{entity.name}: {entity.hp}" for entity in self.entities]))

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
                    toggleablePrint(f"{entityPlaying.name} uses {rolledFace.faceName} on {target.name}, ",end="")
                else:
                    toggleablePrint(f"{entityPlaying.name} uses {rolledFace.faceName}, ",end="")
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
            hpLost = 0
            if magic:
                hpLost = dmg
            else:
                hpLost = max(0, dmg-self.activeArmor)
            self.hp -= hpLost
            toggleablePrint(f"{self.name} looses {hpLost} hp")
        else:
            toggleablePrint(f"{self.name} is immune")

    def handleHeal(self, heal):
        self.hp += heal
        toggleablePrint(f"{self.name} heals {heal} hp")

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
        toggleablePrint("nothing happens")
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
            toggleablePrint("No one to attack")
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
        
        toggleablePrint(f"{target.name} gains {self.owner.concentration*self.armor} armor")

    def defaultTarget(self, game):
        return self._selectSelf(game)

class Concentration(Face):
    def __init__(self, owner : Entity):
        super().__init__("CONCENTRATION", owner)

    def apply(self, game, target: Entity):
        """target is ignored"""
        self.owner.concentration *= 2
        toggleablePrint(f"{self.owner.name} concentrates")
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
            toggleablePrint("No one to stun")
        else:
            self.owner.stunning = target
            toggleablePrint(f"{target.name} is stunned")
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
            toggleablePrint("No one to fireball")
        else:
            target.handleAttack(self.owner.concentration*self.dmg,True)
        self.owner.playedThisTurn = True

    def defaultTarget(self, game):
        return self._selectWeakestOpp(game)

# UPGRADE IS NOT IMPLEMENTED
        
#level1Faces = ["Attack1","Attack2","Attack3","Heal1","Heal2","Sweep1","Sweep2","Fireball1","Armor2","Armor3"]
level1Faces = ["Attack1","Attack2","Heal1","Heal2","Sweep1","Sweep2","Fireball1","Armor2","Armor3"]

def addSpellByString(player, string):
    if string[0:3] == "Att":
        player.faces.append(Attack(player,int(string[-1])))
    if string[0:3] == "Hea":
        player.faces.append(Heal(player,int(string[-1])))
    if string[0:3] == "Swe":
        player.faces.append(Sweep(player,int(string[-1])))
    if string[0:3] == "Fir":
        player.faces.append(Fireball(player,int(string[-1])))
    if string[0:3] == "Arm":
        player.faces.append(Armor(player,int(string[-1])))

def addAllSpellsToPlayer(player, spells):
    for spell in spells:
        addSpellByString(player, spell)

teamOne = 1
teamTwo = 2

def runGame(game):
    nbTours = 0
    while game.winningTeam() is None:
        game.newTurn()
        nbTours += 1

    print(f"Terminé en {nbTours} tours, soit {nbTours*20/60} minutes") #20 sec par tours

def runGameAndMeasureTime_s(game):
    stat = GameStat()

    nbTours = 0
    while game.winningTeam() is None:
        game.newTurn(stat)
        nbTours += 1
    
    timePerThrow_s = 20

    return stat.nbThrows*timePerThrow_s

def runGameAndReturnWinner(game):
    while game.winningTeam() is None:
        game.newTurn()

    win = game.winningTeam()
    for player in game.entities:
        if player.team == win:
            return player 

def battle(listOfSpells):
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

    for i in range(len(players)-1):
        for j in range(i+1,len(players)):
            for _ in range(1000):
                # get them ready to fight
                players[i].resetEffects()
                players[i].hp = hp
                players[i].team=1
                gamePlayed[i] += 1

                players[j].resetEffects()
                players[j].hp = hp
                players[j].team=2
                gamePlayed[j] += 1

                g = Game()

                if randint(0,1) == 0:           
                    g.entities.append(players[i])
                    g.entities.append(players[j])
                else:
                    g.entities.append(players[j])
                    g.entities.append(players[i])

                winner = runGameAndReturnWinner(g)
                if winner == players[i]:
                    victories[i] += 1
                if winner == players[j]:
                    victories[j] += 1

    for k,player in enumerate(players):
        print(f"player {player.name} : winrate of {victories[k]/gamePlayed[k]*100:.0f} %")

    

import matplotlib.pyplot as plt

if __name__ == "__main__":
    #g = init1V1_everyFaces()
    battle(level1Faces)
