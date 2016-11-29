from mesa.visualization.modules import CanvasGrid
from mesa.visualization.ModularVisualization import ModularServer

from ethno import EthnoModel

COLOR_KEY = {1:"#ff7c7a", 2:"#81ff7a", 3:"#7aadff", 4:"#faff7a"}
TEXT_KEY = {0b11:"H", 0b10:"E", 0b01:"T", 0b00:"S"}
SHAPE_KEY = {0:"rect", 1: "circle"}
FILL_KEY = {0: False, 1: True}

def agent_portrayal(agent):
    portrayal = {"Shape": SHAPE_KEY[agent.hetero],
                 "Filled": FILL_KEY[agent.homo],
                 "Layer": 0,
                 "Color": COLOR_KEY[agent.tag],
                 "text": TEXT_KEY[agent.behavior],
                 "text_color": "black",
                 "r": 0.75,
                 "w":0.6,
                 "h":0.6}
    return portrayal

grid = CanvasGrid(agent_portrayal, 50, 50, 750, 750)
server = ModularServer(EthnoModel,
                       [grid],
                       "Ethnocentrism Model",
                       10, 50, 50, 1, 0.005, [0b00, 0b01, 0b10, 0b11])
server.port = 8889
server.launch()
