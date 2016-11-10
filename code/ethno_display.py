from mesa.visualization.modules import CanvasGrid
from mesa.visualization.ModularVisualization import ModularServer

from ethno import EthnoModel

LABEL_KEY = {1:"#ff7c7a", 2:"#81ff7a", 3:"#7aadff", 4:"#faff7a"}
BEHAVIOR_KEY = {0b11:"H", 0b10:"E", 0b01:"T", 0b00:"S"}

def agent_portrayal(agent):
    portrayal = {"Shape": "circle",
                 "Filled": "true",
                 "Layer": 0,
                 "Color": LABEL_KEY[agent.tag],
                 "text": BEHAVIOR_KEY[agent.behavior],
                 "text_color": "black",
                 "r": 0.5}
    return portrayal

grid = CanvasGrid(agent_portrayal, 40, 40, 800, 800)
server = ModularServer(EthnoModel,
                       [grid],
                       "Ethnocentrism Model",
                       10, 40, 40, 1, 0.05)
server.port = 8889
server.launch()
