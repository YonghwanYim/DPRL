import numpy as np
from matplotlib import pyplot as plt


class AgentOnGW:
    def __init__(self, env):
        self.env = env
        self.nA = env.get_action_space()
        self.nr, self.nc = env.get_state_space()
        self.nS = self.nr * self.nc
        self.gamma = env.gamma  # discount factor
        self.reset_all()

    # self.V : value for each cell
    def reset_V(self, v=0.0):
        if 'V' not in dir(self):  # locals()
            self.V = np.zeros(self.nS, float)
        self.V.fill(v)

    # self.Q : value for each state-action pair (s, a)
    def reset_Q(self, v=0.0):
        if 'Q' not in dir(self):  # locals()
            nSA = self.get_nSA()
            self.Q = np.zeros(nSA, float)
        self.Q.fill(v)

    # self.pi : policy for each state
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
            del (self.optimalQ)

    def get_nSA(self):
        return (self.nS, self.nA)

    def rc_to_index(self, r, c):
        return r * self.nc + c

    def index_to_rc(self, idx):  # idx --> (r, c)
        return idx // self.nc, idx % self.nc

    def get_Q_2D(self):
        # reshape does not make a new copy of Q
        return self.Q.reshape((self.nr, self.nc, self.nA))

    def get_V_2D(self):
        # reshape does not make a new copy of Q
        return self.V.reshape((self.nr, self.nc))

    def get_V_from_Q(self):
        self.V = np.max(self.Q, axis=1)  # compute V from Q for display purpose

    def optimality_gap(self):
        if 'Q' not in dir(self):
            return 0
        if 'optimalQ' not in dir(self):
            dpa = DPAgentOnGW(self.env)
            dpa.gamma = self.gamma
            dpa.value_iteration(max_iter=100)
            self.optimalQ = dpa.Q
            self.optimalV = dpa.V

        diff = (self.V - self.optimalV)
        L2 = np.sqrt(np.mean(diff ** 2))
        return L2

    def getStatusMsg(self):
        return "Opt. gap = %.2f  " % self.optimality_gap()


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

    def pe_step(self):
        max_dev = 0.0
        newQ = np.zeros((self.nS, self.nA))
        for s in range(self.nS):
            for a in range(self.nA):
                value = 0.
                for next_s in range(self.nS):
                    value += self.T[a][s, next_s] * self.Q[next_s, self.pi[next_s]]
                newQ[s, a] = self.R[s, a] + self.gamma * value
                dev = np.abs(newQ[s, a] - self.Q[s, a])
                if dev > max_dev:
                    max_dev = dev
        self.Q = newQ  # sync. backup
        self.get_V_from_Q()  # compute V from Q for display purpose
        return max_dev

    def greedy_policy_improve(self):
        greedy_actions = np.argmax(self.Q, axis=1)
        n_changed = (greedy_actions != self.pi).sum()
        self.pi = greedy_actions
        return n_changed > 0

    def policy_evaluation(self, max_iter_eval=100, eps=1e-4):
        for k in range(max_iter_eval):
            dev = self.pe_step()
            if dev < eps:
                return

    def policy_iteration(self, max_iter, max_iter_eval=100):
        self.greedy_policy_improve()  # initial policy
        for k in range(max_iter):
            self.policy_evaluation(max_iter_eval)
            policy_changed = self.greedy_policy_improve()
            if not policy_changed:
                break

    def vi_step(self):  # async backup
        max_dev = 0.0
        for a in range(self.nA):
            for s in range(self.nS):
                maxQ = np.max(self.Q, axis=1)
                newQ = self.R[s, a] + self.gamma * np.dot(self.T[a][s, :], maxQ)
                dev = np.abs(newQ - self.Q[s, a])
                if dev > max_dev:
                    max_dev = dev
                self.Q[s, a] = newQ
        self.get_V_from_Q()  # compute V from Q for display purpose
        return max_dev

    def value_iteration(self, max_iter=10000, eps=1e-4):
        self.greedy_policy_improve()  # initial policy
        for k in range(max_iter):
            dev = self.vi_step()
            if dev < eps:
                break


# Agent with Monte-Carlo control capability
class MCControlOnGW(AgentOnGW):
    def __init__(self, env):
        super().__init__(env)
        self.eps = 0.5
        self.reset_episode()

    def get_state(self):
        return self.env.observe()

    def reset_episode(self):
        # self.env.reset()
        self.env.reset(0.7)  # 70% random start, 30% start at (0,0)
        if 'n_episode' not in dir(self):
            self.n_episode = 0
        self.n_episode += 1

    # self.NV : visit count for each state (grid)
    # self.NQ : visit count for each state-action pair
    def reset_NV(self):
        if 'NV' not in dir(self):  # locals()
            self.NV = np.zeros(self.nS, int)
        else:
            self.NV.fill(0)
        if 'NQ' not in dir(self):  # locals()
            self.NQ = np.zeros(self.get_nSA(), int)
        else:
            self.NQ.fill(0)

    def reset_all(self):
        super().reset_all()
        self.reset_NV()

    def set_alpha(self, const_alpha=True, p_or_v=0.5):
        self.const_alpha = const_alpha
        # const_alpha = True -> learning rate: self.alpha
        # const_alpha = False  -> learning rate: (1/N)**p
        self.alpha = p_or_v
        self.p = p_or_v

    '''
    Task 1: Epsilon-greedy policy function

    Get action from epsilon-greedy policy
    '''

    def eps_greedy_policy(self, eps):
        p = np.random.random()

        if p <= eps:
            return np.random.randint(0, self.nA)
        else:
            s = self.get_state()
            return np.argmax(self.Q[s, :])

    # policy function
    def get_action(self):
        s = self.get_state()
        if self.NV[s] == 0:  # epsilon is state-dependent
            self.eps = 1.0
        else:
            self.eps = 1 / (self.NV[s] ** 0.5)

        return self.eps_greedy_policy(self.eps)

    # Simulate 1 episode through current policy & value function
    def get_episode(self, max_step=1000):
        self.reset_episode()
        S = []
        A = []
        R = []
        S.append(self.get_state())
        n_step = 0
        while n_step < max_step:
            a = self.get_action()
            A.append(a)
            ns, reward, done = self.env.step(a)
            R.append(reward)
            S.append(ns)
            n_step += 1
            if done: break
        return S, A, R, done

    # Calculate G(t) for each t
    def calc_return(self, R):
        n = len(R)
        G = np.zeros(n, float)
        g = 0.0
        for i in range(n - 1, -1, -1):  # calc. return backward
            g = self.gamma * g + R[i]
            G[i] = g
        return G

    '''
    Task 2: MC prediction & control

    Update the value functions through MC algorithm
    '''

    def run_episode(self, max_step=1000):
        S, A, R, terminated = self.get_episode(max_step)
        G = self.calc_return(R)
        n = len(R)

        cur_episode = np.zeros((self.nS, self.nA))
        for i in range(n):
            self.NQ[S[i]][A[i]] += 1
            self.NV[S[i]] += 1

            if cur_episode[S[i]][A[i]] == 0:
                self.Q[S[i]][A[i]] = self.Q[S[i]][A[i]] + (1 / self.NQ[S[i]][A[i]]) * (G[i] - self.Q[S[i]][A[i]])
                self.V[S[i]] = max(self.Q[S[i]])

            cur_episode[S[i]][A[i]] += 1

        self.pi = np.argmax(self.Q, axis=1)

        return 0

    def run_simulation(self, n_episode, n_step):
        gaps = []
        for _ in range(n_episode):
            self.run_episode(max_step=n_step)
            self.get_V_from_Q()
            if n_episode >= 1000:
                gaps.append(self.optimality_gap())

        if n_episode >= 1000:
            plt.figure(figsize=(8, 6))
            plt.title('Learning plot of MC', fontsize=15)
            plt.plot(gaps)
            plt.xlabel('Episodes', fontsize=15)
            plt.ylabel('Opt. gap', fontsize=15)
            plt.show()

    def getStatusMsg(self):
        s1 = super().getStatusMsg()
        s1 += "# of episodes = %d" % (self.n_episode - 1)
        return s1


# Agent with Temporal-Difference control capability
class TDControlOnGW(MCControlOnGW):
    def __init__(self, env):
        super().__init__(env)
        self.alpha = 0.5
        self.p = 1.0
        self.td_method = 'Q-Learn'  # can be 'SARSA' or 'ExpSARSA'
        self.const_alpha = True
        self.t_env = 0

    def set_td_method(self, td_method='Q-Learn'):
        self.td_method = td_method

    def reset_all(self):
        super().reset_all()

    '''
    Task 3: TD prediction & control

    Update the value functions through TD algorithms
    '''

    def run_episode(self, max_step=1000):
        act = self.get_action()
        n_step = 0
        while n_step < max_step:
            n_step += 1
            s = self.get_state()
            self.NV[s] += 1
            self.NQ[s][act] += 1
            sp, reward, done = self.env.step(act)

            if self.env.is_terminal():  # terminal node
                self.Q[sp] = 0.0
            if self.const_alpha:
                alpha = self.alpha  # learning rate
            else:
                alpha = 1 / (self.NQ[s][act] ** self.p)  # learning rate

            if self.td_method == 'SARSA':
                next_act = self.get_action()
                self.Q[s][act] = self.Q[s][act] + alpha * (reward + self.gamma * self.Q[sp][next_act] - self.Q[s][act])
                act = next_act

            elif self.td_method == 'Q-Learn':
                self.Q[s][act] = self.Q[s][act] + alpha * (reward + self.gamma * np.max(self.Q[sp]) - self.Q[s][act])
                act = self.get_action()

            else:  # self.update == 'ExpSARSA'
                expectation = (1 - self.eps) * np.max(self.Q[sp]) + self.eps * np.mean(self.Q[sp])
                self.Q[s][act] = self.Q[s][act] + alpha * (reward + self.gamma * expectation - self.Q[s][act])
                act = self.get_action()

            if done:
                self.reset_episode()
                break

        if not done:
            self.reset_episode()

    def run_simulation(self, n_episode, n_step=1000):
        self.t_env = 0
        gaps = []
        for i in range(n_episode):
            self.run_episode(max_step=n_step)
            self.get_V_from_Q()
            if n_episode >= 1000:
                gaps.append(self.optimality_gap())
            self.t_env += 1

        if n_episode >= 1000:
            plt.figure(figsize=(8, 6))
            title = f"Learning plot of {self.td_method}"
            plt.title(title, fontsize=15)
            plt.plot(gaps)
            plt.xlabel('Episodes', fontsize=15)
            plt.ylabel('Opt. gap', fontsize=15)
            plt.show()
