"""
Authors: Wouter Van Gansbeke, Simon Vandenhende
Licensed under the CC BY-NC 4.0 license (https://creativecommons.org/licenses/by-nc/4.0/)
"""
import torch
import torch.nn as nn
import torch.nn.functional as F


class ContrastiveModel(nn.Module):
    def __init__(self, backbone, head='mlp', middle_dim = 256, features_dim=128):
        super(ContrastiveModel, self).__init__()
        self.backbone = backbone['backbone']
        self.backbone_dim = backbone['dim']
        self.head = head
        self.middle_dim = middle_dim
 
        if head == 'linear':
            self.contrastive_head = nn.Linear(self.backbone_dim, features_dim)

        # elif head == 'mlp':
        #     self.contrastive_head = nn.Sequential(
        #             nn.Linear(self.backbone_dim, self.middle_dim),
        #             nn.ReLU(), nn.Linear(self.middle_dim, self.middle_dim), nn.ReLU())
        elif head == 'mlp':
            self.contrastive_head = nn.Sequential(
                    nn.Linear(self.backbone_dim, self.middle_dim),
                    nn.ReLU(), nn.Linear(self.middle_dim, self.middle_dim), nn.ReLU(),nn.Linear(self.middle_dim, features_dim), nn.ReLU())
        
        
        else:
            raise ValueError('Invalid head {}'.format(head))

    def forward(self, x):
        features = self.contrastive_head(self.backbone(x))
        features = F.normalize(features, dim = 1)
        return features

class SupervisedModel(nn.Module):
    def __init__(self, backbone, middle_dim = 256, features_dim = 128, number_of_classes=6):
        super(SupervisedModel, self).__init__()
        self.backbone = backbone['backbone']
        self.backbone_dim = backbone['dim']
        self.middle_dim = middle_dim
        self.contrastive_head = nn.Sequential(
                    nn.Linear(self.backbone_dim, self.middle_dim),
                    nn.ReLU(), nn.Linear(self.middle_dim, self.middle_dim), nn.ReLU(),nn.Linear(self.middle_dim, features_dim), nn.ReLU())
        #self.contrastive_model = model
        self.supervised_head = nn.Linear(features_dim, number_of_classes)
    def forward(self, x, forward_pass = 'backbone'):
        #hidden = self.contrastive_model(x)
        if forward_pass == 'backbone':
            hidden = self.backbone(x)
            out = hidden 
        elif forward_pass == 'head':

            hidden_feature = self.contrastive_head(x)
            logits = self.supervised_head(hidden_feature)
            out = logits
            #out = {'features': hidden_feature, 'logits': logits}
        elif forward_pass == 'default':
            hidden = self.backbone(x)
            logits = self.supervised_head(self.contrastive_head(hidden))
            out = logits
        elif forward_pass == 'return_all':
            hidden = self.backbone(x)
            hidden_feature = self.contrastive_head(hidden)
            logits = self.supervised_head(hidden_feature)
            #out = logits
            out = {'features': hidden_feature, 'output': logits}
        else:
            raise ValueError('Invalid forward pass {}'.format(forward_pass))
        return out





class ClusteringModel(nn.Module):
    def __init__(self, backbone, nclusters, nheads=1):
        super(ClusteringModel, self).__init__()
        self.backbone = backbone['backbone']
        self.backbone_dim = backbone['dim']
        self.nheads = nheads
        assert(isinstance(self.nheads, int))
        assert(self.nheads > 0)
        self.cluster_head = nn.ModuleList([nn.Linear(self.backbone_dim, nclusters) for _ in range(self.nheads)])

    def forward(self, x, forward_pass='default'):
        if forward_pass == 'default':
            features = self.backbone(x)
            out = [cluster_head(features) for cluster_head in self.cluster_head]

        elif forward_pass == 'backbone':
            out = self.backbone(x)

        elif forward_pass == 'head':
            out = [cluster_head(x) for cluster_head in self.cluster_head]

        elif forward_pass == 'return_all':
            features = self.backbone(x)
            out = {'features': features, 'output': [cluster_head(features) for cluster_head in self.cluster_head]}
        
        else:
            raise ValueError('Invalid forward pass {}'.format(forward_pass))        

        return out
