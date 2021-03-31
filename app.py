# app.py
from flask import Flask, request, jsonify
import json
import os, requests
import hashlib
import math
import traceback
from requests.exceptions import Timeout
app = Flask(__name__)
os.environ['PYTHONHASHSEED'] = '0'

# Important globals
storage = {}
TIMEOUT = 2
VECTOR_CLOCK = []

# History is a list of events.
# Note: history is not ordered so use the vector clock values for ordering
# Events are logged as follows:
#   ["PUT"/"GET", key, value_after_operation, clock_after_operation]
HISTORY = []
COUNT_MESSAGE_SENDS = False
COUNT_MESSAGE_RECEIVES = False
COUNT_SUCCESSFUL_READS = True
COUNT_SUCCESSFUL_WRITES = True
COUNT_SUCCESSFUL_DELETES = False
PRINT_STATEMENTS_ON = True

# Configuration of environment variables and building context variables
MAIN_ADDR = os.getenv('ADDRESS')
VIEW = os.getenv('VIEW')

VIEW_LIST = VIEW.split(",")
VIEW_LIST.sort()

if(MAIN_ADDR in VIEW_LIST):
    ADDRESS_INDEX = VIEW_LIST.index(MAIN_ADDR)
else:
    ADDRESS_INDEX = 0

NODE_NUMBER = ADDRESS_INDEX + 1

NODES_IN_VIEW = len(VIEW_LIST)
REPL_FACTOR = int(os.getenv('REPL_FACTOR'))

SHARD_LIST = []
NUMBER_OF_SHARDS = NODES_IN_VIEW / REPL_FACTOR
REPLICA_ID = 0
SHARD_ID = 0

# ==============================================================================
# ------------------------------------------------------------------------------
# HELPER FUNCTIONS
# ------------------------------------------------------------------------------
# ==============================================================================

# observes all event tuples in the history list involving key 'key'
# and determines which of those events happened last
def findLatestEvent(key):
    winner = None
    first = True
    for tuple in HISTORY:
        if (tuple[1] == key):
            if first:
                winner = tuple
                first = False
                continue
            winner = compareTupleToWinner(tuple, winner)
    if first == True:
        return None
    else:
        return winner

# compares two tuples of the history log,
# observes both vector clocks and determines if the candidate tuple has a
# strictly greater than Vector clock of the winner
def compareTupleToWinner(tuple, winner):
    for x in range(3, REPL_FACTOR + 3):
        if (tuple[x] < winner[x]):
            return winner
    return tuple

# observes the tuples of events in the history log and
# determines if there are at least 2 tuples involving key 'key'
# in which neither clock associated with each event can be said to be bigger than the other
# UNDER CONSTRUCTION.
# dont think this function is needed
def conflictTest(key):
    # first see if there is no tuple, return None
    exists = False
    return_list = []
    for tuple in HISTORY:
        if (tuple[1] == key):
            exists = True
            break
    if not exists:
        return True
    else:
        return False

# performs the set union of the context list and our history of events
# no duplicates allowed
def portNewEvents(context):
    global HISTORY

    #print("\t\tport: history -> ", HISTORY, flush=True)
    #print("\t\tport: context -> ", context, flush=True)

    HISTORY = [tuple(t) for t in HISTORY]
    HISTORY_SET = set(HISTORY)

    context = [tuple(v) for v in context]
    context_set = set(context)

    new_history = list(set(HISTORY_SET) | set(context_set))

    HISTORY = new_history
    return


# Takes the pairwise max of all events in the context, merges that vector clock
# with out own
def mergeClockWithContext(context, gossip=False):
    # print("\tCLOCK MERGED.. (jk)", flush=True)

    CLOCK = []
    global VECTOR_CLOCK

    for y in range(REPL_FACTOR):
        CLOCK.append(0)

    for event in context:
        for x in range(REPL_FACTOR):
            CLOCK[x] = max(CLOCK[x], int(event[x+3]))

    #print("CLOCK: ", CLOCK, flush=True)
    #print("VECTOR_CLOCK: ", VECTOR_CLOCK, flush=True)

    for number in CLOCK:
        for x in range(REPL_FACTOR):
            VECTOR_CLOCK[x] = max(VECTOR_CLOCK[x], CLOCK[x])

    if gossip:
        print("\tgossip: CLOCK UPDATED TO ", VECTOR_CLOCK, flush=True)
    else:
        print("\tclient reqest: CLOCK UPDATED TO ", VECTOR_CLOCK, flush=True)

    return


# turns the causal-context object in a JSON request into a List of lists in the
# form:
#   [[Event1],[Event2],[Event3]...[EventN]]
def contextToList(contextObject):
    list = []
    #print("\tCONTEXT FOUND: ", contextObject, flush=True)

    # if this line doesnt cause problems this entire function may be redundant.
    # nonetheless, this function exists in case more processing needs to be
    # done on causal contexts
    list = contextObject.copy()

    return list


# creates a list representing the event, the vector clock of the process
# is incremented during this method
def logEvent(operation, subject_key, value_after_operation):
    # increment clock
    clockIncrement()

    # create event
    event = []
    event.append(operation)
    event.append(subject_key)
    event.append(value_after_operation)

    for x in VECTOR_CLOCK:
        event.append(x)

    #event.append(VECTOR_CLOCK)

    # send event to history
    HISTORY.append(tuple(event))

    print("\tNEW EVENT:  ", flush=True)
    print("\t\t", event, flush=True)

    # return event
    return event

def getJSONObjFromDict(json_response):
    json_dump = json.dumps(json_response)
    json_object = json.loads(json_dump)
    return json_object

def shardIndex():
    return SHARD_ID
def replicaIndex():
    return REPLICA_ID

#shards works using VIEW_LIST and assumes the addresses to be sorted
def makeShards():
    global SHARD_LIST
    global VIEW_LIST
    global MAIN_ADDR
    global REPLICA_ID
    global SHARD_ID

    SHARD_LIST.clear()
    shard_list = []
    replica_count = 0

    for address in VIEW_LIST:
        shard_list.append(address)
        replica_count += 1
        if MAIN_ADDR == address:
            REPLICA_ID = replica_count-1
        if replica_count == REPL_FACTOR:
            SHARD_LIST.append(shard_list.copy())
            if(MAIN_ADDR in shard_list):
                SHARD_ID = len(SHARD_LIST) - 1
            shard_list.clear()
            replica_count = 0

    return

#
def updateLocalView(view_list, repl_factor):
    global VIEW_LIST
    global ADDRESS_INDEX
    global NODE_NUMBER
    global REPL_FACTOR
    global NODES_IN_VIEW
    global NUM_OF_SHARDS

    VIEW_LIST.clear()
    VIEW_LIST = view_list.copy()
    VIEW_LIST.sort()
    if(MAIN_ADDR in VIEW_LIST):
        ADDRESS_INDEX = VIEW_LIST.index(MAIN_ADDR)
    else:
        ADDRESS_INDEX = 0
    
    NODE_NUMBER = ADDRESS_INDEX + 1
    NODES_IN_VIEW = len(VIEW_LIST)
    REPL_FACTOR = int(repl_factor)
    clockInitialize()
    NUM_OF_SHARDS = int(NODES_IN_VIEW / REPL_FACTOR)
    makeShards()
    return

def printNodeData():
    print("----------------------------------------")
    print("\nView List:",*VIEW_LIST,"\n")
    for shards in SHARD_LIST:
        print("Shard:",SHARD_LIST.index(shards)+1)
        for node in shards:
            print("\t" + node, "\tReplica", shards.index(node) + 1,flush=True)
    print("\nReplication Factor: ", REPL_FACTOR,flush=True)
    print("\tMY VECTOR CLOCK IS: ", VECTOR_CLOCK, flush=True)
    print("\n----------------------------------------", flush=True)
    return

def print_clock(msg):
    print("\t", VECTOR_CLOCK, " -- ", msg, flush=True)
    return

def clockInitialize():
    VECTOR_CLOCK.clear()
    for r in range(REPL_FACTOR):
        VECTOR_CLOCK.append(0)
    return

def clockReset():
    for c in range(REPL_FACTOR):
        VECTOR_CLOCK[c] = 0
    return

def clockIncrement():
    VECTOR_CLOCK[replicaIndex()] += 1
    return

def clockMerge(clock1, clock2):
    # assert(len(clock1) == len(clock2))
    mergedClock = []
    for c in range(REPL_FACTOR):
        mergedClock[c] = max(clock1[c], clock2[c])
    return mergedClock

def updateClock(method = 'DEFAULT'):

    if (method == 'DEFAULT'):
        clockIncrement()
        print_clock("DEFAULT")
        return

    if (method == 'SEND'):
        if(COUNT_MESSAGE_SENDS):
            clockIncrement()
            print_clock("SEND")
            return
    if (method == 'READ'):
        if(COUNT_SUCCESSFUL_READS):
            clockIncrement()
            print_clock("READ")
            return

    if (method == 'WRITE'):
        if (COUNT_SUCCESSFUL_WRITES):
            clockIncrement()
            print_clock("WRITE")
            return

    if (method == 'GET'):
        if (COUNT_MESSAGE_RECEIVES):
            clockIncrement()
            print_clock("GET")
            return

    if (method == 'PUT'):
        if (COUNT_MESSAGE_RECEIVES):
            clockIncrement()
            print_clock("PUT")
            return
    if (method == 'DELETE'):
        if (COUNT_SUCCESSFUL_DELETES):
                clockIncrement()
                print_clock("DELETE")
        if (COUNT_MESSAGE_SENDS):
            clockIncrement()
            print_clock("SEND")

def printDestination(shard):
    if(PRINT_STATEMENTS_ON):
        if(MAIN_ADDR in SHARD_LIST[shard]):
            print("No need to proxy.", flush=True)
        else:
            print("Sending request to shard '", shard, "', address are ", *SHARD_LIST[shard], flush=True)

# ==============================================================================
# ------------------------------------------------------------------------------
# INITIALIZATION OF NODE
# ------------------------------------------------------------------------------
# ==============================================================================

templist = VIEW_LIST.copy()
updateLocalView(templist, REPL_FACTOR)
clockInitialize()
printNodeData()

# ==============================================================================
# ------------------------------------------------------------------------------
# APP ROUTES
# ------------------------------------------------------------------------------
# ==============================================================================

# default home page
@app.route('/')
def hello_world():
    return 'hello, world!'

# route for key/value store
@app.route('/kvs/keys/<key>', methods=['GET','PUT','DELETE'])
def keys(key):
    # use the key to determine which node will execute the request
    hash_value = hash(key)
    shard = hash_value % NUM_OF_SHARDS
    printDestination(shard)

    # PROXY CODE
    if not (MAIN_ADDR in SHARD_LIST[shard]):
        try:

            context = request.json.get('causal-context').get('events')
            if context == None:
                context = []
            if request.method =='PUT':
                result = requests.put('http://%s/kvs/keys/%s'%(SHARD_LIST[shard][0], key),
        							json={'value':request.json['value'],
                                        'causal-context':{'events':context}},
        							headers = {"Content-Type": "application/json"},
                                    timeout=TIMEOUT)
            elif request.method =='GET':
                result = requests.get('http://%s/kvs/keys/%s'%(SHARD_LIST[shard][0], key),
        							json={'causal-context':{'events':context}},
        							headers = {"Content-Type":"application/json"},
                                    timeout=TIMEOUT)
            elif request.method =='DELETE':
                result = requests.delete('http://%s/kvs/keys/%s'%(SHARD_LIST[shard][0], key),
        							headers = {"Content-Type": "application/json"},
                                    timeout=TIMEOUT)
            else:
                return 'impossible'
            pythondict = result.json()
            d1 = {"address" : SHARD_LIST[shard][0]}
            pythondict.update(d1)
            return jsonify(pythondict), result.status_code
        except Exception as ex:

            print(" exception: ", ex, flush=True)

            # NOTE: in the above code, we only attempt to reach out to one replica
            # in the target shard. We aren't sure whether or not to pursue other
            # replicas, but ideally what that would look like is paralell requests
            # being send and monitoring those responses
            return jsonify(error="Unable to satisfy request",
                message="Error in " + request.method,
                status_code=503), 503

    # enforce key length
    if len(key) > 50:
        return jsonify(error='Key is too long',
            message='Error in ' + request.method,
            status_code=400), 400

    # CONTEXT PROCESSING -------------------------------------------------------
    try:

        # convert the supplied context JSON object to a list of lists
        json_data = request.json
        context = json_data.get('causal-context').get('events')
        if context == None:
            context = []
        contextList = contextToList(context)

        # NEW: Save our vector clock before merging

        # merge our clock with the clock of the latest event in the supplied context
        mergeClockWithContext(contextList)

        # perform the union of the context and our history
        portNewEvents(contextList)

        # implement Events in a causal order using implementEvents()
        success = implementEvents()

        # by this point, any changes that this client has missed out on are now
        # applied in a causal order.

        # the operation can now be performed as normally below..

    except Exception as ex:
        print(" exception in context processing: ", ex, flush=True)

    print("\tHISTORIES MERGED: ", flush=True)
    for i in HISTORY:
        print("\t\t", i , flush=True)

    try:
        # GET METHOD --------------------------------------------------
        if request.method == 'GET':

            x = storage.get(key) # operation occurs here
            if x == None:
                key_exists = False
            else:
                key_exists = True

            # find latest event involving the key
            #latest_event = findLatestEvent(key)

        # if a latest event was detected..
        #if not latest_event == None:
            # update/insert our value for that key, send the value to the client
            #if key_exists:
            #    if not x == latest_event[2]:
            #        # update our copy of the value
            #        storage[key] = latest_event[2]
            #else:
                # key did not exist in our system, but we have knowledge of
                # an event that did observe the key's value
                # insert the key into our data
            #    storage[key] = latest_event[2]

            if key_exists:
                newEvent = logEvent("GET", key, x)
                print("\tEVENT LOGGED.. ", flush=True)

                # this error checking covers case if client with no context
                context = json_data.get('causal-context').get('events')
                if context == None:
                    context = []
                context.append(newEvent)

                gossipBroadcast()

                json_response = {"doesExist":True,
                    "message":"Retrieved successfully",
                    "value":x,
                    "causal-context":{'events':context},
                    "status_code":200}

                return getJSONObjFromDict(json_response), json_response['status_code']
            else:
                # key doesnt exist on this node, even after observing the causal
                # history, send DNE response
                json_response = {"doesExist":False,
                    "error":"Key does not exist","message":"Error in GET",
                    "causal-context":{'events':context},
                    "status_code":404}

                return getJSONObjFromDict(json_response), json_response['status_code']

            #else:
                # even if two concurrent events were detected, the code in
                # findLatestEvent() resolves this conflic for us and picks one

                # SO: causal violation!
                # return error: unable to satisfy request
                #json_response = {"error":"Unable to satisfy request",
            #        "message":"Error in GETs"}
            #    return getJSONObjFromDict(json_response), 400


        # PUT method --------------------------------------------------
        elif request.method == 'PUT':
            # determine an already existing pair?
            has_key = key in storage

            # enforce non-null value
            json_value = request.json['value']
            if not json_value:
                return jsonify(error="Value is missing",
                    message="Error in PUT",
                    status_code=400), 400

            # find latest event involving the key
            # latest_event = findLatestEvent(key)

            # perform the operation
            storage[key] = json_value

            # logging of event.
            newEvent = logEvent("PUT", key, json_value)
            print("\tEVENT LOGGED.. ", flush=True)

            # GOSSIP_CALL
            # gossipBroadcast()
            # checking to make sure no issue if no context provided
            context = json_data.get('causal-context').get('events')
            if context == None:
               context = []
            
            context.append(newEvent)

            gossipBroadcast()
            #print("\tHISTORY UPDATED: ", HISTORY, flush=True)

            json_response = {"causal-context":{"events":context}}

            if not has_key:
                json_response['message'] = "Added successfully"
                json_response['replaced'] = False
                json_response['status_code'] = 201
            else:
                json_response['message'] = "Updated successfully"
                json_response['replaced'] = True
                json_response['status_code'] = 200

            return getJSONObjFromDict(json_response), json_response['status_code']


        # delete method. NOT IMPORTANT FOR NOW
        elif request.method == 'DELETE':
            # perform operation and return
            if not storage.pop(key) == None:
                # prepare to respond
                updateClock('DELETE')
                return jsonify(doesExist=True,
                    message="Deleted successfully",
                    status_code=200), 200
            else:
                return jsonify(doesExist=False,
                    error="Key does not exist",
                    message="Error in DELETE",
                    status_code=404), 404

        # unsupported method
        else:
            return 'Method not Allowed', 405
    except Exception as ex:
        traceback.print_exc()
        print(" exception in operation execution: ", ex, flush=True)
        return


# KEY COUNT
# Gets the total number of keys stored by this node
# and returns its shard id
@app.route('/kvs/key-count', methods=['GET'])
def keyCount():
    key_count = len(storage)

    return {"message":"Key count retrieved successfully",
        "key-count":key_count,
        "shard-id":SHARD_ID}, 200

# GET ID for each shard
# The response should contain the id of each shard.
@app.route('/kvs/shards', methods=['GET'])
def shards():
    shard_array = []
    for index in range(NUM_OF_SHARDS):
        shard_array.append(index)

    return {"message":"Shard membership retrieved successfully",
        "shards":shard_array}

# GET information for a specific shard
# get the number of keys stored by a shard and
# what node each replica is stored on.
@app.route('/kvs/shards/<id>', methods=['GET'])
def shards_id(id):
    printDestination(int(id))
    if (int(id) == SHARD_ID):
        # they are inquiring about THIS shard
        return {"message":"Shard information retrieved successfully",
        "shard-id": int(id),
        "key-count": len(storage),
        "replicas": SHARD_LIST[int(id)] }, 200

    else:
        result = requests.get('http://%s/kvs/shards/%s'%(SHARD_LIST[int(id)][0], id),
        							headers = {"Content-Type": "application/json"},
                                    timeout=TIMEOUT)
        return result.content, result.status_code

        # they are inquiring about another node, send this request to one (or all)
        # of the nodes for the target shard




# VIEW CHANGE
# Responsible for handling a PUT request for a view change.
#
# 1. Change this nodes view
# 2. Call the updateView endpoint on all other nodes, telling them to update
#       their views.
# 3. Tell all the other nodes to reshard their keys by calling the
#       reconcilePartition endpoint.
# 4. Reshard THIS node's keys by calling the method reconcilePartition()
# 5. Finally, construct the response to the client according to the spec.
#
#
@app.route('/kvs/view-change', methods=['PUT'])
def viewChange():
    print(request.json['view'], flush=True)

    # STEP 1A: Change this node's view!
    global VIEW_LIST
    global VIEW
    VIEW = request.json['view']
    new_repl_factor = request.json['repl-factor']


    # the list of nodes who recieve view change request is in full_list
    # cant be in VIEW_LIST as that causes an issue where VIEW_LIST still includes the removed node
    # while another node is trying to send new keys some of which get redirected to removed node
    # full_list is union of old VIEW_LIST and new VIEW_LIST
    full_list = list(set(VIEW_LIST) | set(VIEW.split(",")))
    VIEW_LIST.clear()
    VIEW_LIST = VIEW.split(",")
    print (VIEW_LIST)
    print (full_list)

    # Keep the original address string to send to other nodes
    address_string = request.json['view']
    print (address_string)

    # STEP 1B: Propagate the view update to every node:
    for address in full_list:
        if address != MAIN_ADDR:
            try:
                print("updating view")
                requests.put('http://%s/kvs/updateView'%(address),
                                        json={'view' : address_string,
                                              'repl-factor' : new_repl_factor},
            							headers = {"Content-Type": "application/json"},
                                        timeout=TIMEOUT)
            except Timeout as ex:
                print('Exception Raised: ', ex, flush=True)
                return jsonify(error="Target node is down. Cannot perform view-change! [view-change1]",
                    message="Error in " + request.method,
                    status_code=503), 503
                # This is a bandaid solution, because 'this' node performed the view change, along
                # with X other nodes that successfully changed views before we encountered a down node.
                # We will have to tackle this problem soon. We have 6 total seconds to perform a view-change.

    templist = VIEW_LIST.copy()
    updateLocalView(templist, new_repl_factor)
    # STEP 2A: RESHARD OF THE KEYS (for all nodes but this one)
    # PROBLEM? Does the code above truly ensure that a proper request was recieved for
    #     every node?
    for address in full_list:
        if address != MAIN_ADDR:
            try:
                print("doing partition")
                requests.get('http://%s/kvs/reconcilePartition'%(address),
            							headers = {"Content-Type": "application/json"},
                                        timeout=TIMEOUT)
            except:
                return jsonify(error="Target node is down. Cannot perform view-change! [view-change2]",
                    message="Error in " + request.method,
                    status_code=503), 503
                # another bandaid solution that we may or may not have to fix this project

    # STEP 2B: RESHARD OF THE KEYS (for this node)

    reconcilePartition()
    # STEP 3: CONSTRUCT THE RESPONSE TO CLIENT

    shard_list = [] # a list of dictionaries representing each shard
    print("Collecting Responses", flush=True)
    for shard in range(NUM_OF_SHARDS):
        if not MAIN_ADDR in SHARD_LIST[shard]:
            try:
                print("Requesting shard information from",SHARD_LIST[shard][0])
                response = requests.get('http://%s/kvs/shards/%d'%(SHARD_LIST[shard][0],shard),
                                        timeout=TIMEOUT)
                response_data = response.json()
                shard_id = response_data['shard-id']
                key_count = response_data['key-count']
                replicas = SHARD_LIST[shard]
                print("Shard return values of ", shard_id, key_count, replicas)
                shard_list.append({'shard-id': shard_id, 'key-count': key_count, 'replicas': replicas})
            except:
                traceback.print_exc()
                return jsonify(error="Target node is down. Cannot perform view-change! [view-change3]",
                    message="Error in " + request.method,
                    status_code=503), 503
        else:
            print("Main address has shard information", SHARD_ID,len(storage),*SHARD_LIST[shard])
            shard_list.append({'shard-id': SHARD_ID, 'key-count': len(storage), 'replicas': SHARD_LIST[shard]})

    return jsonify(message="View change successful",
        shards=shard_list), 200


# RECONCILE PARTITION (ROUTE)
# Used as a bridge to the function responsible for resharding keys among nodes.
#
#
@app.route('/kvs/reconcilePartition', methods=['GET'])
def reconcilePartitionRoute():
    reconcilePartition()
    return jsonify(message="View change successful"), 200


# RECONCILE PARTITION (FUNCTION)
# Method responsible for resharding the keys among the nodes.
#
# 1) Maintain a list of keys to delete once they've been sent to their new home.
#      - Doing it on the fly causes a runtime exception (see note)
# 2) For every key in the storage, compute the hash and then the new node (index
#      in the VIEW_LIST). If the key no longer belongs on this node, send the
#      key-value pair to its new home using a PUT request. Append the key to a
#      delete_list for deletion later.
# 3) Delete moved keys from storage.
#
#
def reconcilePartition():
    # create a list of pairs to delete once we send them to other nodes, see note below
    delete_list = []

    for key in storage:
        hash_value = hash(key)
        shard = hash_value % NUM_OF_SHARDS
        if not MAIN_ADDR in SHARD_LIST[shard]:
            delete_list.append(key)
        #for each node in shard
        #send new key
        #if you would send to yourself, don't
        for replica in range(REPL_FACTOR):
            if not (SHARD_LIST[shard][replica] == MAIN_ADDR):
                try:
                    result = requests.put('http://%s/kvs/reconcilePartition/%s'%(SHARD_LIST[shard][replica], key),
                                            json={'value':storage.get(key)
                                                },
                                            headers = {"Content-Type": "application/json"},
                                            timeout=TIMEOUT)
                except Timeout as ex:
                    print('Exception Raised: ', ex, flush=True)
                    return jsonify(error="Target node is down. Cannot perform view-change! [reconcilePartition1]",
                        message="Error in " + request.method,
                        status_code=503), 503

    # NOTE: we need to delete moved keys from this node after sending them off
    # because the first loop breaks if we delete it on the fly:
    # RuntimeError: dictionary changed size during iteration
    for key in delete_list:
        storage.pop(key)

    return


# UPDATE VIEW
# Responsible for updating this nodes view.
# Modifies the VIEW and VIEWLIST global variables in preparation for resharding
#       of keys, based on the supplied VIEW environment variable.
@app.route('/kvs/updateView', methods=['PUT'])
def updateView():
    global VIEW
    VIEW = request.json['view']
    new_repl_factor = request.json['repl-factor']
    new_view_list = VIEW.split(",")
    updateLocalView(new_view_list,new_repl_factor)
    return jsonify(message="Update view successful!"), 200

# This endpoint receives a PUT request from other nodes.
# The PUT request contains a JSON object containing a list of events.
# The purpose of this gossipReceive function is to incoporporate those events
# into our history.
#
# - Unpackage the JSON object into a list of events using contextToList()
# - use mergeClockWithContext() to update this clock
# - use portNewEvents() to import those events into our history
# - update values stored in the kvs with latest value
# - currently issue with incrementing the clock correctly
#
# The JSON object can be named whatever, "payload", "causal-context"..etc
# Just make sure it matches when sending the request to this endpoint, which
# would be after calls to logEvent() above.
#
@app.route('/kvs/gossip', methods=['PUT'])
def gossip():
    print("handling request", flush = True)
    # this catches context and makes changes based on what it can see
    # recieves causal context, compare the vector clocks
    # if this clocks just greater then ez dub do nothing
    # if the other clock is greater implement events on that clock until no longer the case (7,0) rec on (0,0) -> 7,7
    # else either (1,0) (0,1) or (1,1) (1,1) second case is ez solution
    # default to more events done or default to lowest index
    # in (1,0) to (0,1) choose lowest index in 2,0 to 0,1 choose 2,0
    # helper compare clocks and sum clocks
    global VECTOR_CLOCK
    json_data = request.json
    context = json_data.get('causal-context').get('events')
    if context == None:
        context = []
    contextList = contextToList(context)
    #print (contextList)


    # merge our clock with the clock of the latest event in the supplied context
    mergeClockWithContext(contextList, gossip=True)

    # perform the union of the context and our history
    portNewEvents(contextList)

    try:

        # apply the updates in causal order by observing our history
        sucess = implementEvents()

    except Exception as ex:
        print(' error implementing events: ', ex, flush=True)

    print("\tGossip resolved! my new clock is now ", VECTOR_CLOCK, flush=True)

    return jsonify(doesExist=True,
                    message="gossip successful",
                    status_code=200), 200
#{
#   "causal-context": {}
#....
#}
#[Event] [event] [event]
#[ PUT, x, 1, [1 ,0]]
def implementEvents():
    #return 1
    #old_clock = VECTOR_CLOCK.copy() #copy or bad things happen
    for key in getKeyList():
        #perform the first
        # dont perform action if a more recent one has been done relative to old clock so comparable
        #increment our clock

        # find the latest event involving the key
        latest = findLatestEvent(key)

        # next step would be to have findLatestEvent(key) detect two events involving
        # the key that are not strictly greater than eachother
        storage[latest[1]] = latest[2]
        print("\timplementing event: KV pair (",latest[1], ",",latest[2], ") refreshed..", flush=True)

        #print("adding to storage  " + storage.get(latest[1]), flush=True)
        #clockIncrement() this needs to be done for each event not for
        #could also just set clock

        #print clock
    return 1

# return list of all keys events have interacted with
def getKeyList():
    keys = []
    for events in HISTORY:
        #print(events, flush=True)
        key = events[1]
        if not key in keys and not events[0] == 'INIT':
            keys.append(key)
    return keys

@app.route('/kvs/reconcilePartition/<key>', methods=['PUT'])
def partitionNoGossip(key): 

    json_value = request.json['value']
    storage[key] = json_value

    return 200

#sends put request to all other replicas in the shard
def gossipBroadcast():
    global SHARD_LIST
    # take list of replicas exclude current address\
    # send a request to everyone in list message includes events + vector clock
    # if we recieve no response from one time out and keep going the values from these arent used anyway so could make these async later
    # reminder that async does not gel well with default programming style so dont use until the end
    # send vector_clock and event_list
    for replica in range(0, REPL_FACTOR):

        if SHARD_LIST[SHARD_ID][replica] != MAIN_ADDR:

            historyList = []
            for element in range(0, len(HISTORY)):
                listItem = list(HISTORY[element])
                historyList.append(listItem)
                #converted from tuples to lists
            try:
                result = requests.put('http://%s/kvs/gossip'%(SHARD_LIST[SHARD_ID][replica]),
                                    json={  'causal-context': {'events': historyList}},
        	    					headers = {"Content-Type": "application/json"},
                                    timeout=TIMEOUT)
            except Exception as ex:
                print(" exception: ", ex, flush=True)
            # could print result of gossip for testing so lets do that right now
            print("sent gossip to: " + SHARD_LIST[SHARD_ID][replica] + " received", flush=True)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=13800)
