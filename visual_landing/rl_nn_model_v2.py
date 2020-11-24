import torch
import cv2 as cv
import torch.nn as nn
import torch.nn.functional as F
from torch.distributions import MultivariateNormal
from visual_landing.memory_leak import debug_gpu
import torchvision.models as tvmodels
import numpy as np
import torchvision.models as models

"""
MECHANICAL ENGINEERING POST-GRADUATE PROGRAM
UNIVERSIDADE FEDERAL DO ABC - SANTO ANDRÉ, BRASIL

NOME: RAFAEL COSTA FERNANDES
RA: 21201920754
E−MAIL: COSTA.FERNANDES@UFABC.EDU.BR

DESCRIPTION:
    PPO neural network model
    hidden layers has 64 neurons
"""
H0 = 2**12
H1 = 2**11
H11 = 128
H2 = 2**10
SENS_SIZE = 75
class Flatten(nn.Module):
    def forward(self, input):
        return input.view(input.size(0), -1)
    
def plot_conv(x, name):
    for channel in x[0]:
        image = ((channel-channel.min())/(channel.max()-channel.min()+1e-8)).detach().cpu().numpy()
    cv.imshow('conv_in_'+str(name), image)
    cv.waitKey(1)
    return

def plot_conv3D(x, name):
    for channel in x[0, 0]:
        image = ((channel-channel.min())/(channel.max()-channel.min()+1e-8)).detach().cpu().numpy()
    cv.imshow('conv_in_'+str(name), image)
    cv.waitKey(1)
    return

class conv_forward(nn.Module):
    def __init__(self, T, child):
        self.child = child
        super(conv_forward, self).__init__()
        
        self.conv_1 = nn.Conv2d(in_channels = 3, out_channels = 100, kernel_size=(3,3), stride=(1,1), padding=(1, 1))
        self.conv_2 = nn.Conv2d(in_channels = 100, out_channels = 200, kernel_size=(3,3), stride=(1,1), padding=(1, 1))
        self.conv_3 = nn.Conv2d(in_channels = 200, out_channels = 300, kernel_size=(3,3), stride=(1,1), padding=(1, 1))
        # self.conv_4 = nn.Conv2d(in_channels = 256, out_channels = 128, kernel_size=(2,2), stride=(1,1), padding=(1, 1))
        self.fc_1 = nn.Linear(300*12**2, H0)
        
    def forward(self, x):

        x = F.elu(self.conv_1(x))
        x = torch.max_pool2d(x, 2)
        # plot_conv(x, 1)

        x = F.elu(self.conv_2(x))
        x = torch.max_pool2d(x, 2)
        # plot_conv(x, 2)
        

        x = F.elu(self.conv_3(x))
        x = torch.max_pool2d(x, 2)
        # if not self.child:
        #     plot_conv(x, 3)
        
        # x = torch.tanh(self.conv_4(x))
        # x = torch.max_pool2d(x, 2)
        # plot_conv(x, 4)
        # print(x.size())
        x = F.elu(self.fc_1(torch.flatten(x, start_dim=1)))

        return x

class conv3D_forward(nn.Module):
    def __init__(self, T, child):
        super(conv3D_forward, self).__init__()
        self.mother = not(child)
        self.conv_1 = nn.Conv3d(in_channels = 3, out_channels = 60, kernel_size=(2,3,3), stride=(1,1,1), padding=(0, 1, 1))
        self.conv_2 = nn.Conv3d(in_channels = 60, out_channels = 120, kernel_size=(2,3,3), stride=(1,1,1), padding=(0, 1, 1))
        self.conv_3 = nn.Conv2d(in_channels = 120, out_channels = 180, kernel_size=(3,3), stride=(1,1), padding=(1, 1))
        self.fc_1 = nn.Linear(180*10**2, H0)
        
    def forward(self, x):
        x = F.elu(self.conv_1(x))
        x = torch.max_pool3d(x, (1,2,2))
        # if self.mother:
        #     plot_conv3D(x, 1)

        x = F.elu(self.conv_2(x))
        x = torch.max_pool3d(x, (1,2,2))
        # if self.mother:
        #     plot_conv3D(x, 2)
        
        x = torch.squeeze(x, dim=2)
        x = F.elu(self.conv_3(x))
        x = torch.max_pool2d(x, (2,2))
        # if self.mother:
        #     plot_conv3D(x, 3)

        # print(x.size())        
        x = F.elu(self.fc_1(torch.flatten(x, start_dim=1)))

        return x


class actor_nn(nn.Module):
    def __init__(self, T, child=False):
        super(actor_nn, self).__init__()  
        self.conv_ac = conv3D_forward(T, child)
        self.fc_1 = nn.Linear(H0+SENS_SIZE, H1)                
        self.fc_2 = nn.Linear(H1, H2)
        self.fc_21 = nn.Linear(H2, H2)
        self.fc_3 = nn.Linear(H2, 3)
        
    def forward(self, image, sens):
        # print('Actor')
        x = self.conv_ac(image)
        # x_2 = self.conv_ac(image[:,1,:,:,:])
        # x_3 = self.conv_ac(image[:,2,:,:,:])
        # x_4 = self.conv_ac(image[:,3,:,:,:])
        # x = torch.cat((x_1, x_2, x_3, x_4), dim=1)
        # x = torch.cat((x_1, x_2), dim=1)
        # x = self.conv_ac(image)
        x = torch.cat((x, sens), dim=1)
        x = torch.tanh(self.fc_1(x))
        x = torch.tanh(self.fc_2(x))        
        # x = F.elu(self.fc_21(x))        
        x = torch.tanh(self.fc_3(x))
        # print(x)
        return x
    
class critic_nn(nn.Module):
    def __init__(self, T, child=False):
        super(critic_nn, self).__init__() 
        
        self.conv_ct = conv3D_forward(T, child)
        
        self.fc_1 = nn.Linear(H0+SENS_SIZE+3, H1)                
        self.fc_2 = nn.Linear(H1, H2)
        # self.fc_21 = nn.Linear(H2, H2)
        self.fc_3 = nn.Linear(H2, 1)
        
    def forward(self, image, sens, action):
        # print('Critic')
        # print(x)
        x = self.conv_ct(image)
        # x_1 = self.conv_ct(image[:,0,:,:,:])
        # x_2 = self.conv_ct(image[:,1,:,:,:])
        # x_3 = self.conv_ct(image[:,2,:,:,:])
        # x_4 = self.conv_ct(image[:,3,:,:,:])
        # x = torch.cat((x_1, x_2, x_3, x_4), dim=1)
        # x = torch.cat((x_1, x_2), dim=1)
        # x = self.conv_ct(image)
        x = torch.cat((x, sens, action), dim=1)
        x = torch.tanh(self.fc_1(x))
        x = torch.tanh(self.fc_2(x))   
        # x = F.elu(self.fc_21(x))   
        x = self.fc_3(x)
        # print(x)
        return x 
 
    
             
class ActorCritic(nn.Module):
    def __init__(self, T, action_dim, action_std, child = False):
        super(ActorCritic, self).__init__()        
        if child:
            self.device = torch.device("cpu")
        else:
            self.device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
            # self.device = torch.device("cpu")
       
        self.actor_nn = actor_nn(T, child).to(self.device)
        self.critic_nn = critic_nn(T, child).to(self.device)
        
        self.action_var = torch.full((action_dim,), action_std*action_std, device = self.device, dtype=torch.float)
        self.action_log_std = torch.full((1, action_dim), action_std, device=self.device)
    
    def __get_dist(self, action_mean):
        action_log_std = self.action_log_std.expand_as(action_mean).to(self.device)
        return torch.distributions.Normal(action_mean, action_log_std)
        
     
    def forward(self, image, sens):
        actor_output = self.actor_nn(image, sens)
        return actor_output

    def critic(self, image, sens, action):
        critic_output = self.critic_nn(image, sens, action)        
        return critic_output
        
        
        
    def act(self, state, sens, last_conv, memory):

        action_mean = self.forward(state, sens)

    
        dist = self.__get_dist(action_mean)
        action = dist.sample()
        
        state_value = self.critic(state, sens, action)
        
        
        action_logprob = dist.log_prob(action)
        memory.append_memory_as(action.detach().cpu().numpy(), state.detach().cpu().numpy(), action_logprob.detach().cpu().numpy(), sens.detach().cpu().numpy(), state_value.detach().cpu().numpy())
            
        action = action.detach().cpu().numpy().flatten()       
        
        return action
    
    def evaluate(self, state, sens, action, last_conv):   
        action_mean = self.forward(state, sens)

        dist = self.__get_dist(action_mean)
        
        action_logprobs = dist.log_prob(action)
        dist_entropy = dist.entropy()
        state_value = self.critic(state, sens, action)
        return action_logprobs, torch.squeeze(state_value), dist_entropy