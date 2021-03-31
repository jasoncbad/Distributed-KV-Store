#exec(open('testpython.py').read())

VIEW_LIST = ["10.10.0.3:13800", "10.10.0.4:13800","10.10.0.2:13800","10.10.0.1:13800"]
MAIN_ADDR = "10.10.0.3:13800"
NODE_ADDR = "10.10.0.3:13800"
ADDRESS_INDEX = VIEW_LIST.index(MAIN_ADDR)
NODE_NUMBER = ADDRESS_INDEX + 1
NODES_IN_VIEW = len(VIEW_LIST) + 1
REPL_FACTOR = 2
SHARD_LIST = []
REPLICA_ID = 0
SHARD_ID = 0

# +-----------------------+   +-----------------------+   +------------+   +------------+
# |   node1               |   |   node2               |   |   node3    |   |   node4    |
# | --------------------- |   | --------------------- |   | ---------- |   | ---------- |
# |  shard1               |   |  shard1               |   |  shard2    |   |  shard2    |
# |  replica1             |   |  replica2             |   |  replica1  |   |  replica2  |
# | --------------------- |   | --------------------- |   | ---------- |   | ---------- |
# |  - key1               |   |  - key1               |   |  - key2    |   |  - key2    |
# |  - key3               |   |  - key3               |   |  - key4    |   |  - key4    |
# |  - key5               |   |  - key5               |   |  - key6    |   |  - key6    |
# |  - attending_class    |   |  - attending_class    |   |  - key8    |   |  - key8    |
# +-----------------------+   +-----------------------+   +------------+   +------------+
# 4 nodes 2 repl 
# N1 = S1 R1 | | N2 = S1 R2 | | N3 = S2 R1 | | N4 = S2 R2
# 6 nodes 3 repl
# N1 = S1 R1 | | N2 = S1 R2 | | N3 = S1 R3 | | N4 = S2 R1 | | N5 = S2 R2 | | N6 = S2 R3  
# 6 nodes 2 repl
# N1 = S1 R1 | | N2 = S1 R2 | | N3 = S2 R1 | | N4 = S2 R2 | | N5 = S3 R1 | | N6 = S3 R2
#

#assumes sorted VIEW_LIST
def make_shards():
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
            REPLICA_ID = replica_count
        if replica_count == REPL_FACTOR:
            SHARD_LIST.append(list(shard_list))
            if(MAIN_ADDR in shard_list):
                SHARD_ID = len(SHARD_LIST)
            shard_list.clear()
            replica_count = 0
    return

#set VIEW_LIST, NODE_ADDR, ADDRESS_INDEX, NODE_NUMBER, NODES_IN_VIEW, REPL_FACTOR, REPLICA_ID, SHARD_ID
def update_local_view(view_list, repl_factor):
    global VIEW_LIST
    global ADDRESS_INDEX
    global NODE_NUMBER
    global REPL_FACTOR
    global NODES_IN_VIEW
    VIEW_LIST.clear()
    VIEW_LIST = view_list.copy()
    VIEW_LIST.sort()
    ADDRESS_INDEX = VIEW_LIST.index(NODE_ADDR)
    NODE_NUMBER = ADDRESS_INDEX + 1
    NODES_IN_VIEW = len(VIEW_LIST) + 1
    REPL_FACTOR = repl_factor
    make_shards()
    print_node_data()
    return

def print_node_data():
    global VIEW_LIST
    global SHARD_LIST
    global REPLICA_ID
    global SHARD_ID
    print("View List:",*VIEW_LIST,"\n")
    for shards in SHARD_LIST:
        print("Shard:",SHARD_LIST.index(shards)+1,"\n")
        for node in shards:
            print(node," is in Shard : ",SHARD_LIST.index(shards) + 1,
            "\n Node is replica : ", shards.index(node) + 1, "\n")
    print("Node S",SHARD_ID," R",REPLICA_ID )


update_local_view(["10.10.0.3:13800", "10.10.0.4:13800","10.10.0.2:13800","10.10.0.1:13800"], 2)
print("\n**********\n")
update_local_view(["10.10.0.3:13800", "10.10.0.4:13800","10.10.0.2:13800","10.10.0.1:13800","10.10.0.5:13800","10.10.0.6:13800"], 2)
print("\n**********\n")
update_local_view(["10.10.0.3:13800", "10.10.0.4:13800","10.10.0.2:13800","10.10.0.1:13800","10.10.0.5:13800","10.10.0.6:13800"], 3)
print("\n**********\n")

print(SHARD_LIST[0][2])
print(len(SHARD_LIST))