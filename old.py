""" Function obsolete that I don't want to delete now """

def battlePlayers(hp, players, minNbPlayerPerSide, maxNbPlayerPerSide, maxTime_min):
    nbPlayers = len(players)
    dictOfSpellWinrate = {}
    nbOfThrows = [] # A list per numberOfPlayerPer side containing a list of the number of throws per match

    nbIters = nbPlayers*300
    nbUnfinishable = 0
    for nbPlayerPerSide in range(minNbPlayerPerSide,maxNbPlayerPerSide+1):
        nbOfThrows.append([])
        for i in range(nbIters):
            if i%1000 ==0:
                print(f"{i/nbIters*100:.2f}%")
            playerIndexes = getNIndexesRandomly(players,2*nbPlayerPerSide,True)
            throws = battleOnce(hp, players, playerIndexes, maxTime_min,dictOfSpellWinrate)
            if throws>60*10/60: #TODO
                nbUnfinishable +=1

    print(nbUnfinishable, " unfinishables")
    
    return dictOfSpellWinrate,nbOfThrows