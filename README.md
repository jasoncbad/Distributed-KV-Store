# Key-Value Store

This is a Key-Value Store implemented in the Python Flask framework. This KV-Store is scalable and replicated. In this project, we distribute keys accross nodes according to the replication factor and number of shards in the view of the system. For example, a system of four nodes with a replication factor of 2 produces two shards: each shard contains two replicas and the key's are distributed accross shards using consistent hashing. 

This project was developed by me and my colleagues as a Capstone Project for Peter Alvaro's Fall 2020 offering of CSE138 (Distributed Systems) at the University of California, Santa Cruz. 
They are listed below: 
[Skyler Stewart](https://github.com/skyler-stewart)
[Karl Munson](https://github.com/ksmunson)
[Jake Forrester]()

### 

We will call the partitions that we separate keys into as **shards**, where the keys
in a particular shard are stored on a particular key-value store instance, or **node**.

```
            +----------+              +----------+
            |  shard1  |              |  shard2  |
            |  (node1) |              |  (node2) |
            |  ------  |              |  ------  |
            |  - key1  |              |  - key2  |
            |  - key3  |              |  - key4  |
            |  - key5  |              |          |
            +----------+              +----------+
```

A key-value store that distributes keys across two nodes, as in the ascii diagram above, must
partition the keys into two shards, where each shard is then stored on a single node. 

If a node is queried (receives a request) for a key, the node must first find the node that stores
the requested key. If the queried node is the node that stores the key (according to the partitioning rule, no matter the key exists or not),
then it is able to directly handle the request and respond to the client (serve the request). If 
the queried node does not store the key, then it may serve the request by forwarding the request 
to the correct storage node and forwarding the response back to the client, acting as a proxy.
 This is demonstrated in the ascii diagram below, which should look quite similar to the 
ascii diagram of the previous assignment illustrating the overall behavior.

```
             +--------+                             +-------+
             | client |                             | Node1 |
             +--------+                             +-------+
                 |                                     |
                 |                                     | ---
                 | ---------------request----------->  |  ^
                 |                                     |  | node1
                 |                                     |  | has
                 |                                     |  | key
                 | <--------------response-----------  |  v
                 |                                     | ---
                 |             +---------+             |
                 |             |  Node2  |             |
                 |             +---------+             |
                 |                  |                  | ---
                 | --- request -->  |                  |  ^
                 |                  | --  request -->  |  | node1
                 |                  |                  |  | has
                 |                  | <-- response --  |  | key
                 | <-- response --  |                  |  v
                 |                  |                  | ---
                 v                  v                  v
```

The process of adding a node to the key-value store dynamically (while it is running) is called a
**view change** and allows us to increase capacity or throughput of the key-value store. To execute
a view change, the key-value store must re-partition keys into new shards (one additional shard is
used for the additional node), and then re-distribute each key-value pair to the correct storage
node. Re-partitioning keys is also known as a **reshard**. When a view change request is received,
the receiving node should notify the other nodes of the new view and initiate the reshard of the
entire key-value store.

# API

### Endpoints

All endpoints will accept JSON content type ("Content-Type: application/json"), and will respond in
JSON format and with the appropriate HTTP status code.

| Endpoint URI       | accepted request types |
| ------------------ | ---------------------- |
| `/kvs/keys/<key>`  | GET, PUT, DELETE       |
| `/kvs/key-count`   | GET                    |
| `/kvs/view-change` | PUT                    |


### Administrative Operations

##### GET key count for a shard

- To get the number of keys stored by a node, send a GET request to the endpoint,
  `/kvs/key-count` at any node.

- On success, the response should have status code 200 and JSON: `{"message":"Key count 
  retrieved successfully","key-count":<key-count>}`.

##### PUT request for view change

- To change the view, or add a new node to the key-value store, send a PUT request to the endpoint,
  `/kvs/view-change`, with a JSON payload containing the list of addresses in the new view.
  For example, the JSON payload to add `node3`, with IP address `10.10.0.6:13800`, to a view
  containing `node1` and `node2` would be: `{"view":"10.10.0.4:13800,10.10.0.5:13800,10.10.0.6:13800"}`.

  View change request can be sent to any of the existing nodes.

  A view change requires two operations:

    - Propagating the view update to every node

    - Reshard of the keys (a re-partition of keys across nodes)

  On success, the response should have status code 200 and JSON: 
      ```JSON
          {
              "message": "View change successful",
              "shards" : [
                  { "address": "10.10.0.4:13800", "key-count": 5 },
                  { "address": "10.10.0.5:13800", "key-count": 3 },
                  { "address": "10.10.0.6:13800", "key-count": 6 }
              ]
          }
      ```
      where each element in the "shards" list is a dictionary with two key-value pairs: the
      "address" key maps to the IP address of a node storing a shard, and the "key-count" key maps
      to the number of keys that are assigned to that node. For the above example, the node at
      address "10.10.0.6:13800" has 6 key-value pairs, meaning that after the view-change, 6 of the
      14 keys in the key-value store were re-partitioned into the shard stored on `node3`.

##### Insert new key

- To insert a key named `sampleKey`, send a PUT request to `/kvs/keys/sampleKey`.

    - If no value is provided for the new key, the key-value store should respond with status code
      400 and JSON: `{"error":"Value is missing","message":"Error in PUT"}`.

    - If the value provided for the new key has length greater than 50, the key-value store should
      respond with status code 400 and JSON: `{"error":"Key is too long","message":"Error in
      PUT"}`.

    - On success, the key-value store should respond with status code 201 and JSON:
      `{"message":"Added successfully","replaced":false,"address":"10.10.0.5:13800"}`. This example
      assumes the receiving node (`node1`) does not have address "10.10.0.5:13800" and it acted as a proxy to
      the node (`node2`) with that address. (Remember the follower from assignment 2?)


##### Update existing key

- To update an existing key named `sampleKey`, send a PUT request to `/kvs/keys/sampleKey`.

    - If no updated value is provided for the key, the key-value store should respond with status
      code 400 and JSON: `{"error":"Value is missing","message":"Error in PUT"}`

    - The key-value store should respond with status code 200 and JSON: `{"message":"Updated
      successfully","replaced":true}`. This example assumes the receiving node (`node2`) stores the key,
      `sampleKey`.


##### Read an existing key

- To get an existing key named `sampleKey`, send a GET request to `/kvs/keys/sampleKey`.

    - If the key, `sampleKey`, does not exist, the key-value store should respond with status code
      404 and the JSON: `{"doesExist":false,"error":"Key does not exist","message":"Error in GET"}`

    - On success, assuming the current value of `sampleKey` is `sampleValue`, the key-value store should
      respond with status code 200 and JSON:
      `{"doesExist":true,"message":"Retrieved successfully","value":"sampleValue"}`


##### Remove an existing key

- To delete an existing key named `sampleKey`, send a DELETE request to `/kvs/keys/sampleKey`.

    - If the key, `sampleKey`, does not exist, the key-value store should respond with status code
      404 and JSON: `{"doesExist":false,"error":"Key does not exist","message":"Error in DELETE"}`

    - On success, the key-value store should respond with status code 200 and JSON:
      `{"doesExist":true,"message":"Deleted successfully","address":"10.10.0.5:13800"}`. This
      example assumes the receiving node (`node1`) does not have address "10.10.0.5:13800" and it acted as a
      proxy to the node (`node2`) with that address.

### Command-line Examples

- Create subnet, kv_subnet, with IP range 10.10.0.0/16:
```bash
    $ docker network create --subnet=10.10.0.0/16 kv_subnet
```

- Build Docker image containing the key-value store implementation:
```bash
    $ docker build -t kvs:3.0 <path-to-Dockerfile-directory>
```

- Run two instances named `node1` and `node2`
```bash
    $ docker run -d -p 13801:13800 --net=kv_subnet --ip=10.10.0.4 --name="node1" 
      -e ADDRESS="10.10.0.4:13800" -e VIEW="10.10.0.4:13800,10.10.0.5:13800" 
      kvs:3.0
    $ docker run -d -p 13802:13800 --net=kv_subnet --ip=10.10.0.5 --name="node2" 
      -e ADDRESS="10.10.0.5:13800" -e VIEW="10.10.0.4:13800,10.10.0.5:13800" 
      kvs:3.0
```

-  Send requests as you wish with JSON payload.

- After a bunch of data operations, add an instance named `node3` and request for view-change:
```bash
    $ docker run -d -p 13803:13800 --net=kv_subnet --ip=10.10.0.6 --name="node3" 
      -e ADDRESS="10.10.0.6:13800" -e VIEW="10.10.0.4:13800,10.10.0.5:13800,10.10.0.6:13800"
      kvs:3.0
    
    $ curl --request   PUT                          \
           --header    "Content-Type: application/json" \
           --write-out "%{http_code}\n"              \
           --data      '{"view":"10.10.0.4:13800,10.10.0.5:13800,10.10.0.6:13800"}'
           http://127.0.0.1:13801(or 13802, 13803)/kvs/view-change
           {"message": "View change successful","shards":[{"address":"10.10.0.4:13800","key-count":5},
           {"address":"10.10.0.5:13800","key-count":3},{"address":"10.10.0.6:13800","key-count":6}]}
           200
```

# Container Options and Environment 

- VIEW -- a required environment variable that provides the address of each node in the store

- ADDRESS -- a required environment variable that provides the address of the node being started

- ip -- a required container property that assigns the given IP address to the container

- port -- a required container property that binds the given host port to the given container port

- net -- a required container property that connects the container to the given network

- name -- a convenience property so that we can distinguish between containers using a human
          readable name

