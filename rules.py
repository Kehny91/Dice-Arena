

class Rules:
    poisonCuredFaces = 2
    poisonDamage = 1
    poisonIsMagic = True
    bombExplosionFaces = 2
    bombLeftFaces = 2
    bombRightFaces = 2
    bombDamage = 6
    bombIsMagic = False
    canOverHeal = False
    vampireStealInitialHealth = True
    ghoulsAreEnraged = True
    canGhoulAttackImmediatly = True
    maxGhoulCount = 4
    maxPoisonCount = 4
    maxBombCount = 4
    paladinHeal = 2
    tankThorns = 2
    tankArmor = 4
    barbarianDMG = 1
    barbarianBuff = 2


class Deck:
    # faces is a list for every tier of list containing tuples (faceName, multiplicity)
    faces = [[("Attack2",3),("Heal1",1),("Sweep1",1),("Fireball1",1),("Armor2",2)],
            [("Attack4",3),("Heal3",1),("Sweep2",2),("Armor6",2),("Concentration",2),("Fireball3",2), ("Poison",2), ("Bomb",2)],
            [("Attack6",3),("Fireball5",1),("Sweep4",2)],
            [("Tank",1), ("Vampire",1), ("King",1), ("Paladin",1), ("Lich",1), ("Barbarian",1)]]
    
    allSpellsAndClass = [name for (name,mult) in faces[0]] + [name for (name,mult) in faces[1]] + [name for (name,mult) in faces[2]] + [name for (name,mult) in faces[3]]
    nbOfDifferentDices1123CF = len(faces[0])*len(faces[0])*len(faces[1])*len(faces[2])*len(faces[3])
    
    @classmethod
    def getTier(cls, faceName):
        if faceName == "Fail" or faceName == "Upgrade":
            return 0
        else:
            for tier in range(1,5):
                if faceName in Deck.getFaces(tier):
                    return tier
            # If we reach here, there is  a problem
            assert False, f"unknown tier for {faceName}"

    _level1FacesWithMult = None
    _level2FacesWithMult = None
    _level3FacesWithMult = None
    _level4FacesWithMult = None
    _level1Faces = None
    _level2Faces = None
    _level3Faces = None
    _level4Faces = None
    _inited = False

    @classmethod
    def _init(cls):
        def getListWithMultiplicity(tuples):
            out = []
            for face, mult in tuples:
                out  += [face]*mult
            return out
        Deck._level1FacesWithMult = getListWithMultiplicity(Deck.faces[0])
        Deck._level2FacesWithMult = getListWithMultiplicity(Deck.faces[1])
        Deck._level3FacesWithMult = getListWithMultiplicity(Deck.faces[2])
        Deck._level4FacesWithMult = getListWithMultiplicity(Deck.faces[3])
        Deck._level1Faces = [name for (name,mult) in Deck.faces[0]]
        Deck._level2Faces = [name for (name,mult) in Deck.faces[1]]
        Deck._level3Faces = [name for (name,mult) in Deck.faces[2]]
        Deck._level4Faces = [name for (name,mult) in Deck.faces[3]]
        Deck._inited = True

    @classmethod
    def getFacesWithMult(cls, tier):
        if not Deck._inited:
            Deck._init()
        assert tier>0 and tier<=4, f"No faces with tier {tier}"
        if tier == 1:
            return Deck._level1FacesWithMult
        elif tier == 2:
            return  Deck._level2FacesWithMult
        elif tier == 3:
            return Deck._level3FacesWithMult
        elif tier == 4:
            return Deck._level4FacesWithMult
        
    @classmethod 
    def getFaces(cls, tier):
        if not Deck._inited:
            Deck._init()
        assert tier>0 and tier<=4, f"No faces with tier {tier}"
        if tier == 1:
            return Deck._level1Faces
        elif tier == 2:
            return  Deck._level2Faces
        elif tier == 3:
            return Deck._level3Faces
        elif tier == 4:
            return Deck._level4Faces


    
