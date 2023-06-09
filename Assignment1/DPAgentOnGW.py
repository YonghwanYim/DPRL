import numpy as np
from GridWorldEnv_DP import GWE_Trap

class AgentOnGW:
    def __init__(self, env):
        self.env = env
        self.nA = env.get_action_space()
        self.nr, self.nc = env.get_state_space()
        self.nS = self.nr * self.nc
        self.gamma = 0.9   # discount factor
        self.reset_all()

    # self.V : value for each cell
    def reset_V(self, v=0.0):
        if 'V' not in dir(self):  # locals()
            self.V = np.zeros(self.nS, float)
        self.V.fill(v)

    # self.Q : value for each state-action pair (sr, sc, a)
    def reset_Q(self, v=0.0):
        if 'Q' not in dir(self):  # locals()
            nSA = self.get_nSA()
            self.Q = np.zeros(nSA, float)
        self.Q.fill(v)

    # self.pi : policy for each state-action pair (sr, sc)
    def reset_policy(self):
        if 'pi' not in dir(self):
            self.pi = np.zeros(self.nS, int)  # policy function
        else:
            self.pi.fill(0)

    def reset_all(self):
        self.reset_V()
        self.reset_Q()
        self.reset_policy()
        if 'optimalQ' in dir(self):
            del(self.optimalQ)

    def get_nSA(self):
        return (self.nS, self.nA)

    def rc_to_index(self, r, c):
        return r*self.nc + c

    def index_to_rc(self, idx):  # idx --> (r, c)
        return idx // self.nc, idx % self.nc

    def get_Q_2D(self):
        # reshape does not make a new copy of Q
        return self.Q.reshape((self.nr, self.nc, self.nA))

    def get_V_2D(self):
        # reshape does not make a new copy of Q
        return self.V.reshape((self.nr, self.nc))


# Agent with Dynamic Programming capability
class DPAgentOnGW(AgentOnGW):
    def __init__(self, env):
        super().__init__(env)
        self.T, self.R = self.get_model()

    def get_model(self):
        T = [None] * self.nA
        R = np.zeros((self.nS, self.nA))

        for action in range(self.nA):
            Ta = np.zeros((self.nS, self.nS))
            for sr in range(self.nr):
                for sc in range(self.nc):
                    s = self.rc_to_index(sr, sc)
                    self.env.move_to(sr, sc)
                    transition = self.env.get_transition(sr, sc, action)
                    for (tr, tc) in transition.keys():
                        tran = transition[(tr, tc)]
                        s_next = self.rc_to_index(tr, tc)
                        Ta[s, s_next] = tran[0]
                        R[s, action] += tran[1]

            T[action] = Ta

        return T, R

    '''
    Problem 1: Policy evauation step

    Evaluate the current action values for all the state-action pairs
    '''
    def pe_step(self):
        newQ = np.zeros((self.nS, self.nA))
        for s in range(self.nS):
            for a in range(self.nA):
                newQ[s][a] = self.R[s][a] + (self.gamma * self.T[a][s] * self.V).sum()

        self.Q = newQ  # sync. backup
        for s in range(self.nS):
            a = self.pi[s]
            self.V[s] = self.Q[s][a]

    '''
    Problem 2: Greedy policy improvement

    Improve the current policy greedily
    '''
    def greedy_policy_improve(self):
        for s in range(self.nS):
            self.pi[s] = np.argmax(self.Q[s])

    def policy_evaluation(self, max_iter_eval=100):
        for k in range(max_iter_eval):
            self.pe_step()

    def policy_iteration(self, max_iter, max_iter_eval=100):
        self.greedy_policy_improve()   # initial policy
        for k in range(max_iter):
            self.policy_evaluation(max_iter_eval)
            self.greedy_policy_improve()

    '''
    Problem 3: Value Iteration step

    Update the action values for all the state-action pairs
    '''
    def vi_step(self):   # async backup
        for s in range(self.nS):
            for a in range(self.nA):
                self.Q[s][a] = self.R[s][a] + (self.gamma * self.T[a][s] * self.V).sum()

        self.V = np.max(self.Q, axis=1)  # compute V from Q for display purpose

    def value_iteration(self, max_iter=100):
        self.greedy_policy_improve()  # initial policy
        for k in range(max_iter):
            self.vi_step()
