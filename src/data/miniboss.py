"""Mini-boss spawn data."""

enemyZeroWidth = 0x21E18530
enemyZeroHeight = 0x21E18534
enemyZeroDepth = 0x21E18538
scaleOffset = 0x3510
varOffset = 0x190
scaleSize = 1.5
enemyHPMult = 3
enemyABSMult = 3
enemyItemResistMulti = 10
enemyGoldMult = 3
enemyDropChance = 100
staminaTimer = 79

attachmentsTableLucky = [
    95, 96, 97, 98, 99, 100, 101, 102, 103, 104,
    105, 106,
]

attachmentsTableUnlucky = [
    81, 82, 83, 84, 85, 91, 92, 93, 94, 111,
    112, 113, 114, 115, 116, 117, 118, 119, 120,
]

itemTableLucky = [150, 178, 235]
itemTableUnlucky = [132, 133, 134, 135]



class MiniBoss:
    enemyNumber = 0
    miniBossRolled = False

