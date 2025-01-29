from core import Face,Entity,Game,getNIndexesRandomly,ge
from typing import override
from rules import Rules as R
from rules import Deck
from random import randint

class Fail(Face):
    def __init__(self, owner : Entity):
        super().__init__("FAIL", owner, 0, True, Face.ThrowType.LIGHT)

    def comment(self, game, target : Entity):
        return  "fails"

    def apply(self, game, target : Entity):
        self.owner.playedThisTurn = True

    def defaultTarget(self, game):
        return self._selectNone(game)
    
class GhoulFail(Fail):
    def __init__(self, owner):
        super().__init__("FAIL", owner)
        self.isRemovable = False

class Attack(Face):
    def __init__(self, owner : Entity, dmg, tier):
        super().__init__("Attack"+str(dmg), owner, tier, True)
        self.dmg = dmg

    def comment(self, game, target : Entity):
        if target is None:
            return "no one to attack"
        else:
            return f"attacks({self.dmg}) " + target.name + ":"

    def apply(self, game, target : Entity):
        """target must be the one to attack"""
        if target is not None:
            target.handleAttack(self.owner.buffed(self.dmg),False, game)
            if target.thorns > 0:
                self.owner.handleAttack(target.thorns, False, game)
        self.owner.playedThisTurn = True

    def defaultTarget(self, game):
        return self._selectWeakestOppWithoutTooMuchArmor(game)
    
class GhoulAttack(Attack):
    def __init__(self, owner : Entity, dmg, tier):
        super().__init__(owner, dmg, tier)
        self.isRemovable = False

    @override
    def apply(self, game, target : Entity):
        """target must be the one to attack"""
        if target is None:
            ge.print("No one to attack")
        else:
            target.handleAttack(self.owner.buffed(self.dmg),False, game)
            if target.thorns > 0:
                self.owner.handleAttack(target.thorns, False, game)
        self.owner.playedThisTurn = False # That is the difference with normal attack !


class Heal(Face):
    def __init__(self, owner : Entity, heal, tier):
        super().__init__("Heal"+str(heal), owner, tier, True)
        self.heal = heal

    def comment(self, game, target : Entity):
        if target == self:
            return f"heals({self.heal}) itself:"
        else:
            return f"heals({self.heal}) " + target.name + ":"

    def apply(self, game, target : Entity):
        """target must be the one to heal"""
        # Target can't be None as the caster is alive
        target.handleHeal(self.owner.buffed(self.heal))
        self.owner.playedThisTurn = True

    def defaultTarget(self, game):
        return self._selectWeakestFriend(game)

class Armor(Face):
    def __init__(self, owner : Entity, armor, tier):
        super().__init__("Armor"+str(armor), owner, tier, True, Face.ThrowType.LIGHT)
        self.armor = armor

    def comment(self, game, target : Entity):
        return f"armors({self.armor}):"

    def apply(self, game, target: Entity):
        """target must be the one to armor"""
        # Target can't be None as the caster is alive
        target.activeArmor = self.owner.buffed(self.armor)
        self.owner.playedThisTurn = True
        
        ge.print(f"{self.owner.buffed(self.armor)} armor gained")

    def defaultTarget(self, game):
        return self._selectSelf(game)

class Concentration(Face):
    def __init__(self, owner : Entity, tier):
        super().__init__("Concentration", owner, tier, True, Face.ThrowType.LIGHT)

    def comment(self, game, target : Entity):
        return f"concentrates"

    def apply(self, game, target: Entity):
        """target is ignored"""
        if self.owner.barbarism == 0: # Can't concentrate after barbarism
            self.owner.concentration *= 2
            assert target is None, "WEIRD"
            # Do not set self.owner.playedThisTurn to True
        else:
            self.owner.playedThisTurn = True
            
    def defaultTarget(self, game):
        return self._selectNone(game)

class Stun(Face):
    def __init__(self, owner : Entity, tier):
        super().__init__("Stun", owner, tier, True)

    def comment(self, game, target : Entity):
        if target is None:
            return "no one to stun"
        else:
            return f"stuns " + target.name
    
    def apply(self, game, target: Entity):
        """Target is stunned"""
        if target is not None:
            self.owner.stunning = target
        self.owner.playedThisTurn = True

    def defaultTarget(self, game):
        return self._selectWeakestOpp(game)

class Sweep(Face):
    def __init__(self, owner: Entity, dmg, tier):
        super().__init__("Sweep"+str(dmg), owner, tier, True)
        self.dmg = dmg

    def comment(self, game, target : Entity):
        return f"sweeps({self.dmg}):"

    def apply(self, game, target: Entity):
        """Target is ignored"""
        for entity in game.entities:
            if entity.team != self.owner.team and entity.alive():
                entity.handleAttack(self.owner.buffed(self.dmg),False, game)
                if entity.thorns > 0:
                    self.owner.handleAttack(entity.thorns, False, game)
        self.owner.playedThisTurn = True

    def defaultTarget(self, game):
        return self._selectNone(game)

class Fireball(Face):
    def __init__(self, owner : Entity, dmg, tier):
        super().__init__("Fireball"+str(dmg), owner, tier, True)
        self.dmg = dmg

    def comment(self, game, target : Entity):
        if target is None:
            return "no one to fireball"
        else:
            return f"fireballs({self.dmg}) " + target.name + ":"

    def apply(self, game, target : Entity):
        """target must be the one to attack"""
        if target is not None:
            target.handleAttack(self.owner.buffed(self.dmg),True, game)
        self.owner.playedThisTurn = True

    def defaultTarget(self, game):
        return self._selectWeakestOpp(game)
    
class Poison(Face):
    def __init__(self, owner : Entity, tier):
        super().__init__("Poison", owner, tier, True)

    def comment(self, game, target : Entity):
        if target is None:
            return "No one to poison"
        else:
            return f"poisons " + target.name

    def apply(self, game, target : Entity):
        """target must be the one to attack"""
        for _ in range(self.owner.buffed(1)):
            if target is not None:
                if game.canSpawnPoison():
                    target.poisons += 1
                else:
                    ge.print("Can't spawn more poison")
        self.owner.playedThisTurn = True

    def defaultTarget(self, game):
        return self._selectWeakestOpp(game)
    
class Bomb(Face):
    def __init__(self, owner : Entity, tier):
        super().__init__("Bomb", owner, tier, True)

    def comment(self, game, target : Entity):
        if target is None:
            return "No one to bomb"
        else:
            return f"bombs " + target.name

    def apply(self, game, target : Entity):
        """target must be the one to attack"""
        for _ in range(self.owner.buffed(1)):
            if target is not None:
                if game.canSpawnBomb():
                    target.bombs += 1
                else:
                    ge.print("Can't spawn more bombs")
        self.owner.playedThisTurn = True

    def defaultTarget(self, game):
        return self._selectWeakestOpp(game)

class Upgrade(Face):
    def __init__(self, owner : Entity):
        super().__init__("Upgrade", owner, 4, False, Face.ThrowType.HEAVY)
        self.tierStack = [Deck.getFacesWithMult(1),Deck.getFacesWithMult(2),Deck.getFacesWithMult(3)]

    def comment(self, game, target : Entity):
        return f"upgrades"

    def apply(self, game, target: Entity):
        """Target is ignored. always upgrade the weakest face"""
        for _ in range(self.owner.buffed(1)):
            weakestFaceIndex = None
            weakestFaceTier = None
            for k,v in enumerate(self.owner.faces):
                if v.tier<4 and (weakestFaceTier is None or v.tier < weakestFaceTier):
                    weakestFaceIndex = k
                    weakestFaceTier = v.tier

            assert weakestFaceTier is not None, "WEIRD"
            newFaceTier = min(weakestFaceTier+1, 3)

            index  = getNIndexesRandomly(self.tierStack[newFaceTier-1],1,False)[0] # minus one because of indexes
            self.owner.faces.pop(weakestFaceIndex)
            addSpellByString(self.owner,self.tierStack[newFaceTier-1][index],newFaceTier)
        self.owner.playedThisTurn = True


    def defaultTarget(self, game):
        return self._selectSelf(game)

class Tank(Face):
    def __init__(self, owner : Entity):
        super().__init__("Tank", owner, 4, False, Face.ThrowType.LIGHT)
        self.armor = R.tankArmor

    def comment(self, game, target : Entity):
        return f"use Tanks:"

    def apply(self, game, target: Entity):
        """Target is ignored"""
        self.owner.taunting = True
        self.owner.activeArmor = self.owner.buffed(self.armor)
        self.owner.thorns = self.owner.buffed(R.tankThorns)
        ge.print(f"{self.owner.buffed(R.tankThorns)} thorns gained")
        ge.print(f"{self.owner.buffed(self.armor)} armor gained")
        self.owner.playedThisTurn = True

    def defaultTarget(self, game):
        return self._selectSelf(game)

class Vampire(Face):
    def __init__(self, owner):
        super().__init__("Vampire", owner, 4, False)

    def comment(self, game, target : Entity):
        if target is None:
            return "No one to Vampireise"
        else:
            return f"vampires " + target.name + ":"

    def apply(self, game, target):
        hpLost = 0
        if target is not None:
            hpLost = target.handleAttack(self.owner.buffed(R.vampireAttack),True, game)
            if R.vampireStealInitialHealth:
                target.initialHp -= hpLost
        if R.vampireStealInitialHealth:
            self.owner.initialHp += hpLost
        self.owner.handleHeal(hpLost)
        self.owner.playedThisTurn = True

    def defaultTarget(self, game):
        return self._selectWeakestOpp(game)

class King(Face):
    def __init__(self, owner):
        super().__init__("King", owner, 4, False)
        self.dmg = R.kingDmg
        self.heal = R.kingHeal
        self.armor = R.kingArmor

    def comment(self, game, target : Entity):
        if target is None:
            return "no one to attack. Only doing heal and armor"
        else:
            return f"kings " + target.name + ":"

    def apply(self, game, target):
        if target is not None:
            target.handleAttack(self.owner.buffed(self.dmg),False, game)
        self.owner.handleHeal(self.owner.buffed(self.heal))
        self.owner.activeArmor = self.owner.buffed(self.armor)
        ge.print(f"{self.owner.buffed(self.armor)} armor gained")
        self.owner.playedThisTurn = True

    def defaultTarget(self, game):
        return self._selectWeakestOppWithoutTooMuchArmor(game)


class Paladin(Face):
    def __init__(self, owner):
        super().__init__("Paladin", owner, 4, False)
        self.heal = R.paladinHeal

    def comment(self, game, target : Entity):
        if target == self:
            return f"paladins itself:"
        else:
            return f"paladins " + target.name + ":"

    def apply(self, game, target):
        target.handleHeal(self.heal)
        self.owner.immuning = target
        ge.print(f"{target.name} is immuned")
        self.owner.playedThisTurn = True

    def defaultTarget(self, game):
        return self._selectWeakestFriend(game)

class Lich(Face):
    def __init__(self, owner):
        super().__init__("Lich", owner, 4, False)

    def comment(self, game, target : Entity):
        return f"uses Lich"

    def apply(self, game : Game, target):
        """target is ignored"""
        nbOfGhoulsToSpawn = self.owner.buffed(1)
        for k in range(nbOfGhoulsToSpawn):
            if game.canSpawnGhoul():
                ghoul = createGhoul(self.owner)
                game.entities.append(ghoul)
            else:
                ge.print("too many ghouls")
        self.owner.playedThisTurn = True

    def defaultTarget(self, game):
        return self._selectSelf(game)
    
class Barbarian(Face):
    def __init__(self, owner : Entity):
        super().__init__("Barbarian", owner, 4, False, Face.ThrowType.LIGHT)

    def comment(self, game, target : Entity):
        return f"uses Barbarian:"

    def apply(self, game, target: Entity):
        """target is ignored"""
        if self.owner.concentration == 1 and self.owner.getHP() > 1: # Does nothing if the barbarian was concentrating or is too weak
            self.owner.barbarism += R.barbarianBuff
            self.owner.handleAttack(R.barbarianDMG, True, game)
            # Do not set self.owner.playedThisTurn to True
        else:
            self.owner.playedThisTurn = True
        assert target is None, "WEIRD"
            
    def defaultTarget(self, game):
        return self._selectNone(game)

class Thief(Face):
    def __init__(self, owner : Entity):
        super().__init__("Thief", owner, 4, False, Face.ThrowType.HEAVY)

    def comment(self, game, target : Entity):
        if target is None:
            return "No one to steal"
        else:
            return f"thiefs " + target.name + ":"

    def apply(self, game, target: Entity):
        if target is not None:
            oppfaceStolenIndex = randint(0,5)
            oppFace : Face = target.faces[oppfaceStolenIndex]
            if oppFace.isRemovable:
                #Find my weakest face
                weakestIndex = None
                weakestTier = None
                for k in range(len(self.owner.faces)):
                    if self.owner.faces[k].isRemovable:
                        if weakestIndex is None or weakestIndex > self.owner.faces[k].tier:
                            weakestIndex = k
                            weakestTier = self.owner.faces[k].tier

                assert weakestTier is not None, "WEIRD"
                if R.thiefCanRefuseTrade and weakestTier > oppFace.tier:
                    ge.print(f"refuses swaping {self.owner.faces[weakestTier].faceName} for {oppFace.faceName}")
                else:
                    # Swap
                    ge.print(f"swaps {self.owner.faces[weakestTier].faceName} for {oppFace.faceName}")
                    # Change owners
                    oppFace.owner = self.owner
                    self.owner.faces[weakestIndex].owner = target
                    # Swaps
                    tmp = self.owner.faces[weakestIndex]
                    self.owner.faces[weakestIndex] = oppFace
                    target.faces[oppfaceStolenIndex] = tmp
            else:
                ge.print(f"can't steal {oppFace.faceName}")

        self.owner.playedThisTurn = True
            
    def defaultTarget(self, game : Game):
        """ targetting is very specific for thief"""
        bestEsperance = None
        bestTarget = None
        for entity in game.entities:
            esperance = 0
            if not entity.isGhoul() and entity.team != self.owner.team and entity.alive():
                for face in entity.faces:
                    if face.isRemovable:
                        esperance += face.tier*1/6
                if bestTarget is None or esperance >  bestEsperance:
                    bestTarget = entity
                    bestEsperance = esperance
        return bestTarget
    
class Judge(Face):
    def __init__(self, owner : Entity):
        super().__init__("Judge", owner, 4, False, Face.ThrowType.LIGHT)

    def comment(self, game, target : Entity):
        return "has choices between"

    def apply(self, game, target: Entity):
        face1 = self.owner.getRandomFace()
        face2 = self.owner.getRandomFace()

        ge.print(f"{face1.faceName} and {face2.faceName}")

        faceToPlay = face1

        averageTier = sum([f.tier for f in self.owner.faces])/len(self.owner.faces)
        isCurrentDiceLowTier = averageTier < 3

        if isinstance(face1, Concentration): # Concentration is very good -> no brainer
            faceToPlay = face1
        elif isinstance(face2, Concentration): # Concentration is very good -> no brainer
            faceToPlay = face2
        elif isinstance(face1, Upgrade):
            if isCurrentDiceLowTier: # If dice is weak, go for upgrade
                faceToPlay = face1
            else: # Else, the other will be better
                faceToPlay = face2
        elif isinstance(face2, Upgrade):
            if isCurrentDiceLowTier: # If dice is weak, go for upgrade
                faceToPlay = face2
            else:
                faceToPlay = face1 # Else, the other will be better
        else: # Go for higher tier
            if face1.tier >= face2.tier:
                faceToPlay = face1
            else:
                faceToPlay = face2

        # Actually play the face
        game.countThrow(faceToPlay.throwType)
        target = faceToPlay.defaultTarget(game)
        ge.print(faceToPlay.comment(game, target))
        faceToPlay.apply(game, target)

        #Do not set self.owner.playedThisTurn = True as the invoked faces will 


    def defaultTarget(self, game : Game):
        return self._selectNone(game)

def createGhoul(father : Entity):
    ghoulHp = 1
    p = Entity(ghoulHp, "Ghoul", father.team, father)
    for _ in range(6-R.ghoulAttack1Faces-R.ghoulAttack2Faces):
        p.faces.append(Fail(p))

    for _ in range(R.ghoulAttack1Faces):
        if R.ghoulsAreEnraged:
            p.faces.append(GhoulAttack(p,1,1))
        else:
            p.faces.append(Attack(p,1,1))
    for _ in range(R.ghoulAttack2Faces):
        if R.ghoulsAreEnraged:
            p.faces.append(GhoulAttack(p,2,1))
        else:
            p.faces.append(Attack(p,2,1))
    if not R.canGhoulAttackImmediatly:
        p.playedThisTurn = True # Ghoul cannot play immediatly
    return p

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
    elif string[0:3] == "Poi":
        player.faces.append(Poison(player, tier))
    elif string[0:3] == "Bom":
        player.faces.append(Bomb(player, tier))
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
    elif string[0:3] == "Bar":
        player.faces.append(Barbarian(player))
    elif string[0:3] == "Thi":
        player.faces.append(Thief(player))
    elif string[0:3] == "Jud":
        player.faces.append(Judge(player))
    elif string[0:3] == "Fai":
        player.faces.append(Fail(player))
    elif string[0:3] ==  "Upg":
        player.faces.append(Upgrade(player))
    else:
        assert False, f"could not create spell {string} of tier {tier}"