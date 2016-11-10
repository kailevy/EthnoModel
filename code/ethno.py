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
            if flip(self.model.mutate):
                tag = random.choice([i for i in range(1,TAGS+1) if not i==self.tag])
            else:
                tag = self.tag
            # use bitwise xor to flip binaries if mutating
            homo = int(flip(self.model.mutate))^self.homo
            hetero = int(flip(self.model.mutate))^self.hetero
            a = EthnoAgent(self.model.num_agents, self.model, tag, homo, hetero)
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
    def __init__(self, N, width, height, immigrate, mutate):
        """
        N: number of agents to start with
        """
        self.immigrate = immigrate
        self.mutate = mutate
        self.grid = MultiGrid(width, height, True)
        self.schedule = StagedActivation(self,stage_list=['get_ptr', 'reproduce', 'die'],shuffle=True)
        self.num_agents = self.new_agents(N)

    def new_agents(self, num):
        n = 0
        for i in range(num):
            a = EthnoAgent(i, self, random.randint(1, TAGS), random.randint(0,1), random.randint(0,1))
            x = random.randrange(self.grid.width)
            y = random.randrange(self.grid.height)
            if self.grid.is_cell_empty((x,y)):
                self.grid.place_agent(a, (x, y))
                self.schedule.add(a)
                n += 1
        return n

    def step(self):
        self.num_agents += self.new_agents(self.immigrate)
        self.schedule.step()
