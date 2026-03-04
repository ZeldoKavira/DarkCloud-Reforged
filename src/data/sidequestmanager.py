"""Side quest definitions and dungeon enemy lists."""

dungeonNames = ["Divine Beast Cave", "Wise Owl Forest", "Shipwreck", "Sun & Moon Temple", "Moon Sea", "Gallery of Time", "Demon Shaft"]
DBCEnemies = ["Master Jackets", "Dashers", "Mimics", "Dragons"]
WOFEnemies = ["Fliflis", "Earth Diggers", "Mimics", "Werewolves"]
ShipwreckEnemies = ["Gunnys", "Gyons", "Mimics", "Pirate´s Chariots"]
SMEnemies = ["Golems", "Dunes", "Mimics", "Blue Dragons"]
MoonSeaEnemies = ["Moon Diggers", "Space Gyons", "Mimics", "Crescent Barons"]
GOFEnemies = ["Rash Dashers", "Jokers", "Mimics", "Alexanders"]
NorunePondFish = ["Nilers", "Gummies", "Nonkies", "Gobblers"]
MatatakiPondFish = ["Baku Bakus", "Gobblers", "Tartons", "Umadakaras"]
MatatakiWaterfallFish = ["Baku Bakus", "Nonkies", "Gummies", "Mardan Garayan", "Baron Garayan"]
QueensSeaFish = ["Bobos", "Kajis", "Piccolys", "Bons", "Hamahamas"]
MuskaOasisFish = ["Negies", "Dens", "Heelas", "Mardan Garayans", "Baron Garayan"]
alliesChar = ["Ť", "Ӿ", "Ʊ", "Ʀ", "Ų", "Ō"]
DBCEnemyIDs = [1, 6, 35, 59]
WOFEnemyIDs = [8, 12, 79, 7]
ShipwreckEnemyIDs = [23, 24, 81, 25]
SMEnemyIDs = [30, 32, 37, 73]
MoonSeaEnemyIDs = [66, 72, 39, 76]
GOFEnemyIDs = [63, 48, 83, 43]
NorunePondFishIDs = [7, 6, 2, 1]
MatatakiPondFishIDs = [4, 1, 10, 9]
MatatakiWaterfallFishIDs = [4, 2, 6, 5, 17]
QueensSeaFishIDs = [0, 3, 11, 12, 13]
MuskaOasisFishIDs = [14, 15, 16, 5, 17]
DBCBackFloors = [2, 4, 5, 6, 8, 9, 11, 12, 13]



class SideQuestManager:
    rolledDng = 0
    rolledEnemy = 0
    enemyID = 0
    rolledFish = 0
    fishID = 0
    fishingPoints = 0
    randomizedFPoints = 0
    fishMultiplier = 0
    matatakiLocation = 0
    matatakiLocationID = 0
    duplicateRetries = 0
    generatedNeededFishCount = 0
    generatedMinFishSize = 0
    generatedMaxFishSize = 0

