import sys
import gym
import pylab
import random
import numpy as np
from collections import deque
from keras.layers import Dense
from keras.optimizers import Adam
from keras.models import Sequential
from keras import backend as K

EPISODES = 10000
TEST = False # to evaluate a model
LOAD = False # to load an existing model


# this is Double DQN Agent
# it uses Neural Network to approximate q function
# and replay memory & target q network
class DoubleDQNAgent:
    def __init__(self, state_size, action_size):
        # if you want to see learning, then change to True
        self.render = False

        # get size of state and action
        self.state_size = state_size
        self.action_size = action_size

        # these is hyper parameters for the Double DQN
        self.discount_factor = 0.9
        self.learning_rate = 0.01
        if TEST:
            self.epsilon = 0.0
        else:
            self.epsilon = 1.0
        self.epsilon_decay = 0.9998
        self.epsilon_min = 0.01
        self.batch_size = 16
        self.train_start = 150
        # create replay memory using deque
        self.memory = deque(maxlen=750)

        # create main model and target model
        self.model = self._build_model()
        self.target_model = self._build_model()
        # copy the model to target model
        # --> initialize the target model so that the parameters of model & target model to be same
        self.update_target_model()


    # approximate Q function using Neural Network
    # state is input and Q Value of each action is output of network
    def _build_model(self):
        model = Sequential()
        model.add(Dense(24, input_dim=self.state_size, activation='relu', kernel_initializer='he_uniform'))
        #model.add(Dense(24, input_dim=self.state_size, activation='relu', kernel_initializer='he_uniform'))
        model.add(Dense(self.action_size, activation='linear', kernel_initializer='he_uniform'))
        model.summary()
        model.compile(loss='mse', optimizer=Adam(lr=self.learning_rate))
        return model

    # after some time interval update the target model to be same with model
    def update_target_model(self):
        self.target_model.set_weights(self.model.get_weights())

    # get action from model using epsilon-greedy policy
    def get_action(self, state):
        if np.random.rand() <= self.epsilon:
            return random.randrange(self.action_size)
        else:
            q_value = self.model.predict(state)
            return np.argmax(q_value[0])

    # save sample <s,a,r,s'> to the replay memory
    def replay_memory(self, state, action, reward, next_state, done):
        self.memory.append((state, action, reward, next_state, done))
        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay

    # pick samples randomly from replay memory (with batch_size)
    def train_replay(self):
        if len(self.memory) < self.train_start:
            return
        batch_size = min(self.batch_size, len(self.memory))
        mini_batch = random.sample(self.memory, batch_size)

        update_input = np.zeros((batch_size, self.state_size))
        update_target = np.zeros((batch_size, self.action_size))

        for i in range(batch_size):
            state, action, reward, next_state, done = mini_batch[i]
            target = self.model.predict(state)[0]

            # like Q Learning, get maximum Q value at s'
            # But from target model
            if done:
                target[action] = reward
            else:
                # the key point of Double DQN
                # selection of action is from model
                # update is from target model
                #t = self.target_model.predict(next_state)[0]
                #target[action] = reward + self.discount_factor * np.amax(t)
                a = np.argmax(self.model.predict(next_state)[0])
                target[action] = reward + self.discount_factor * \
                        (self.target_model.predict(next_state)[0][a])


            update_input[i] = state
            update_target[i] = target

        # make minibatch which includes target q value and predicted q value
        # and do the model fit!
        self.model.fit(update_input, update_target, batch_size=batch_size, epochs=1, verbose=0)

    # load the saved model
    def load_model(self, name):
        self.model.load_weights(name)

    # save the model which is under training
    def save_model(self, name):
        self.model.save_weights(name)


if __name__ == "__main__":
    # in case of CartPole-v1, you can play until 500 time step
    env = gym.make('FrozenLake-v0')
    # get size of state and action from environment

    state_size = 2#env.observation_space.n
    action_size = env.action_space.n

    agent = DoubleDQNAgent(state_size, action_size)

    scores, episodes = [], []

    for e in range(EPISODES):
        done = False
        score = 0
        state = env.reset()
        beenToLoc = [state]

        x = state%4
        y = int(np.floor(state/4))
        state = np.reshape([x, y], [1, state_size])

        if LOAD:
            agent.load_model("./FrozenLake_DoubleDQN.h5")

        while not done:
            if agent.render:
                env.render()

            # get action for the current state and go one step in environment
            action = agent.get_action(state)
            next_state, reward, done, info = env.step(action)

            if next_state == 15 and done:
                reward += 100

            beenToLoc += [next_state]
            newx = next_state%4
            newy = int(np.floor(next_state/4))
            next_state = np.reshape([newx, newy], [1, state_size])



            if not TEST:
                # save the sample <s, a, r, s'> to the replay memory
                agent.replay_memory(state, action, reward, next_state, done)
                # every time step do the training
                agent.train_replay()
            score += reward
            state = next_state

            if done:
                env.reset()
                # every episode update the target model to be same with model
                agent.update_target_model()

                scores.append(score)
                episodes.append(e)
                pylab.plot(episodes, scores, 'b')
                pylab.savefig("./FrozenLake_DoubleDQN.png")
                print("episode: {:3}   score: {:8.6}   memory length: {:4}   epsilon {:.3}"
                            .format(e, score, len(agent.memory), agent.epsilon))

                # if the mean of scores of last 10 episode is bigger than X
                # stop training
                if np.mean(scores[-min(10, len(scores)):]) >= 100:
                    agent.save_model("./FrozenLake_DoubleDQN.h5")
                    sys.exit()

        # save the model every N episodes
        if e % 10 == 0:
            agent.save_model("./FrozenLake_DoubleDQN.h5")