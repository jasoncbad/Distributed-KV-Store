#all nodes keep a vector clock consisiting of all nodes in the view
#upon receiving a message from another node they merge clocks
#upon receiving a message from another node, the nodes merge clocks

#keys are stored with a dict that holds the value and a vector clock from
#the time of the write

event = (key[value,vector clock])

causal-context = dict{event}
storage(event)

#gossip works like before

#clients store the events theyve witnessed as a dictionary of 
#events

#merge clientclock
#merge clock
#allowread(causal-context)
#writeandupdate causal-context