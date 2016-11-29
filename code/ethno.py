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
    def __init__(self, id, model, tag, behavior):
        """
        id: unique model id, not actually unique
        model: the model
        tag: which public tag the agent has
        behavior: agent's behavior, encoded as 2-bit binary string where:
            - first bit is homogenous cooperation
            - second bit is heterogenous cooperation
        """
        super().__init__(id, model)
        self.tag = tag
        self.behavior = behavior
        self.homo = behavior // 2
        self.hetero = behavior % 2
        self.ptr = BASE_PTR
        self.neighborhood = None

    def reset_ptr(self):
        """
        resets the ptr of the agent and then adjusts it based off of neighbors
        """
        self.ptr = BASE_PTR

    def reproduce(self):
        """
        reproduces with a chance by the agent's ptr if there is an adjacent empty space
        and with mutations governed by the mutation rate
        """
        if not self.neighborhood:
            self.neighborhood = self.model.grid.get_neighborhood(self.pos, moore=False, include_center=False)
        adjacent_empty = [c for c in self.neighborhood if self.model.grid.is_cell_empty(c)]
        if flip(self.ptr) and adjacent_empty:
            if flip(self.model.mutate):
                tag = random.choice([i for i in range(1,TAGS+1) if not i==self.tag])
            else:
                tag = self.tag
            # use bitwise xor to flip binaries if mutating
            homo = int(flip(self.model.mutate))^self.homo
            hetero = int(flip(self.model.mutate))^self.hetero
            behavior = homo * 0b10 + hetero * 0b01
            if behavior not in self.model.allowed_behaviors:
                #ignore the mutation
                behavior  = self.behavior
            a = EthnoAgent(self.model.num_agents, self.model, tag, behavior)
            self.model.schedule.add(a)
            self.model.grid.place_agent(a, random.choice(adjacent_empty))
            self.model.num_agents += 1

    def die(self):
        """
        removes the agent by death rate
        """
        if flip(DEATH_RATE):
            self.model.schedule.remove(self)
            self.model.grid._remove_agent(self.pos, self)
            self.model.num_agents -= 1

    def play_neighbors(self):
        """
        adds to neighbor's ptr based off of whether we will cooperate (with perception error),
        and subtract from own
        """
        for neighbor in self.model.grid.get_neighbors(self.pos, moore=False, include_center=False, radius=1):
            misperceive = flip(self.model.misperception)
            if misperceive:
                neighbor_tag = random.choice([i for i in range(1,TAGS+1) if not i==neighbor.tag])
            else:
                neighbor_tag = neighbor.tag
            if self.tag == neighbor_tag:
                if self.homo:
                    neighbor.ptr += RECEIVE_PTR
                    self.ptr += GIVE_PTR
            else:
                if self.hetero:
                    neighbor.ptr += RECEIVE_PTR
                    self.ptr += GIVE_PTR

class EthnoModel(Model):
    def __init__(self, N, width, height, immigrate, mutate, misperception, allowed_behaviors=range(4), max_iters=2000):
        """
        N: number of agents to start with
        width: width of grid
        height: height of grid
        immigrate: number of random immigrants per round
        mutate: mutation rate
        allowed_behaviors: list of allowed behaviors (encoded as 2-bit binary string)
        max_iters: maximum number of steps to run
        """
        self.immigrate = immigrate
        self.mutate = mutate
        self.misperception = misperception
        self.grid = MultiGrid(width, height, True)
        self.running = True
        self.allowed_behaviors = allowed_behaviors
        self.max_iters = max_iters
        self.iter = 0
        self.schedule = StagedActivation(self,stage_list=['reset_ptr', 'play_neighbors', 'reproduce', 'die'],shuffle=True)
        self.num_agents = self.new_agents(N)
        default_data = {"Total Population": lambda m: m.num_agents,
                        "Selfish": lambda m: self.count_behavior(m, 0b00),
                        "Traitor": lambda m: self.count_behavior(m, 0b01),
                        "Ethnocentric": lambda m: self.count_behavior(m, 0b10),
                        "Humanitarian": lambda m: self.count_behavior(m, 0b11)}
        tag_behavior = {str(i)+BEHAVIOR_KEY[j]: lambda m,i=i,j=j: self.count_tag_behavior(m, i, j) for i in range(1, TAGS+1)
                        for j in range(4)}
        self.datacollector = DataCollector(model_reporters = {**default_data, **tag_behavior})

    def new_agents(self, num):
        """
        adds num new agents
        """
        n = 0
        for i in range(num):
            a = EthnoAgent(i, self, random.randint(1, TAGS), random.choice(self.allowed_behaviors))
            x = random.randrange(self.grid.width)
            y = random.randrange(self.grid.height)
            if self.grid.is_cell_empty((x,y)):
                self.grid.place_agent(a, (x, y))
                self.schedule.add(a)
                n += 1
        return n

    def step(self):
        """
        collects data, adds new agents by immigration, then lets all agents step
        """
        self.datacollector.collect(self)
        self.num_agents += self.new_agents(self.immigrate)
        self.schedule.step()
        self.iter += 1
        if self.iter > self.max_iters:
            self.running = False

    @staticmethod
    def count_behavior(model, behavior):
        """
        counts agents with a given behavior
        """
        count = 0
        for agent in model.schedule.agents:
            if agent.behavior == behavior:
                count += 1
        return count

    @staticmethod
    def count_tag_behavior(model, tag, behavior):
        """
        counts agents with a given tag and behavior
        """
        count = 0
        for agent in model.schedule.agents:
            if agent.tag == tag and agent.behavior == behavior:
                count += 1
        return count
