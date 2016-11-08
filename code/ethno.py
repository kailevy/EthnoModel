from mesa import Agent, Model
from mesa.space import MultiGrid
from mesa.time import StagedActivation
import random

TAGS = 4
BASE_PTR = 0.12
DEATH_RATE = 0.1

def flip(p):
    return random.random() < p

class EthnoAgent(Agent):
    def __init__(self, id, model, tag, homo, hetero):
        """
        id: unique model id, not actually unique
        model: the model
        tag: which public tag the agent has
        homo: whether or not the agent helps those with the same tag
        hetero: whether or not the agent helps those with different tag
        """
        super().__init__(id, model)
        self.tag = tag
        self.homo = homo
        self.hetero = hetero
        self.ptr = BASE_PTR
        self.neighborhood = None

    def get_ptr(self):
        self.ptr = BASE_PTR
        self.play_neighbors()

    def reproduce(self):
        if not self.neighborhood:
            self.neighborhood = self.model.grid.get_neighborhood(self.pos, moore=True, include_center=False)
        adjacent_empty = [c for c in self.neighborhood if self.model.grid.is_cell_empty(c)]
        if flip(self.ptr) and adjacent_empty:
            a = EthnoAgent(self.model.num_agents, self.model, self.tag, self.homo, self.hetero)
            self.model.schedule.add(a)
            self.model.grid.place_agent(a, random.choice(adjacent_empty))
            self.model.num_agents += 1

    def die(self):
        if flip(DEATH_RATE):
            self.model.schedule.remove(self)
            self.model.grid._remove_agent(self.pos, self)
            self.model.num_agents -= 1


    def play_neighbors(self):
        for neighbor in self.model.grid.get_neighbors(self.pos, moore=True, include_center=False, radius=1):
            if neighbor.tag == self.tag:
                if self.homo:
                    self.ptr -= 0.01
                if neighbor.homo:
                    self.ptr += 0.03
            else:
                if self.hetero:
                    self.ptr -= 0.01
                if neighbor.hetero:
                    self.ptr += 0.03

class EthnoModel(Model):
    def __init__(self, N, width, height):
        """
        N: number of agents to start with
        """
        self.grid = MultiGrid(width, height, True)
        self.schedule = StagedActivation(self,stage_list=['get_ptr', 'reproduce', 'die'],shuffle=True)
        self.num_agents = N

        for i in range(N):
            a = EthnoAgent(i, self, random.randint(1, TAGS), random.randint(0,1), random.randint(0,1))
            self.schedule.add(a)
            # Add the agent to a random grid cell
            x = random.randrange(self.grid.width)
            y = random.randrange(self.grid.height)
            self.grid.place_agent(a, (x, y))

    def step(self):
        self.schedule.step()
