# app.py
# TODO fix + "" jake removed from json returns
# TODO gossip before view change
import os, requests
import hashlib
import math
import json
NODES_IN_VIEW = 4
NODE_NUMBER = 2

class VectorClock:
    def __init__(self, vector, index = 0):
        self.vector = list(vector)
        self.index = index

    def print(self):
        print("[",*self.vector,"]")
    
    def reset(self):
        for c in range(len(self.vector)):
            self.vector[c] = 0
        return

    def increment(self):
        self.vector[self.index] += 1
        return

    def merge(self, clock = None):
        if(clock):
            if(len(self.vector) != len(clock.vector)):
                print("Invalid clock to merge")
                return
            for c in range(len(self.vector)):
                self.vector[c] = max(self.vector[c], clock.vector[c])

def allowRead(clientInfo, key):
    global storage
            
    if(not clientInfo):
        return True

    event = storage[key]
    witnessedevent = clientInfo[key]

    return False


key = "k"
value = "there"
time = [1,0,0,0]
VALUE = 0
CONTEXT = 1

event = [value,time]
storage = {key : event}
print(dict2[key][VALUE])
print(dict2[key][CONTEXT])




print("\n\n\n")
templist = [0,0,0,0]
templist2 = [0,0,0,4]

vc = VectorClock([0,0,0,0],2)
vc.increment()
vc.print()
vc.increment()
vc.increment()
vc.print()
vc.print()
incomingVC = VectorClock(templist2,4)
vc.merge(incomingVC)
vc.print()

clientTime = dict{storage}

key = "x"

vc.allowRead(clientTime,key)

