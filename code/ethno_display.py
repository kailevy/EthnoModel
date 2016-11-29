from mesa.visualization.modules import CanvasGrid
from mesa.visualization.ModularVisualization import ModularServer

from ethno import EthnoModel

COLOR_KEY = {1:"#ff7c7a", 2:"#81ff7a", 3:"#7aadff", 4:"#faff7a"}
# 1: pink, 2: green, 3: blue, 4: yellow
TEXT_KEY = {0b111:"H", 0b100:"E", 0b011:"T", 0b000:"S", 0b010:"wT", 0b101: "wA", 0b001:"pT", 0b110:"A"}
# SHAPE_KEY = {0:"rect", 1: "circle"}
# FILL_KEY = {0: False, 1: True}

def agent_portrayal(agent):
    portrayal = {"Shape": "rect",
                 "Filled": True,
                 "Layer": 0,
                 "Color": COLOR_KEY[agent.tag],
                #  "text": TEXT_KEY[agent.behavior],
                 "text": str(bin(agent.behavior))[2:],
                 "text_color": "black",
                 "r": 0.75,
                 "w":0.8,
                 "h":0.8}
    return portrayal

grid = CanvasGrid(agent_portrayal, 50, 50, 1000, 1000)
server = ModularServer(EthnoModel,
                       [grid],
                       "Ethnocentrism Model",
                       10, 50, 50, 1, 0.005)
server.port = 8889
server.launch()
