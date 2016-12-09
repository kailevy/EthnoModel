from mesa import Agent, Model
from mesa.space import MultiGrid
from mesa.time import StagedActivation
from mesa.datacollection import DataCollector
import random
import numpy as np

TAGS = 4
BASE_PTR = 0.12
RECEIVE_PTR = 0.03
GIVE_PTR = -0.01
DEATH_RATE = 0.1
BEHAVIOR_KEY = {0b11:"H", 0b10:"E", 0b01:"T", 0b00:"S"}

def flip(p):
    return random.random() < p

class EthnoAgent(Agent):
    def __init__(self, id, model, tag, behavior, misperception):
        """
        id: unique model id, not actually unique
        model: the model
        tag: which public tag the agent has
        behavior: agent's behavior, encoded as 2-bit binary string where:
            - first bit is homogenous cooperation
            - second bit is heterogenous cooperation
        misperception: agent's misperception rate
        """
        super().__init__(id, model)
        self.tag = tag
        self.behavior = behavior
        self.misperception = misperception
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
            misperception = self.misperception + random.uniform(self.model.max_misperception * self.model.misp_mutate,
                                                self.model.max_misperception * -1*self.model.misp_mutate) # 10% misperception mutation
            # limit between 0 and max
            misperception = max(0, misperception)
            misperception = min(self.model.max_misperception, misperception)
            if behavior not in self.model.allowed_behaviors:
                #ignore the mutation
                behavior  = self.behavior
            a = EthnoAgent(self.model.num_agents, self.model, tag, behavior, misperception)
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
            # self.model.total_interactions += 1
            misperceive = flip(self.misperception)
            neighbor_tag = neighbor.tag
            if misperceive:
                neighbor_tag = random.randint(1,TAGS)
            if self.tag == neighbor_tag:
                if self.homo:
                    neighbor.ptr += RECEIVE_PTR
                    self.ptr += GIVE_PTR
                    # self.model.total_coops += 1
            else:
                if self.hetero:
                    neighbor.ptr += RECEIVE_PTR
                    self.ptr += GIVE_PTR
                    # self.model.total_coops += 1

class EthnoModel(Model):
    def __init__(self, N, width, height, immigrate, mutate, max_misperception, misp_mutate, allowed_behaviors=range(4), max_iters=2000):
        """
        N: number of agents to start with
        width: width of grid
        height: height of grid
        immigrate: number of random immigrants per round
        mutate: mutation rate
        max_misperception: maximum misperception rate for agents
        allowed_behaviors: list of allowed behaviors (encoded as 2-bit binary string)
        max_iters: maximum number of steps to run
        """
        self.immigrate = immigrate
        self.mutate = mutate
        self.max_misperception = max_misperception
        self.misp_mutate = misp_mutate
        self.grid = MultiGrid(width, height, True)
        self.running = True
        self.allowed_behaviors = allowed_behaviors
        self.total_interactions = 0
        self.total_coops = 0
        self.max_iters = max_iters
        self.iter = 0
        self.schedule = StagedActivation(self,stage_list=['reset_ptr', 'play_neighbors', 'reproduce', 'die'],shuffle=True)
        self.num_agents = self.new_agents(N)
        default_data = {"Total Population": lambda m: m.num_agents,
                        "Selfish": lambda m: self.count_behavior(m, 0b00),
                        "Traitor": lambda m: self.count_behavior(m, 0b01),
                        "Ethnocentric": lambda m: self.count_behavior(m, 0b10),
                        "Humanitarian": lambda m: self.count_behavior(m, 0b11),
                        "Misperception Mean": lambda m: self.misperception_mean(m),
                        "Misperception Median": lambda m: self.misperception_median(m),
                        "Misperception StdDev": lambda m: self.misperception_stdev(m)}
        tag_behavior = {str(i)+BEHAVIOR_KEY[j]: lambda m,i=i,j=j: self.count_tag_behavior(m, i, j) for i in range(1, TAGS+1)
                        for j in range(4)}
        self.datacollector = DataCollector(model_reporters = {**default_data, **tag_behavior})

    def new_agents(self, num):
        """
        adds num new agents
        """
        n = 0
        for i in range(num):
            a = EthnoAgent(i, self, random.randint(1, TAGS), random.choice(self.allowed_behaviors), random.uniform(0, self.max_misperception))
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
    def calc_misperception(model):
        """
        Calculates mean, median, standard dev of misperception trait
        """
        misperceptions = []
        for agent in model.schedule.agents:
            misperceptions.append(agent.misperception)
        return (np.mean(misperceptions), np.median(misperceptions), np.std(misperceptions))

    @staticmethod
    def misperception_mean(model):
        """
        Calculates mean, median, standard dev of misperception trait
        """
        misperceptions = []
        for agent in model.schedule.agents:
            misperceptions.append(agent.misperception)
        return np.mean(misperceptions)

    @staticmethod
    def misperception_median(model):
        """
        Calculates mean, median, standard dev of misperception trait
        """
        misperceptions = []
        for agent in model.schedule.agents:
            misperceptions.append(agent.misperception)
        return np.median(misperceptions)

    @staticmethod
    def misperception_stdev(model):
        """
        Calculates mean, median, standard dev of misperception trait
        """
        misperceptions = []
        for agent in model.schedule.agents:
            misperceptions.append(agent.misperception)
        return np.std(misperceptions)

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

def plot_stats(m):
    data = m.datacollector.get_model_vars_dataframe()
    ax = data[["Ethnocentric","Humanitarian", "Selfish", "Traitor"]].plot()
    ax.set_title("Population and Behavior Over Time")
    ax.set_xlabel("Step")
    ax.set_ylabel("Number of Agents")
    _ = ax.legend(bbox_to_anchor=(1.35, 1.025))
    ax2 = data[["Misperception Mean", "Misperception Median"]].plot()
    ax2.set_title("Misperception Stats Over Time")
    ax2.set_xlabel("Step")
    ax2.set_ylabel("Number of Agents")
    _ = ax2.legend(bbox_to_anchor=(1.35, 1.025))
