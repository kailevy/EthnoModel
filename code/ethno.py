from mesa import Agent, Model
from mesa.space import MultiGrid
from mesa.time import StagedActivation
from mesa.datacollection import DataCollector
import random

TAGS = 4
BASE_PTR = 0.12
RECEIVE_PTR = 0.03
GIVE_PTR = -0.01
DEATH_RATE = 0.1
BEHAVIOR_KEY = {0b11:"H", 0b10:"E", 0b01:"T", 0b00:"S"}

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
        self.behavior = 0b10 * self.homo + 0b01 * self.hetero
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
                    self.ptr += GIVE_PTR
                if neighbor.homo:
                    self.ptr += RECEIVE_PTR
            else:
                if self.hetero:
                    self.ptr += GIVE_PTR
                if neighbor.hetero:
                    self.ptr += RECEIVE_PTR

class EthnoModel(Model):
    def __init__(self, N, width, height, immigrate, mutate, max_iters=2000):
        """
        N: number of agents to start with
        """
        self.immigrate = immigrate
        self.mutate = mutate
        self.grid = MultiGrid(width, height, True)
        self.running = True
        self.max_iters = max_iters
        self.iter = 0
        self.schedule = StagedActivation(self,stage_list=['get_ptr', 'reproduce', 'die'],shuffle=True)
        self.num_agents = self.new_agents(N)
        self.datacollector = DataCollector(
            model_reporters = {"Total Population": lambda m: m.num_agents,
                            "Selfish": lambda m: self.count_behavior(m, 0b00),
                            "Traitor": lambda m: self.count_behavior(m, 0b01),
                            "Ethnocentric": lambda m: self.count_behavior(m, 0b10),
                            "Humanitarian": lambda m: self.count_behavior(m, 0b11)})

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
        self.datacollector.collect(self)
        self.num_agents += self.new_agents(self.immigrate)
        self.schedule.step()
        self.iter += 1
        if self.iter > self.max_iters:
            self.running = False

    @staticmethod
    def count_behavior(model, behavior):
        count = 0
        for agent in model.schedule.agents:
            if agent.behavior == behavior:
                count += 1
        return count
