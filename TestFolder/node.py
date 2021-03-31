
class Node():
    def __init__(self, *args, **kwargs):
        self.view = os.getenv('VIEW')
        self.view_list = self.view.split
        self.view_list.sort()
        self.node_addr = os.getenv('ADDRESS')
        self.address_index = self.view_list.index(self.node_addr)
        self.node_number = self.address_index + 1
        self.nodes_in_view = len(self.view_list)
        self.repl_factor = int(os.getenv('REPL_FACTOR'))
        self.shard_list = []
        self.number_of_shards = self.nodes_in_view / self.repl_factor
        self.makeShards()
    
    def makeShards(self):
        self.shard_list.clear()
        temp_shards = []
        replica_count = 0
        for address in self.view_list:
            temp_shards.append(address)
            replica_count += 1
            if self.node_addr == address:
                self.replica_id = replica_count
            if replica_count == self.repl_factor:
                self.shard_list.append(temp_shards.copy())
                if(self.node_addr in shard_list):
                    self.shard_index = len(self.shard_list)
                    self.shard_id =  self.shard_index - 1
                temp_shards.clear()
                replica_count = 0

        return

    def updateView(view_list, repl_factor):
        self.view_list.clear()
        self.view_list = view_list.copy()
        self.view_list.sort()
        self.address_index = self.view_list.index(self.node_addr)
        self.node_number = self.address_index + 1
        self.nodes_in_view = len(self.view_list)
        self.repl_factor = int(repl_factor)
        self.number_of_shards = int(self.nodes_in_view / self.repl_factor)
        self.makeShards()
        return

    def print(self):
        return

